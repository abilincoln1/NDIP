"""
NDIP V6.2 Phase A item 1 -- Redis caching for the Strategic Opportunity
Intelligence dashboard route, using the EXISTING, already-proven
cache.py infrastructure (get_cached/set_cached/cache_key), matching the
manual pattern Leadership Pack already uses.

TTL: 30 min. This route calls generate_opportunity_assessments()
internally, which re-detects opportunities from current discourse --
genuinely time-sensitive, shorter than Leadership Pack's 60 min.
Invalidated by the existing invalidate_all() call after daily ingest --
no new invalidation logic needed.

Anchor confirmed via live full-function extraction this session.

Run: docker exec agora-backend-1 python scripts/v62_add_soi_caching.py
"""
PATH = "/app/app/api/routes/strategic_outcome.py"

with open(PATH, "r") as f:
    content = f.read()

patches_applied = []
patches_skipped = []


def apply_patch(name, old, new):
    global content
    if old not in content:
        patches_skipped.append(name)
        return
    content = content.replace(old, new, 1)
    patches_applied.append(name)


apply_patch(
    "Import cache functions + TTL constant",
    '''from app.schemas.schemas import (
    StakeholderRegistryCreate, OpportunityRegistryCreate,
    OpportunityStatusUpdate, OutcomeChainLinkCreate,
    StakeholderRelationshipCreate, StakeholderRegistryUpdate, OpportunityRegistryUpdate,
)''',
    '''from app.schemas.schemas import (
    StakeholderRegistryCreate, OpportunityRegistryCreate,
    OpportunityStatusUpdate, OutcomeChainLinkCreate,
    StakeholderRelationshipCreate, StakeholderRegistryUpdate, OpportunityRegistryUpdate,
)
from app.services.cache import cache_key, get_cached, set_cached

# V6.2 Phase A -- cache TTL for the previously-uncached SOI Dashboard,
# shorter than Leadership Pack's 60min since this route re-detects
# opportunities from current discourse on every call.
TTL_SOI_DASHBOARD = 1800  # 30 min''',
)

old_function_tail = '''    from app.services.opportunity_intelligence import (
        generate_opportunity_assessments, get_top_opportunities, get_opportunity_pipeline_summary,
    )
    from app.services.stakeholder_registry import get_top_stakeholders
    from app.services.intelligence_learning import run_intelligence_learning_cycle
    generation_result = generate_opportunity_assessments(db, days)
    top_opportunities = get_top_opportunities(db, limit=10)
    pipeline_summary_data = get_opportunity_pipeline_summary(db)
    top_stakeholders = get_top_stakeholders(db, limit=10, days=days)
    learning_cycle = run_intelligence_learning_cycle(db)
    value_counts = {"Critical": 0, "High": 0, "Medium": 0, "Low": 0}
    for o in top_opportunities:
        sv = o.get("strategic_value", "Low")
        value_counts[sv] = value_counts.get(sv, 0) + 1
    engagement_priorities = [
        s for s in top_stakeholders if s.get("monitoring_priority") in ("High", "Critical")
    ][:5]
    # V6.1.2 Phase B -- dossier-derived Decision Makers / Funding Sources /
    # Implementation breakdown per opportunity, reusing
    # generate_opportunity_dossier (no new computation engine; classifies
    # the same already-computed alignment data by real stakeholder_type).
    opportunity_dossiers = []
    try:
        from app.services.opportunity_dossier import generate_opportunity_dossier
        for o in top_opportunities[:10]:
            opp_id = o.get("id") or o.get("opportunity_id")
            if opp_id is None:
                continue
            try:
                dossier = generate_opportunity_dossier(db, opp_id)
                opportunity_dossiers.append({
                    "opportunity_id": opp_id,
                    "title": dossier["opportunity_assessment"],
                    "decision_makers": dossier["stakeholders_by_role"]["Decision Makers"],
                    "funding_sources": dossier["stakeholders_by_role"]["Funding Sources"],
                    "implementation": dossier["stakeholders_by_role"]["Implementation"],
                    "data_quality_notes": dossier["data_quality_notes"],
                })
            except Exception:
                continue
    except Exception:
        opportunity_dossiers = []
    return {
        "period_days": days,
        "generation_summary": generation_result,
        "top_opportunities": top_opportunities,
        "stakeholder_rankings": top_stakeholders,
        "engagement_priorities": engagement_priorities,
        "opportunity_pipeline": pipeline_summary_data,
        "strategic_value_distribution": value_counts,
        "decision_quality_metrics": learning_cycle.get("decision_quality_metrics"),
        "strategic_outcome_metrics": learning_cycle.get("strategic_outcome_metrics"),
        "platform_learning_score": learning_cycle.get("platform_learning_score"),
        "opportunity_dossiers": opportunity_dossiers,
    }'''

