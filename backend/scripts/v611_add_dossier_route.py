"""
NDIP V6.1.1 Phase F -- Add the Executive Opportunity Dossier route.

Inserted directly after the existing get_execution_plan route, in the
exact same style (confirmed live via sed extraction), under the same
/strategic-outcome/v61/opportunities/{opportunity_id}/... URL pattern.

Run: docker exec agora-backend-1 python scripts/v611_add_dossier_route.py
"""
PATH = "/app/app/api/routes/strategic_outcome.py"

with open(PATH, "r") as f:
    content = f.read()

old = '''@router.get("/v61/opportunities/{opportunity_id}/execution-plan")
def get_execution_plan(
    opportunity_id: int,
    db: Session = Depends(get_db),
    _: dict = Depends(get_current_user),
):
    from app.services.opportunity_intelligence import generate_execution_plan
    try:
        return generate_execution_plan(db, opportunity_id)
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))'''

new = '''@router.get("/v61/opportunities/{opportunity_id}/execution-plan")
def get_execution_plan(
    opportunity_id: int,
    db: Session = Depends(get_db),
    _: dict = Depends(get_current_user),
):
    from app.services.opportunity_intelligence import generate_execution_plan
    try:
        return generate_execution_plan(db, opportunity_id)
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/v611/opportunities/{opportunity_id}/dossier")
def get_opportunity_dossier(
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

count = content.count(old)
print(f"Anchor found {count} time(s).")

if count != 1:
    print(f"Expected exactly 1 occurrence, found {count} -- aborting without changes.")
else:
    content = content.replace(old, new, 1)
    with open(PATH, "w") as f:
        f.write(content)
    print("Patched successfully: /strategic-outcome/v611/opportunities/{opportunity_id}/dossier route added.")
