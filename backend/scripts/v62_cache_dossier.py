"""
NDIP V6.2 Phase A item 1 -- Executive Opportunity Dossier caching.
Reference implementation: SOI Dashboard (verified 99.98% warm-cache
improvement). Anchor fetched fresh via live sed extraction this session.

TTL: 30 min, matching SOI Dashboard (same underlying alignment/readiness
data, same freshness consideration).

Run: docker exec agora-backend-1 python scripts/v62_cache_dossier.py
"""
PATH = "/app/app/api/routes/strategic_outcome.py"

with open(PATH, "r") as f:
    content = f.read()

old = '''def get_opportunity_dossier(
    opportunity_id: int,
    db: Session = Depends(get_db),
    _: dict = Depends(get_current_user),
):
    """V6.1.1 Phase F -- Executive Opportunity Dossier, structuring the existing execution plan into the dossier's named sections (Decision Makers, Funding Sources, Implementation, Oversight)."""
    from app.services.opportunity_dossier import generate_opportunity_dossier
    try:
        return generate_opportunity_dossier(db, opportunity_id)
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))'''

new = '''def get_opportunity_dossier(
    opportunity_id: int,
    db: Session = Depends(get_db),
    _: dict = Depends(get_current_user),
):
    """V6.1.1 Phase F -- Executive Opportunity Dossier, structuring the existing execution plan into the dossier's named sections (Decision Makers, Funding Sources, Implementation, Oversight)."""
    _cache_key = cache_key("opportunity-dossier", f"opportunity_id={opportunity_id}")
    _cached = get_cached(_cache_key)
    if _cached is not None:
        _cached["_cached"] = True
        return _cached
    from app.services.opportunity_dossier import generate_opportunity_dossier
    try:
        result = generate_opportunity_dossier(db, opportunity_id)
        set_cached(_cache_key, result, TTL_SOI_DASHBOARD)
        return result
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))'''

count = content.count(old)
print(f"Anchor found {count} time(s).")

if count != 1:
    print(f"Expected exactly 1 occurrence, found {count} -- aborting without changes.")
else:
    content = content.replace(old, new, 1)
    with open(PATH, "w") as f:
        f.write(content)
    print("Patched successfully: Opportunity Dossier route now cached (TTL_SOI_DASHBOARD, 30 min).")
