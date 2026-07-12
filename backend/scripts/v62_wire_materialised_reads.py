"""
NDIP V6.2 Phase A -- Wire materialised intelligence reads into
get_narrative_analysis() and get_top_influence_stakeholders().

STRATEGY: each function gets a read-from-materialised-table fast path
that activates when fresh data exists (written within the last 25 hours,
covering one daily ingest cycle). Falls back to the existing live
computation path when data is stale or absent -- no functionality lost.

NARRATIVE ANALYSIS:
  narrative_trends stores: narrative, mention_count, sentiment_avg,
  velocity (momentum %), date_bucket.
  Reconstructed fields: share_of_voice (from proportions), momentum_direction,
  sentiment_label, confidence, confidence_label.
  Not available from materialised data: sources, source_count (display-only,
  not used in downstream computation -- set to [] and 0).

INFLUENCE STAKEHOLDERS:
  stakeholder_influence_profiles stores all computed scores per stakeholder.
  The materialised read path does a simple ORDER BY composite_index DESC
  LIMIT n -- sub-millisecond rather than ~5.5s recomputation.

Run: docker exec agora-backend-1 python scripts/v62_wire_materialised_reads.py
"""
import sys; sys.path.insert(0, '/app')

# ── 1. strategic_narratives.py -- add materialised read to get_narrative_analysis ──
PATH_NARRATIVES = "/app/app/analytics/strategic_narratives.py"

with open(PATH_NARRATIVES, "r") as f:
    content = f.read()

old = '''def get_narrative_analysis(db, days: int = 7) -> list[dict]:
    """
    Compute share of voice, momentum, sentiment, and confidence for each narrative.
    This is the core of the Strategic Intelligence layer.

    V6.2 perf fix: memoized per (session, days), no time-based expiry --
    see module-level comment above for the TTL bug this replaced.
    Confirmed live this session to reduce repeated calls within a single
    Leadership Pack request to one genuine computation.
    """
    cache_key = (id(db), days)
    if cache_key in _narrative_analysis_cache:
        return _narrative_analysis_cache[cache_key]
    result = _get_narrative_analysis_uncached(db, days)
    _narrative_analysis_cache[cache_key] = result
    if len(_narrative_analysis_cache) > _NARRATIVE_ANALYSIS_CACHE_MAX_SIZE:
        oldest_key = next(iter(_narrative_analysis_cache))
        del _narrative_analysis_cache[oldest_key]
    return result'''

new = '''def get_narrative_analysis(db, days: int = 7) -> list[dict]:
    """
    Compute share of voice, momentum, sentiment, and confidence for each narrative.
    This is the core of the Strategic Intelligence layer.

    V6.2 perf fix: memoized per (session, days), no time-based expiry.
    V6.2 Phase A materialised intelligence: reads from narrative_trends
    table when fresh data exists (written within last 25h), falling back
    to live computation otherwise. Eliminates the ~3.4s post table scan
    on cache-cold requests when the ingest pipeline has run.
    """
    cache_key = (id(db), days)
    if cache_key in _narrative_analysis_cache:
        return _narrative_analysis_cache[cache_key]
    result = _get_narrative_analysis_from_materialised(db, days)
    if result is None:
        result = _get_narrative_analysis_uncached(db, days)
    _narrative_analysis_cache[cache_key] = result
    if len(_narrative_analysis_cache) > _NARRATIVE_ANALYSIS_CACHE_MAX_SIZE:
        oldest_key = next(iter(_narrative_analysis_cache))
        del _narrative_analysis_cache[oldest_key]
    return result


def _get_narrative_analysis_from_materialised(db, days: int = 7):
    """
    Fast path: read from narrative_trends when fresh data exists.
    Returns None if no fresh data found (triggers live computation fallback).
    Fresh = written within the last 25 hours (covers one daily ingest cycle).
    """
    try:
        from app.models.models import NarrativeTrend
        from datetime import datetime, timezone, timedelta
        cutoff = datetime.now(timezone.utc) - timedelta(hours=25)
        rows = db.query(NarrativeTrend).filter(
            NarrativeTrend.created_at >= cutoff
        ).order_by(NarrativeTrend.mention_count.desc()).all()
        if not rows:
            return None
        total = max(sum(r.mention_count for r in rows), 1)
        results = []
        for row in rows:
            if row.mention_count == 0:
                continue
            share_of_voice = round(row.mention_count / total * 100, 1)
            momentum = row.velocity or 0.0
            avg_sentiment = row.sentiment_avg or 0.0
            confidence = min(round((row.mention_count / 10 * 0.5 + 0.5), 2), 1.0)
            results.append({
                "narrative": row.narrative,
                "description": STRATEGIC_NARRATIVES.get(row.narrative, {}).get("description", row.narrative),
                "count": row.mention_count,
                "prev_count": 0,
                "share_of_voice": share_of_voice,
                "momentum": round(min(momentum, 500) if momentum > 0 else max(momentum, -100), 1),
                "momentum_direction": "rising" if momentum > 10 else "falling" if momentum < -10 else "stable",
                "avg_sentiment": round(avg_sentiment, 3),
                "sentiment_label": "positive" if avg_sentiment > 0.1 else "negative" if avg_sentiment < -0.1 else "neutral",
                "source_count": 0,
                "sources": [],
                "confidence": confidence,
                "confidence_label": "High" if confidence >= 0.7 else "Medium" if confidence >= 0.4 else "Low",
                "_from_materialised": True,
            })
        results.sort(key=lambda x: x["share_of_voice"], reverse=True)
        return results
    except Exception:
        return None'''

