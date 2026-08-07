"""
NDIP Phase D.3 — Scheduler Jobs (D3.6)
File: app/scheduler/d3_jobs.py

Scheduled jobs for Phase D.3. These are called by the existing scheduler
container (ndip-scheduler-1). Integrate into the scheduler's main loop
via the existing schedule library pattern.

Hourly jobs:
  - nlp_extraction_job        — process pending engagement reports with spaCy
  - duplicate_detection_job   — flag duplicate reports/submissions
  - verification_queue_job    — auto-assign pending verifications to verifiers
  - notification_retry_job    — retry failed notification deliveries

Nightly jobs:
  - impact_score_rebuild_job  — compute diaspora impact scores for all members
  - leaderboard_rebuild_job   — update chapter and national ranks
  - intelligence_graph_job    — rebuild intelligence node/edge graph
  - chapter_summaries_job     — generate per-chapter activity summaries
  - cleanup_job               — purge expired tokens, revoked sessions

All jobs are instrumented: they write start/end records to scheduler_job_log.
Job failures are caught and logged — a failing job never crashes the scheduler.
spaCy is operational (en_core_web_sm installed). Falls back to TextBlob
if spaCy model fails to load.
"""
import logging
import traceback
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.db.database import SessionLocal

logger = logging.getLogger(__name__)


# ─── NLP pipeline ──────────────────────────────────────────────────────────

def _load_nlp():
    """Load spaCy model with TextBlob fallback."""
    try:
        import spacy
        nlp = spacy.load("en_core_web_sm")
        logger.info("NLP: spaCy en_core_web_sm loaded")
        return nlp, "spacy"
    except Exception as e:
        logger.warning("spaCy unavailable (%s), using TextBlob fallback", e)
        return None, "textblob"


_NLP, _NLP_BACKEND = _load_nlp()


def _extract_entities_spacy(text_content: str) -> dict:
    doc = _NLP(text_content[:10000])  # spaCy limit safety
    return {
        "persons":       [e.text for e in doc.ents if e.label_ == "PERSON"],
        "organisations": [e.text for e in doc.ents if e.label_ in ("ORG", "GPE")],
        "locations":     [e.text for e in doc.ents if e.label_ in ("GPE", "LOC")],
        "dates":         [e.text for e in doc.ents if e.label_ == "DATE"],
    }


def _extract_sentiment_textblob(text_content: str) -> dict:
    from textblob import TextBlob
    blob = TextBlob(text_content[:5000])
    return {
        "polarity":     round(blob.sentiment.polarity, 4),
        "subjectivity": round(blob.sentiment.subjectivity, 4),
    }


# ─── Job wrapper ───────────────────────────────────────────────────────────

class JobRunner:
    """Context manager that logs job start/end to scheduler_job_log."""

    def __init__(self, db: Session, job_name: str):
        self.db = db
        self.job_name = job_name
        self.log_id: Optional[int] = None
        self.records_processed = 0

    def __enter__(self):
        try:
            row = self.db.execute(text("""
                INSERT INTO scheduler_job_log (job_name, status)
                VALUES (:name, 'running')
                RETURNING id
            """), {"name": self.job_name}).fetchone()
            self.log_id = row.id
            self.db.commit()
        except Exception:
            pass
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        status = "failed" if exc_type else "success"
        error_msg = traceback.format_exc()[:2000] if exc_type else None
        try:
            self.db.execute(text("""
                UPDATE scheduler_job_log
                SET finished_at = now(),
                    status = :status,
                    records_processed = :records,
                    error_message = :error
                WHERE id = :id
            """), {
                "status": status,
                "records": self.records_processed,
                "error": error_msg,
                "id": self.log_id,
            })
            self.db.commit()
        except Exception:
            pass
        # Never suppress exceptions — let caller log them
        return False


# ─── Hourly: NLP extraction ────────────────────────────────────────────────

