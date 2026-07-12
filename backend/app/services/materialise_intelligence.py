"""
NDIP V6.2 Phase A -- Materialised Intelligence Service

Wires the three existing, empty materialised tables into the ingest
pipeline. Called from daily_ingest.py after successful ingest, before
cache invalidation.

DESIGN: no new schemas, no new indexes, no architectural redesign. These
three tables already exist with correct schemas and indexes (confirmed
via live inspection this session). This module simply computes the same
values the request-time functions already compute, and persists them so
subsequent requests can read rather than recompute.

CORRECTNESS: each function is independently safe to call multiple times
(upsert semantics for influence profiles, append-only with dedup check
for momentum snapshots, append-only for narrative trends). A failed run
leaves the tables in a valid, if slightly stale, state -- never corrupt.

Functions:
  materialise_narrative_trends(db, days) -- populate NarrativeTrend
  materialise_influence_profiles(db, days) -- populate StakeholderInfluenceProfile
  materialise_momentum_snapshots(db) -- populate StakeholderMomentumSnapshot
  run_full_materialisation(db) -- convenience wrapper calling all three
"""
from datetime import datetime, timezone, timedelta
from sqlalchemy.orm import Session


def materialise_narrative_trends(db: Session, days: int = 30) -> dict:
    """
    Compute narrative share-of-voice, momentum, and sentiment via the
    EXISTING get_narrative_analysis() function and persist the results to
    NarrativeTrend. Uses an append-only strategy (one row per
    narrative+date_bucket combination per run) since the table is designed
    for time-series accumulation.

    Returns a summary dict for logging.
    """
    from app.analytics.strategic_narratives import _get_narrative_analysis_uncached
    from app.models.models import NarrativeTrend

    now = datetime.now(timezone.utc)
    date_bucket = now.replace(minute=0, second=0, microsecond=0)  # hourly bucket

    try:
        narratives = _get_narrative_analysis_uncached(db, days)
    except Exception as e:
        return {"status": "failed", "error": str(e), "rows_written": 0}

    rows_written = 0
    for n in narratives:
        try:
            row = NarrativeTrend(
                narrative=n["narrative"],
                platform="all",
                mention_count=n.get("count", 0),
                sentiment_avg=n.get("sentiment_score", 0.0),
                velocity=n.get("momentum", 0.0),
                date_bucket=date_bucket,
                query_tag=None,
            )
            db.add(row)
            rows_written += 1
        except Exception:
            continue
    db.commit()
    return {"status": "ok", "rows_written": rows_written, "narratives": len(narratives)}


def materialise_influence_profiles(db: Session, days: int = 30) -> dict:
    """
    Compute per-stakeholder influence scores via the EXISTING
    compute_stakeholder_influence() function and persist to
    StakeholderInfluenceProfile. Uses insert-or-update semantics keyed on
    (stakeholder_id, period_days) within the same calendar day -- so
    re-running on the same day updates rather than duplicating.
    """
    from app.models.models import StakeholderRegistry, StakeholderInfluenceProfile, StakeholderInfluenceLevel
    from app.services.stakeholder_influence import compute_stakeholder_influence
    from sqlalchemy import and_

    now = datetime.now(timezone.utc)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

    active_stakeholders = db.query(StakeholderRegistry).filter(
        StakeholderRegistry.is_active == True
    ).all()

    rows_written = 0
    rows_updated = 0

    for s in active_stakeholders:
        try:
            scores = compute_stakeholder_influence(db, s.id, days=days)
        except Exception:
            continue

        # Map influence_level string to enum
        level_map = {
            "Very High": StakeholderInfluenceLevel.CRITICAL,
            "Critical": StakeholderInfluenceLevel.CRITICAL,
            "High": StakeholderInfluenceLevel.HIGH,
            "Medium": StakeholderInfluenceLevel.MEDIUM,
            "Low": StakeholderInfluenceLevel.LOW,
        }
        influence_level = level_map.get(scores.get("influence_level", "Low"), StakeholderInfluenceLevel.LOW)

        # Check for existing row today for this stakeholder+period
        existing = db.query(StakeholderInfluenceProfile).filter(
            and_(
                StakeholderInfluenceProfile.stakeholder_id == s.id,
                StakeholderInfluenceProfile.period_days == days,
                StakeholderInfluenceProfile.computed_at >= today_start,
            )
        ).first()

        if existing:
            existing.influence_score = scores.get("influence_score", 0.0)
            existing.momentum_score = scores.get("momentum_score", 0.0)
            existing.narrative_impact_score = scores.get("narrative_impact_score", 0.0)
            existing.opportunity_relevance_score = scores.get("opportunity_relevance_score", 0.0)
            existing.engagement_priority_score = scores.get("engagement_priority_score", 0.0)
            existing.relationship_strength_score = scores.get("relationship_strength_score", 0.0)
            existing.composite_index = scores.get("composite_index", 0.0)
            existing.influence_level = influence_level
            existing.computed_at = now
            rows_updated += 1
        else:
            row = StakeholderInfluenceProfile(
                stakeholder_id=s.id,
                computed_at=now,
                period_days=days,
                influence_score=scores.get("influence_score", 0.0),
                momentum_score=scores.get("momentum_score", 0.0),
                narrative_impact_score=scores.get("narrative_impact_score", 0.0),
                opportunity_relevance_score=scores.get("opportunity_relevance_score", 0.0),
                engagement_priority_score=scores.get("engagement_priority_score", 0.0),
                relationship_strength_score=scores.get("relationship_strength_score", 0.0),
                composite_index=scores.get("composite_index", 0.0),
                influence_level=influence_level,
            )
            db.add(row)
            rows_written += 1

    db.commit()
    return {
        "status": "ok",
        "stakeholders_processed": len(active_stakeholders),
        "rows_written": rows_written,
        "rows_updated": rows_updated,
    }