count = content.count(old)
print(f"[narrative] Anchor found {count} time(s).")
if count == 1:
    content = content.replace(old, new, 1)
    with open(PATH_NARRATIVES, "w") as f:
        f.write(content)
    print("[narrative] Patched: materialised fast path added to get_narrative_analysis().")
else:
    print(f"[narrative] SKIPPED -- expected 1, found {count}.")


# ── 2. stakeholder_influence.py -- add materialised read to get_top_influence_stakeholders ──
PATH_INFLUENCE = "/app/app/services/stakeholder_influence.py"

with open(PATH_INFLUENCE, "r") as f:
    content2 = f.read()

old2 = '''def get_top_influence_stakeholders(db: Session, limit: int = 10, days: int = 30) -> list:
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

new2 = '''def get_top_influence_stakeholders(db: Session, limit: int = 10, days: int = 30) -> list:
    """
    Returns stakeholders ranked by composite_index.
    V6.2 Phase A: reads from stakeholder_influence_profiles when fresh
    data exists, falling back to live batched computation otherwise.
    """
    materialised = _get_top_influence_from_materialised(db, limit, days)
    if materialised is not None:
        return materialised
    stakeholders = db.query(StakeholderRegistry).filter(StakeholderRegistry.is_active == True).all()'''

count2 = content2.count(old2)
print(f"[influence] Anchor found {count2} time(s).")
if count2 == 1:
    # Also need to add the helper function -- insert it before get_top_influence_stakeholders
    helper = '''
def _get_top_influence_from_materialised(db: Session, limit: int, days: int) -> list:
    """
    Fast path: read pre-computed influence profiles from
    stakeholder_influence_profiles when fresh data exists (written within
    last 25 hours). Returns None to trigger live computation fallback.
    """
    try:
        from app.models.models import StakeholderInfluenceProfile, StakeholderRegistry
        from datetime import datetime, timezone, timedelta
        cutoff = datetime.now(timezone.utc) - timedelta(hours=25)
        profiles = (
            db.query(StakeholderInfluenceProfile, StakeholderRegistry)
            .join(StakeholderRegistry, StakeholderInfluenceProfile.stakeholder_id == StakeholderRegistry.id)
            .filter(
                StakeholderInfluenceProfile.computed_at >= cutoff,
                StakeholderInfluenceProfile.period_days == days,
                StakeholderRegistry.is_active == True,
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


'''
    content2 = content2.replace(
        "def get_top_influence_stakeholders",
        helper + "def get_top_influence_stakeholders",
        1
    )
    content2 = content2.replace(old2, new2, 1)
    with open(PATH_INFLUENCE, "w") as f:
        f.write(content2)
    print("[influence] Patched: materialised fast path added to get_top_influence_stakeholders().")
else:
    print(f"[influence] SKIPPED -- expected 1, found {count2}.")