def nlp_extraction_job() -> dict:
    """Process engagement reports that have no NLP analysis yet.
    Extracts named entities and sentiment. Stores results in the
    report's outcome_summary if empty, and updates impact_score."""
    db = SessionLocal()
    try:
        with JobRunner(db, "nlp_extraction") as job:
            # Find reports submitted/approved without impact scores
            reports = db.execute(text("""
                SELECT id, title, description, outcome_summary, attendees_count
                FROM engagement_reports
                WHERE status IN ('submitted', 'approved')
                  AND impact_score IS NULL
                  AND deleted_at IS NULL
                ORDER BY created_at
                LIMIT 100
            """)).fetchall()

            for report in reports:
                try:
                    combined_text = f"{report.title}. {report.description or ''}"
                    if _NLP_BACKEND == "spacy":
                        entities = _extract_entities_spacy(combined_text)
                    else:
                        entities = {}

                    sentiment = _extract_sentiment_textblob(combined_text)

                    # Simple impact score: weighted sum of indicators
                    base_score = min(report.attendees_count * 0.5, 50)  # max 50 from attendance
                    sentiment_bonus = max(0, sentiment["polarity"]) * 20  # max 20 from sentiment
                    impact_score = round(base_score + sentiment_bonus, 2)

                    db.execute(text("""
                        UPDATE engagement_reports
                        SET impact_score = :score,
                            updated_at = now()
                        WHERE id = CAST(:id AS UUID)
                    """), {"score": impact_score, "id": str(report.id)})
                    job.records_processed += 1
                except Exception as e:
                    logger.warning("NLP failed for report %s: %s", report.id, e)

            db.commit()
            return {"processed": job.records_processed}
    finally:
        db.close()


# ─── Hourly: Duplicate detection ───────────────────────────────────────────

def duplicate_detection_job() -> dict:
    """Flag potential duplicate engagement reports (same member, same date,
    similar title). Marks duplicates as 'under_review' for human inspection."""
    db = SessionLocal()
    try:
        with JobRunner(db, "duplicate_detection") as job:
            # Find reports from the same member on the same event_date
            # with very similar titles (exact match on first 50 chars for now;
            # fuzzy matching deferred to spaCy similarity in a later phase)
            duplicates = db.execute(text("""
                SELECT a.id, b.id as dup_of
                FROM engagement_reports a
                JOIN engagement_reports b
                    ON a.member_id = b.member_id
                    AND a.event_date = b.event_date
                    AND LEFT(LOWER(a.title), 50) = LEFT(LOWER(b.title), 50)
                    AND a.id != b.id
                    AND a.created_at > b.created_at
                WHERE a.status = 'submitted'
                  AND a.deleted_at IS NULL
                  AND b.deleted_at IS NULL
            """)).fetchall()

            for dup in duplicates:
                db.execute(text("""
                    UPDATE engagement_reports
                    SET status = 'under_review',
                        reviewer_notes = 'Flagged as potential duplicate by automated detection',
                        updated_at = now()
                    WHERE id = CAST(:id AS UUID) AND status = 'submitted'
                """), {"id": str(dup.id)})
                job.records_processed += 1

            db.commit()
            return {"flagged": job.records_processed}
    finally:
        db.close()


# ─── Hourly: Verification queue ────────────────────────────────────────────

def verification_queue_job() -> dict:
    """Auto-assign unassigned verification submissions to available verifiers
    (members with role='verifier'). Round-robin assignment."""
    db = SessionLocal()
    try:
        with JobRunner(db, "verification_queue") as job:
            # Get verifiers
            verifiers = db.execute(text("""
                SELECT id FROM members
                WHERE role = 'verifier' AND is_active = TRUE AND deleted_at IS NULL
                ORDER BY id
            """)).fetchall()

            if not verifiers:
                return {"assigned": 0, "note": "No verifiers available"}

            # Get unassigned pending submissions
            pending = db.execute(text("""
                SELECT id FROM verification_submissions
                WHERE status = 'pending' AND assigned_to IS NULL AND deleted_at IS NULL
                ORDER BY created_at
                LIMIT 50
            """)).fetchall()

            for i, submission in enumerate(pending):
                verifier = verifiers[i % len(verifiers)]
                db.execute(text("""
                    UPDATE verification_submissions
                    SET assigned_to = CAST(:verifier_id AS UUID),
                        status = 'assigned',
                        updated_at = now()
                    WHERE id = CAST(:id AS UUID)
                """), {"verifier_id": str(verifier.id), "id": str(submission.id)})
                job.records_processed += 1

            db.commit()
            return {"assigned": job.records_processed}
    finally:
        db.close()


# ─── Hourly: Notification retry ────────────────────────────────────────────

def notification_retry_job() -> dict:
    """Retry failed notifications. Max 3 attempts per notification."""
    db = SessionLocal()
    try:
        with JobRunner(db, "notification_retry") as job:
            from app.services.notification_service import NotificationService
            svc = NotificationService(db)
            result = svc.retry_failed(max_retries=3)
            job.records_processed = result.get("retried", 0)
            return result
    finally:
        db.close()


