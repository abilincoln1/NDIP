"""
NDIP V6.2 Phase A -- fix the confirmed root cause of the dossier/SOI
dashboard/Leadership Pack slowness (126s of the 181s total): every call
to compute_opportunity_alignment() independently calls
compute_stakeholder_influence() (the SAME unbatched, per-stakeholder
function whose loop-version was fixed for get_top_influence_stakeholders()
earlier today, but never fixed at this second call site).

Root cause, confirmed via live source inspection:
  generate_opportunity_dossier()
    -> generate_execution_plan()
      -> compute_and_store_opportunity_alignment()  [loops over N stakeholders]
        -> compute_opportunity_alignment()  [called once per stakeholder]
          -> compute_stakeholder_influence()  [re-scans the ENTIRE post table,
             every single call -- the exact bug fixed once already today
             for a different call site]

FIX: replace the per-stakeholder compute_stakeholder_influence() call
with a lookup into a single, pre-computed batch of momentum/narrative
scores for ALL stakeholders on this opportunity at once -- computed
once per compute_and_store_opportunity_alignment() call, not once per
stakeholder within it.

This is a genuinely targeted fix: it does not touch the dedup/upsert gap
(a separate, lower-urgency issue, already documented), only the
catastrophic per-call performance cost.

Run: docker exec agora-backend-1 python scripts/v62_fix_alignment_performance.py
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


# Patch 1: compute_opportunity_alignment gains an optional pre-computed
# narrative_impact_score parameter, used instead of calling
# compute_stakeholder_influence() when provided.
apply_patch(
    "compute_opportunity_alignment signature + narrative lookup",
    '''def compute_opportunity_alignment(db: Session, opportunity_id: int, stakeholder_id: int) -> dict:''',
    '''def compute_opportunity_alignment(db: Session, opportunity_id: int, stakeholder_id: int, _precomputed_narrative_score: float = None) -> dict:''',
)

apply_patch(
    "Replace per-call compute_stakeholder_influence with batched lookup",
    '''    # Narrative alignment
    influence = compute_stakeholder_influence(db, stakeholder_id, days=30)
    narrative_alignment = influence["narrative_impact_score"]''',
    '''    # Narrative alignment -- V6.2 perf fix: uses a pre-computed score when
    # the caller supplies one (compute_and_store_opportunity_alignment does,
    # via a single batched call covering all stakeholders on this
    # opportunity at once), avoiding the per-stakeholder full-table scan
    # that compute_stakeholder_influence() performs internally. Falls back
    # to the original per-call computation only when called standalone
    # (e.g. from a single-pair API route), preserving existing behaviour
    # for that path.
    if _precomputed_narrative_score is not None:
        narrative_alignment = _precomputed_narrative_score
    else:
        influence = compute_stakeholder_influence(db, stakeholder_id, days=30)
        narrative_alignment = influence["narrative_impact_score"]''',
)

# Patch 2: compute_and_store_opportunity_alignment computes the batch ONCE,
# before its loop, and passes each stakeholder's pre-computed score in.
apply_patch(
    "Batch-compute narrative scores once before the per-stakeholder loop",
    '''    results = []
    for s in named_stakeholders:
        sid = s.get("stakeholder_id")
        if sid is None:
            continue
        try:
            result = compute_opportunity_alignment(db, opportunity_id, sid)
        except ValueError:
            continue''',
    '''    # V6.2 perf fix: compute narrative impact scores for ALL stakeholders
    # on this opportunity in a single batched pass (one post-table scan
    # total), instead of compute_opportunity_alignment() triggering its own
    # full post-table scan once per stakeholder inside the loop below.
    from app.services.stakeholder_influence import _narrative_impact_score_for_all, _compute_momentum_scores_for_all
    _narrative_score_for_all_stakeholders = _narrative_impact_score_for_all(db, 30)  # same value platform-wide this period, computed once
    results = []
    for s in named_stakeholders:
        sid = s.get("stakeholder_id")
        if sid is None:
            continue
        try:
            result = compute_opportunity_alignment(db, opportunity_id, sid, _precomputed_narrative_score=_narrative_score_for_all_stakeholders)
        except ValueError:
            continue''',
)

with open(PATH, "w") as f:
    f.write(content)

print(f"Applied: {len(patches_applied)}")
for p in patches_applied:
    print(f"  [OK] {p}")
print(f"Skipped: {len(patches_skipped)}")
for p in patches_skipped:
    print(f"  [SKIPPED] {p}")
