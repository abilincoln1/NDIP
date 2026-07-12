"""
NDIP V6.2 -- Fix the influence materialised read patch, using the correct
blank-line-aware anchor confirmed via live diagnostic.

Run: docker exec agora-backend-1 python scripts/v62_fix_influence_materialised.py
"""
PATH = "/app/app/services/stakeholder_influence.py"

with open(PATH, "r") as f:
    content = f.read()

old = '''def get_top_influence_stakeholders(db: Session, limit: int = 10, days: int = 30) -> list:
    """
    Returns stakeholders ranked by composite_index, computing fresh.

    PERFORMANCE: this now computes mentions, momentum, narrative impact,
    relationship strength, and opportunity relevance for ALL active
    stakeholders using batched single-pass helpers, instead of calling
    compute_stakeholder_influence() (which independently re-scans the post
    table) once per stakeholder. Measured at 87s for 45 stakeholders
    before this fix; the batched version should complete in well under a
    second for the same data volume.
    """
    stakeholders = db.query(StakeholderRegistry).filter(StakeholderRegistry.is_active == True).all()'''

new = '''def _get_top_influence_from_materialised(db: Session, limit: int, days: int):
    """
    Fast path: read pre-computed influence profiles from
    stakeholder_influence_profiles when fresh data exists (written within
    last 25 hours). Returns None to trigger live computation fallback.
    """
    try:
        from app.models.models import StakeholderInfluenceProfile, StakeholderRegistry as SR
        from datetime import datetime, timezone, timedelta
        cutoff = datetime.now(timezone.utc) - timedelta(hours=25)
        profiles = (
            db.query(StakeholderInfluenceProfile, SR)
            .join(SR, StakeholderInfluenceProfile.stakeholder_id == SR.id)
            .filter(
                StakeholderInfluenceProfile.computed_at >= cutoff,
                StakeholderInfluenceProfile.period_days == days,
                SR.is_active == True,
            )
            .order_by(StakeholderInfluenceProfile.composite_index.desc())
            .limit(limit)
            .all()
        )
        if not profiles:
            return None
        results = []
        for profile, stakeholder in profiles:
            results.append({
                "stakeholder_id": stakeholder.id,
                "name": stakeholder.name,
                "category": stakeholder.category,
                "sector": stakeholder.sector,
                "stakeholder_type": stakeholder.stakeholder_type,
                "influence_score": profile.influence_score,
                "momentum_score": profile.momentum_score,
                "narrative_impact_score": profile.narrative_impact_score,
                "opportunity_relevance_score": profile.opportunity_relevance_score,
                "engagement_priority_score": profile.engagement_priority_score,
                "relationship_strength_score": profile.relationship_strength_score,
                "composite_influence_index": profile.composite_index,
                "influence_level": profile.influence_level.value if hasattr(profile.influence_level, "value") else str(profile.influence_level),
                "monitoring_priority": "Critical" if profile.composite_index >= 70 else "High" if profile.composite_index >= 50 else "Medium" if profile.composite_index >= 30 else "Low",
                "_from_materialised": True,
            })
        return results
    except Exception:
        return None


def get_top_influence_stakeholders(db: Session, limit: int = 10, days: int = 30) -> list:
    """
    Returns stakeholders ranked by composite_index, computing fresh.

    PERFORMANCE: this now computes mentions, momentum, narrative impact,
    relationship strength, and opportunity relevance for ALL active
    stakeholders using batched single-pass helpers, instead of calling
    compute_stakeholder_influence() (which independently re-scans the post
    table) once per stakeholder. Measured at 87s for 45 stakeholders
    before this fix; the batched version should complete in well under a
    second for the same data volume.

    V6.2 Phase A: reads from stakeholder_influence_profiles when fresh
    data exists (written within last 25h by ingest pipeline).
    """
    materialised = _get_top_influence_from_materialised(db, limit, days)
    if materialised is not None:
        return materialised
    stakeholders = db.query(StakeholderRegistry).filter(StakeholderRegistry.is_active == True).all()'''

count = content.count(old)
print(f"Anchor found {count} time(s).")
if count != 1:
    print("Aborting.")
else:
    content = content.replace(old, new, 1)
    with open(PATH, "w") as f:
        f.write(content)
    print("Patched: materialised fast path added to get_top_influence_stakeholders().")