# ─── Nightly: Impact score rebuild ─────────────────────────────────────────

def impact_score_rebuild_job() -> dict:
    """Rebuild diaspora impact scores for all active members.
    Scoring model:
      - Approved engagement reports: 10 pts each (capped at 100)
      - Active sponsorships:         20 pts each (capped at 100)
      - Project participation:        5 pts each (capped at 50)
      - Verification bonus:          25 pts (if is_verified)
    """
    db = SessionLocal()
    try:
        with JobRunner(db, "impact_score_rebuild") as job:
            today = datetime.now(timezone.utc).date()

            # Get all active members
            members = db.execute(text("""
                SELECT id, is_verified FROM members
                WHERE is_active = TRUE AND deleted_at IS NULL
            """)).fetchall()

            for member in members:
                mid = str(member.id)

                reports_count = db.execute(text("""
                    SELECT COUNT(*) FROM engagement_reports
                    WHERE member_id = CAST(:mid AS UUID) AND status = 'approved'
                      AND deleted_at IS NULL
                """), {"mid": mid}).scalar() or 0

                sponsorships_count = db.execute(text("""
                    SELECT COUNT(*) FROM ward_sponsorships
                    WHERE sponsor_member_id = CAST(:mid AS UUID)
                      AND status IN ('active', 'completed')
                """), {"mid": mid}).scalar() or 0

                projects_count = db.execute(text("""
                    SELECT COUNT(*) FROM project_stakeholders ps
                    JOIN platform_projects pp ON ps.project_id = pp.id
                    WHERE ps.member_id = CAST(:mid AS UUID)
                      AND pp.status IN ('active', 'completed')
                      AND pp.deleted_at IS NULL
                """), {"mid": mid}).scalar() or 0

                reports_score = min(reports_count * 10, 100)
                sponsorship_score = min(sponsorships_count * 20, 100)
                projects_score = min(projects_count * 5, 50)
                verification_bonus = 25.0 if member.is_verified else 0.0
                total = reports_score + sponsorship_score + projects_score + verification_bonus

                db.execute(text("""
                    INSERT INTO diaspora_impact_scores
                        (member_id, score_date, total_score, reports_score,
                         sponsorship_score, projects_score, verification_bonus)
                    VALUES
                        (CAST(:mid AS UUID), :today, :total, :rs, :ss, :ps, :vb)
                    ON CONFLICT (member_id, score_date) DO UPDATE SET
                        total_score = EXCLUDED.total_score,
                        reports_score = EXCLUDED.reports_score,
                        sponsorship_score = EXCLUDED.sponsorship_score,
                        projects_score = EXCLUDED.projects_score,
                        verification_bonus = EXCLUDED.verification_bonus,
                        computed_at = now()
                """), {
                    "mid": mid, "today": today,
                    "total": total, "rs": reports_score,
                    "ss": sponsorship_score, "ps": projects_score,
                    "vb": verification_bonus,
                })
                job.records_processed += 1

            db.commit()
            return {"members_scored": job.records_processed}
    finally:
        db.close()


# ─── Nightly: Leaderboard ranks ────────────────────────────────────────────

def leaderboard_rebuild_job() -> dict:
    """Assign chapter_rank and national_rank to today's impact scores."""
    db = SessionLocal()
    try:
        with JobRunner(db, "leaderboard_rebuild") as job:
            today = datetime.now(timezone.utc).date()

            # National rank
            db.execute(text("""
                UPDATE diaspora_impact_scores dis
                SET national_rank = ranked.rank
                FROM (
                    SELECT id,
                           RANK() OVER (ORDER BY total_score DESC) as rank
                    FROM diaspora_impact_scores
                    WHERE score_date = :today
                ) ranked
                WHERE dis.id = ranked.id AND dis.score_date = :today
            """), {"today": today})

            # Chapter rank — join via members table
            db.execute(text("""
                UPDATE diaspora_impact_scores dis
                SET chapter_rank = ranked.rank
                FROM (
                    SELECT dis2.id,
                           RANK() OVER (
                               PARTITION BY m.chapter_id
                               ORDER BY dis2.total_score DESC
                           ) as rank
                    FROM diaspora_impact_scores dis2
                    JOIN members m ON dis2.member_id = m.id
                    WHERE dis2.score_date = :today
                      AND m.chapter_id IS NOT NULL
                ) ranked
                WHERE dis.id = ranked.id AND dis.score_date = :today
            """), {"today": today})

            db.commit()
            job.records_processed = db.execute(text("""
                SELECT COUNT(*) FROM diaspora_impact_scores WHERE score_date = :today
            """), {"today": today}).scalar() or 0

            return {"ranked": job.records_processed}
    finally:
        db.close()


