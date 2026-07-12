"""
NDIP V8 — Performance Materialisation Worker — uses :param bindparam style
"""
import sys
sys.path.insert(0, '/app')

import json, time
from datetime import datetime, timezone
from sqlalchemy import text
from app.db.database import SessionLocal


def run_materialisation():
    print("\n" + "=" * 60)
    print("NDIP V8 — Intelligence Materialisation Pipeline")
    print("=" * 60)
    db = SessionLocal()
    start = time.time()
    try:
        _ensure_materialised_table(db)
        _materialise_narrative_summary(db)
        _materialise_metrics_summary(db)
        _materialise_opportunity_summary(db)
        print(f"\n OK Materialisation complete in {round(time.time()-start,1)}s")
    except Exception as e:
        print(f"\n FAIL Materialisation failed: {e}")
    finally:
        db.close()


def _upsert(db, itype, data):
    db.execute(text(
        "INSERT INTO materialised_intelligence (intelligence_type, data, computed_at, expires_at) "
        "VALUES (:t, cast(:d as jsonb), NOW(), NOW() + INTERVAL '26 hours') "
        "ON CONFLICT (intelligence_type) DO UPDATE SET data=cast(excluded.data as jsonb), computed_at=NOW(), expires_at=NOW() + INTERVAL '26 hours'"
    ), {"t": itype, "d": json.dumps(data)})
    db.commit()


def _ensure_materialised_table(db):
    try:
        db.execute(text(
            "CREATE TABLE IF NOT EXISTS materialised_intelligence ("
            "intelligence_type VARCHAR(100) PRIMARY KEY, data JSONB NOT NULL, "
            "computed_at TIMESTAMPTZ DEFAULT NOW(), expires_at TIMESTAMPTZ)"
        ))
        db.commit()
    except Exception:
        db.rollback()


def _materialise_narrative_summary(db):
    print("\n[1/3] Materialising narrative summary...")
    try:
        rows = db.execute(text(
            "SELECT narrative, SUM(mention_count) as tm, AVG(sentiment_avg) as sa, AVG(velocity) as av "
            "FROM narrative_trends WHERE date_bucket > NOW() - INTERVAL '48 hours' "
            "GROUP BY narrative ORDER BY tm DESC LIMIT 11"
        )).fetchall()
        narratives = [{"narrative": r.narrative, "mention_count": int(r.tm or 0),
            "sentiment_score": round(float(r.sa or 0), 3), "velocity": round(float(r.av or 0), 2),
            "sentiment_label": "positive" if float(r.sa or 0) > 0.1 else ("negative" if float(r.sa or 0) < -0.1 else "neutral")}
            for r in rows]
        _upsert(db, "narrative_summary", {"narratives": narratives, "computed_at": datetime.now(timezone.utc).isoformat()})
        print(f"  OK {len(narratives)} narratives materialised")
    except Exception as e:
        db.rollback()
        print(f"  WARN Narrative failed: {e}")


def _materialise_metrics_summary(db):
    print("\n[2/3] Materialising metrics summary...")
    try:
        row = db.execute(text(
            "SELECT engagement_index, sentiment_score, total_participants, total_engagements, growth_rate "
            "FROM analytics_snapshots ORDER BY snapshot_date DESC LIMIT 1"
        )).fetchone()
        if not row:
            print("  WARN No analytics snapshots found"); return
        sc = db.execute(text(
            "SELECT COUNT(DISTINCT platform::text) FROM social_posts WHERE fetched_at > NOW() - INTERVAL '48 hours'"
        )).scalar() or 0
        confidence = "High" if sc >= 4 else ("Medium" if sc >= 2 else "Low")
        data = {"engagement_index": float(row.engagement_index or 0),
                "sentiment_score": float(row.sentiment_score or 0),
                "total_participants": int(row.total_participants or 0),
                "total_engagements": int(row.total_engagements or 0),
                "growth_rate": float(row.growth_rate or 0),
                "active_sources": int(sc), "confidence_label": confidence,
                "computed_at": datetime.now(timezone.utc).isoformat()}
        _upsert(db, "metrics_summary", data)
        print(f"  OK Engagement Index: {data['engagement_index']}, Confidence: {confidence}")
    except Exception as e:
        db.rollback()
        print(f"  WARN Metrics failed: {e}")


def _materialise_opportunity_summary(db):
    print("\n[3/3] Materialising opportunity summary...")
    try:
        rows = db.execute(text(
            "SELECT title, confidence, probability_of_success, status, category, "
            "what_opportunity_exists, evidence_post_count FROM opportunity_assessments "
            "ORDER BY probability_of_success DESC NULLS LAST LIMIT 10"
        )).fetchall()
        opps = [{"title": r.title, "confidence": r.confidence,
                 "probability": float(r.probability_of_success or 0), "status": r.status,
                 "category": r.category, "description": (r.what_opportunity_exists or "")[:200],
                 "evidence_posts": r.evidence_post_count or 0} for r in rows]
        _upsert(db, "opportunity_summary", {"opportunities": opps, "computed_at": datetime.now(timezone.utc).isoformat()})
        print(f"  OK {len(opps)} opportunities materialised")
    except Exception as e:
        db.rollback()
        print(f"  WARN Opportunities failed: {e}")


if __name__ == "__main__":
    run_materialisation()
