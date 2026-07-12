"""
NDIP V6.2 -- fix the second confirmed duplication: compute_opportunity_readiness()
independently re-calls compute_and_store_opportunity_alignment(), which
generate_execution_plan() had already called once. This pays the
(now-fixed-but-still-real) narrative-scan cost twice per dossier.

FIX: compute_opportunity_readiness() accepts an optional pre-computed
alignment_results list; generate_execution_plan() passes through the one
it already has, eliminating the second computation entirely. Falls back
to its own computation when called standalone (preserving existing
behaviour for any other caller).

Run: docker exec agora-backend-1 python scripts/v62_fix_readiness_duplication.py
"""
PATH = "/app/app/services/opportunity_intelligence.py"

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
    "compute_opportunity_readiness signature + reuse pre-computed alignment",
    '''def compute_opportunity_readiness(db: Session, opportunity_id: int) -> dict:
    """
    Phase E: six-factor readiness scoring. implementation_complexity is
    scored such that HIGHER complexity REDUCES readiness (it is inverted
    before being added to the composite).
    """
    from app.models.models import OpportunityPipelineEvent
    opp = db.query(OpportunityAssessment).filter(OpportunityAssessment.id == opportunity_id).first()
    if not opp:
        raise ValueError("Opportunity not found")
    alignment_results = compute_and_store_opportunity_alignment(db, opportunity_id)''',
    '''def compute_opportunity_readiness(db: Session, opportunity_id: int, _precomputed_alignment_results: list = None) -> dict:
    """
    Phase E: six-factor readiness scoring. implementation_complexity is
    scored such that HIGHER complexity REDUCES readiness (it is inverted
    before being added to the composite).

    V6.2 perf fix: accepts an optional pre-computed alignment_results list
    (generate_execution_plan() already computes this once and passes it
    through), avoiding a second, fully redundant call to
    compute_and_store_opportunity_alignment() -- confirmed live this
    session to independently cost ~4s on its own, paid twice per dossier
    before this fix.
    """
    from app.models.models import OpportunityPipelineEvent
    opp = db.query(OpportunityAssessment).filter(OpportunityAssessment.id == opportunity_id).first()
    if not opp:
        raise ValueError("Opportunity not found")
    alignment_results = _precomputed_alignment_results if _precomputed_alignment_results is not None else compute_and_store_opportunity_alignment(db, opportunity_id)''',
)

apply_patch(
    "generate_execution_plan -- pass alignment_results through to readiness",
    '''    alignment_results = compute_and_store_opportunity_alignment(db, opportunity_id)
    readiness = compute_opportunity_readiness(db, opportunity_id)''',
    '''    alignment_results = compute_and_store_opportunity_alignment(db, opportunity_id)
    readiness = compute_opportunity_readiness(db, opportunity_id, _precomputed_alignment_results=alignment_results)''',
)

with open(PATH, "w") as f:
    f.write(content)

print(f"Applied: {len(patches_applied)}")
for p in patches_applied:
    print(f"  [OK] {p}")
print(f"Skipped: {len(patches_skipped)}")
for p in patches_skipped:
    print(f"  [SKIPPED] {p}")