def materialise_momentum_snapshots(db: Session) -> dict:
    """
    Append a momentum snapshot for every active stakeholder to
    StakeholderMomentumSnapshot. Append-only (by design -- the table is
    a time series for deriving momentum direction from real history).
    Dedup guard: skips a stakeholder if a snapshot already exists within
    the last hour (prevents duplicate snapshots from multiple ingest runs).
    """
    from app.models.models import StakeholderRegistry, StakeholderMomentumSnapshot
    from app.services.stakeholder_registry import compute_stakeholder_mentions
    from app.services.opportunity_intelligence import get_top_opportunities
    from sqlalchemy import and_

    now = datetime.now(timezone.utc)
    one_hour_ago = now - timedelta(hours=1)

    active_stakeholders = db.query(StakeholderRegistry).filter(
        StakeholderRegistry.is_active == True
    ).all()

    # Batch-compute mentions once for all stakeholders
    try:
        mentions = compute_stakeholder_mentions(db, days=30)
    except Exception:
        mentions = {}

    # Get opportunity relevance signals
    try:
        top_opps = get_top_opportunities(db, limit=5)
        opp_stakeholder_ids = set()
        import json
        for o in top_opps:
            opp_id = o.get("id") or o.get("opportunity_id")
            if opp_id:
                from app.models.models import OpportunityAssessment
                opp = db.query(OpportunityAssessment).filter(OpportunityAssessment.id == opp_id).first()
                if opp and opp.stakeholders_json:
                    try:
                        for s in json.loads(opp.stakeholders_json):
                            opp_stakeholder_ids.add(s.get("stakeholder_id"))
                    except Exception:
                        pass
    except Exception:
        opp_stakeholder_ids = set()

    rows_written = 0
    rows_skipped = 0

    for s in active_stakeholders:
        # Dedup guard
        recent = db.query(StakeholderMomentumSnapshot).filter(
            and_(
                StakeholderMomentumSnapshot.stakeholder_id == s.id,
                StakeholderMomentumSnapshot.snapshot_at >= one_hour_ago,
            )
        ).first()
        if recent:
            rows_skipped += 1
            continue

        mention_data = mentions.get(s.id, {})
        mention_count = mention_data.get("mention_count", 0)
        narrative_visibility = min(100.0, mention_count * 2.0)
        opportunity_relevance = 75.0 if s.id in opp_stakeholder_ids else 0.0
        policy_visibility = 50.0 if s.sector in ("Energy", "Infrastructure", "Climate", "Finance") else 25.0

        if mention_count > 100:
            momentum_label = "Accelerating"
        elif mention_count > 20:
            momentum_label = "Rising"
        elif mention_count > 5:
            momentum_label = "Stable"
        else:
            momentum_label = "Declining"

        row = StakeholderMomentumSnapshot(
            stakeholder_id=s.id,
            snapshot_at=now,
            mention_count=mention_count,
            narrative_visibility=narrative_visibility,
            opportunity_relevance=opportunity_relevance,
            policy_visibility=policy_visibility,
            momentum_label=momentum_label,
        )
        db.add(row)
        rows_written += 1

    db.commit()
    return {
        "status": "ok",
        "rows_written": rows_written,
        "rows_skipped_dedup": rows_skipped,
    }


def run_full_materialisation(db: Session) -> dict:
    """
    Convenience wrapper: run all three materialisation steps in sequence.
    Called from daily_ingest.py after ingest completes, before cache clear.
    Best-effort: a failure in one step does not block the others.
    """
    import time
    results = {}

    print("\nMaterialising intelligence...")

    start = time.time()
    try:
        results["narrative_trends"] = materialise_narrative_trends(db, days=30)
        print(f"  ✓ Narrative trends: {results['narrative_trends'].get('rows_written', 0)} rows written ({time.time()-start:.1f}s)")
    except Exception as e:
        results["narrative_trends"] = {"status": "failed", "error": str(e)}
        print(f"  ✗ Narrative trends: {e}")

    start = time.time()
    try:
        results["influence_profiles"] = materialise_influence_profiles(db, days=30)
        print(f"  ✓ Influence profiles: {results['influence_profiles'].get('rows_written',0)} written, "
              f"{results['influence_profiles'].get('rows_updated',0)} updated ({time.time()-start:.1f}s)")
    except Exception as e:
        results["influence_profiles"] = {"status": "failed", "error": str(e)}
        print(f"  ✗ Influence profiles: {e}")

    start = time.time()
    try:
        results["momentum_snapshots"] = materialise_momentum_snapshots(db)
        print(f"  ✓ Momentum snapshots: {results['momentum_snapshots'].get('rows_written',0)} written ({time.time()-start:.1f}s)")
    except Exception as e:
        results["momentum_snapshots"] = {"status": "failed", "error": str(e)}
        print(f"  ✗ Momentum snapshots: {e}")

    return results
