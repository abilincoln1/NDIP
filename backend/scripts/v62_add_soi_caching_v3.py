"""
NDIP V6.2 Phase A item 1 -- SOI Dashboard caching, final corrected
version with the precise real anchor (confirmed via character-level
diff this session: a blank line exists between the
run_intelligence_learning_cycle import and generation_result = ...).

Run: docker exec agora-backend-1 python scripts/v62_add_soi_caching_v3.py
"""
PATH = "/app/app/api/routes/strategic_outcome.py"

with open(PATH, "r") as f:
    content = f.read()

old = '''    from app.services.opportunity_intelligence import (
        generate_opportunity_assessments, get_top_opportunities, get_opportunity_pipeline_summary,
    )
    from app.services.stakeholder_registry import get_top_stakeholders
    from app.services.intelligence_learning import run_intelligence_learning_cycle

    generation_result = generate_opportunity_assessments(db, days)'''

new = '''    _cache_key = cache_key("soi-dashboard", f"days={days}")
    _cached = get_cached(_cache_key)
    if _cached is not None:
        _cached["_cached"] = True
        return _cached

    from app.services.opportunity_intelligence import (
        generate_opportunity_assessments, get_top_opportunities, get_opportunity_pipeline_summary,
    )
    from app.services.stakeholder_registry import get_top_stakeholders
    from app.services.intelligence_learning import run_intelligence_learning_cycle

    generation_result = generate_opportunity_assessments(db, days)'''

count = content.count(old)
print(f"Anchor found {count} time(s).")

if count != 1:
    print(f"Expected exactly 1 occurrence, found {count} -- aborting without changes.")
else:
    content = content.replace(old, new, 1)
    with open(PATH, "w") as f:
        f.write(content)
    print("Patched successfully: cache check inserted at top of strategic_outcome_dashboard.")