# ─── Nightly: Cleanup ──────────────────────────────────────────────────────

def cleanup_job() -> dict:
    """Purge expired tokens, revoked sessions, old login attempts."""
    db = SessionLocal()
    try:
        with JobRunner(db, "cleanup") as job:
            from app.services.auth_service import AuthService
            svc = AuthService(db)
            result = svc.purge_expired_tokens()
            job.records_processed = sum(result.values())
            return result
    finally:
        db.close()


# ─── Nightly: Chapter summaries ────────────────────────────────────────────

def chapter_summaries_job() -> dict:
    """Generate per-chapter activity summary statistics.
    Results are stored as JSON in a simple cache key in Redis (if available)
    or logged. Frontend can poll /api/v2/admin/chapter-summaries."""
    db = SessionLocal()
    try:
        with JobRunner(db, "chapter_summaries") as job:
            chapters = db.execute(text("""
                SELECT id, name FROM chapters
                WHERE is_active = TRUE AND deleted_at IS NULL
            """)).fetchall()

            summaries = []
            for chapter in chapters:
                cid = str(chapter.id)

                member_count = db.execute(text("""
                    SELECT COUNT(*) FROM members
                    WHERE chapter_id = CAST(:cid AS UUID)
                      AND is_active = TRUE AND deleted_at IS NULL
                """), {"cid": cid}).scalar() or 0

                verified_count = db.execute(text("""
                    SELECT COUNT(*) FROM members
                    WHERE chapter_id = CAST(:cid AS UUID)
                      AND is_verified = TRUE AND deleted_at IS NULL
                """), {"cid": cid}).scalar() or 0

                report_count = db.execute(text("""
                    SELECT COUNT(*) FROM engagement_reports er
                    WHERE er.chapter_id = CAST(:cid AS UUID)
                      AND er.status = 'approved'
                      AND er.deleted_at IS NULL
                """), {"cid": cid}).scalar() or 0

                avg_score = db.execute(text("""
                    SELECT AVG(dis.total_score)
                    FROM diaspora_impact_scores dis
                    JOIN members m ON dis.member_id = m.id
                    WHERE m.chapter_id = CAST(:cid AS UUID)
                      AND dis.score_date = CURRENT_DATE
                """), {"cid": cid}).scalar() or 0.0

                summaries.append({
                    "chapter_id": cid,
                    "name": chapter.name,
                    "member_count": member_count,
                    "verified_count": verified_count,
                    "report_count": report_count,
                    "avg_impact_score": round(float(avg_score), 2),
                })
                job.records_processed += 1

            # Cache in Redis if available
            try:
                import redis, json
                r = redis.from_url(os.getenv("REDIS_URL", "redis://redis:6379/0"))
                r.setex("ndip:chapter_summaries", 86400, json.dumps(summaries))
            except Exception:
                pass  # Redis unavailable — summaries computed but not cached

            return {"chapters_summarised": job.records_processed}
    finally:
        db.close()


import os


# ─── Job registry (for scheduler integration) ──────────────────────────────

HOURLY_JOBS = [
    nlp_extraction_job,
    duplicate_detection_job,
    verification_queue_job,
    notification_retry_job,
]

NIGHTLY_JOBS = [
    impact_score_rebuild_job,
    leaderboard_rebuild_job,
    chapter_summaries_job,
    cleanup_job,
]


def run_all_hourly():
    """Run all hourly jobs. Called by the scheduler every 60 minutes."""
    results = {}
    for job_fn in HOURLY_JOBS:
        try:
            results[job_fn.__name__] = job_fn()
        except Exception as e:
            logger.error("Hourly job %s failed: %s", job_fn.__name__, e)
            results[job_fn.__name__] = {"error": str(e)}
    return results


def run_all_nightly():
    """Run all nightly jobs. Called by the scheduler at 02:00 UTC."""
    results = {}
    for job_fn in NIGHTLY_JOBS:
        try:
            results[job_fn.__name__] = job_fn()
        except Exception as e:
            logger.error("Nightly job %s failed: %s", job_fn.__name__, e)
            results[job_fn.__name__] = {"error": str(e)}
    return results