new_function_tail = '''    _cache_key = cache_key("soi-dashboard", f"days={days}")
    _cached = get_cached(_cache_key)
    if _cached is not None:
        _cached["_cached"] = True
        return _cached

    from app.services.opportunity_intelligence import (
        generate_opportunity_assessments, get_top_opportunities, get_opportunity_pipeline_summary,
    )
    from app.services.stakeholder_registry import get_top_stakeholders
    from app.services.intelligence_learning import run_intelligence_learning_cycle
    generation_result = generate_opportunity_assessments(db, days)
    top_opportunities = get_top_opportunities(db, limit=10)
    pipeline_summary_data = get_opportunity_pipeline_summary(db)
    top_stakeholders = get_top_stakeholders(db, limit=10, days=days)
    learning_cycle = run_intelligence_learning_cycle(db)
    value_counts = {"Critical": 0, "High": 0, "Medium": 0, "Low": 0}
    for o in top_opportunities:
        sv = o.get("strategic_value", "Low")
        value_counts[sv] = value_counts.get(sv, 0) + 1
    engagement_priorities = [
        s for s in top_stakeholders if s.get("monitoring_priority") in ("High", "Critical")
    ][:5]
    # V6.1.2 Phase B -- dossier-derived Decision Makers / Funding Sources /
    # Implementation breakdown per opportunity, reusing
    # generate_opportunity_dossier (no new computation engine; classifies
    # the same already-computed alignment data by real stakeholder_type).
    opportunity_dossiers = []
    try:
        from app.services.opportunity_dossier import generate_opportunity_dossier
        for o in top_opportunities[:10]:
            opp_id = o.get("id") or o.get("opportunity_id")
            if opp_id is None:
                continue
            try:
                dossier = generate_opportunity_dossier(db, opp_id)
                opportunity_dossiers.append({
                    "opportunity_id": opp_id,
                    "title": dossier["opportunity_assessment"],
                    "decision_makers": dossier["stakeholders_by_role"]["Decision Makers"],
                    "funding_sources": dossier["stakeholders_by_role"]["Funding Sources"],
                    "implementation": dossier["stakeholders_by_role"]["Implementation"],
                    "data_quality_notes": dossier["data_quality_notes"],
                })
            except Exception:
                continue
    except Exception:
        opportunity_dossiers = []
    result = {
        "period_days": days,
        "generation_summary": generation_result,
        "top_opportunities": top_opportunities,
        "stakeholder_rankings": top_stakeholders,
        "engagement_priorities": engagement_priorities,
        "opportunity_pipeline": pipeline_summary_data,
        "strategic_value_distribution": value_counts,
        "decision_quality_metrics": learning_cycle.get("decision_quality_metrics"),
        "strategic_outcome_metrics": learning_cycle.get("strategic_outcome_metrics"),
        "platform_learning_score": learning_cycle.get("platform_learning_score"),
        "opportunity_dossiers": opportunity_dossiers,
    }
    set_cached(_cache_key, result, TTL_SOI_DASHBOARD)
    return result'''

apply_patch("Wrap strategic_outcome_dashboard body with cache check + write", old_function_tail, new_function_tail)

with open(PATH, "w") as f:
    f.write(content)

print(f"Applied: {len(patches_applied)}")
for p in patches_applied:
    print(f"  [OK] {p}")
print(f"Skipped: {len(patches_skipped)}")
for p in patches_skipped:
    print(f"  [SKIPPED] {p}")
