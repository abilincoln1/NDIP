"""
NDIP V6.2 -- fix the compute_opportunity_readiness signature patch using
the correct, blank-line-accurate anchor (confirmed via live diagnostic).

URGENT: the call site already passes _precomputed_alignment_results= as
a keyword argument; this function currently does NOT accept it, meaning
every dossier call is presently broken until this patch applies.

Run: docker exec agora-backend-1 python scripts/v62_fix_readiness_signature_v2.py
"""
PATH = "/app/app/services/opportunity_intelligence.py"

with open(PATH, "r") as f:
    content = f.read()

old = '''def compute_opportunity_readiness(db: Session, opportunity_id: int) -> dict:
    """
    Phase E: six-factor readiness scoring. implementation_complexity is
    scored such that HIGHER complexity REDUCES readiness (it is inverted
    before being added to the composite).
    """
    from app.models.models import OpportunityPipelineEvent

    opp = db.query(OpportunityAssessment).filter(OpportunityAssessment.id == opportunity_id).first()
    if not opp:
        raise ValueError("Opportunity not found")

    alignment_results = compute_and_store_opportunity_alignment(db, opportunity_id)'''

new = '''def compute_opportunity_readiness(db: Session, opportunity_id: int, _precomputed_alignment_results: list = None) -> dict:
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

    alignment_results = _precomputed_alignment_results if _precomputed_alignment_results is not None else compute_and_store_opportunity_alignment(db, opportunity_id)'''

count = content.count(old)
print(f"Anchor found {count} time(s).")

if count != 1:
    print(f"Expected exactly 1 occurrence, found {count} -- aborting without changes.")
else:
    content = content.replace(old, new, 1)
    with open(PATH, "w") as f:
        f.write(content)
    print("Patched successfully: compute_opportunity_readiness now accepts pre-computed alignment results.")
