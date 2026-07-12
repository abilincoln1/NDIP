"""
NDIP V6.0A Phase E Bug Fix #3 -- Consistent tie-break ordering

BUG: compute_and_store_opportunity_alignment() returns ties (equal
alignment_score) in stakeholders_json order, because Python's sort is
stable and that's the original list order before sorting. The pathway
function's dedup fix (Bug Fix #2) broke ties by `computed_at` instead,
which is unrelated and effectively random relative to the "Who matters?"
section -- so a genuine tie could rank differently in the two sections of
the same execution plan.

FIX: break ties in the pathway function by stakeholders_json order too,
matching compute_and_store_opportunity_alignment()'s actual behaviour
exactly, so "Who matters?" and the engagement sequence always agree.

Run: docker exec agora-backend-1 python scripts/fix_pathway_tiebreak.py
"""
PATH = "/app/app/services/opportunity_intelligence.py"

with open(PATH, "r") as f:
    content = f.read()

old_block = '''    from app.models.models import OpportunityAlignmentScore as _OAS
    # NOTE: compute_and_store_opportunity_alignment() writes a fresh row on
    # every call with no dedup (separate, pre-existing issue, flagged for
    # the V6.0A completion report's known limitations) -- so this query can
    # return many historical rows per stakeholder. Take only the most
    # recent row per distinct stakeholder_id before ranking, or the same
    # institution can appear multiple times in the ordered list.
    all_alignment_rows = db.query(_OAS).filter(_OAS.opportunity_id == opportunity_id).order_by(_OAS.computed_at.desc()).all()
    most_recent_by_stakeholder = {}
    for row in all_alignment_rows:
        if row.stakeholder_id not in most_recent_by_stakeholder:
            most_recent_by_stakeholder[row.stakeholder_id] = row
    alignment_rows = sorted(most_recent_by_stakeholder.values(), key=lambda r: r.alignment_score, reverse=True)
    if alignment_rows:
        alignment_order_ids = [row.stakeholder_id for row in alignment_rows]
        stakeholder_lookup = {s.get("stakeholder_id"): s for s in stakeholders}
        stakeholders = [stakeholder_lookup[sid] for sid in alignment_order_ids if sid in stakeholder_lookup]'''

new_block = '''    from app.models.models import OpportunityAlignmentScore as _OAS
    # NOTE: compute_and_store_opportunity_alignment() writes a fresh row on
    # every call with no dedup (separate, pre-existing issue, flagged for
    # the V6.0A completion report's known limitations) -- so this query can
    # return many historical rows per stakeholder. Take only the most
    # recent row per distinct stakeholder_id before ranking.
    all_alignment_rows = db.query(_OAS).filter(_OAS.opportunity_id == opportunity_id).order_by(_OAS.computed_at.desc()).all()
    most_recent_by_stakeholder = {}
    for row in all_alignment_rows:
        if row.stakeholder_id not in most_recent_by_stakeholder:
            most_recent_by_stakeholder[row.stakeholder_id] = row

    # Tie-break must match compute_and_store_opportunity_alignment()'s own
    # behaviour exactly: that function does results.sort(key=alignment_score,
    # reverse=True), and Python's sort is stable, so ties fall back to
    # stakeholders_json order. Sorting here by (-score, stakeholders_json
    # position) reproduces that ordering, so "Who matters?" and this
    # engagement sequence always agree, including on genuine ties.
    stakeholders_json_order = {s.get("stakeholder_id"): i for i, s in enumerate(stakeholders)}
    alignment_rows = sorted(
        most_recent_by_stakeholder.values(),
        key=lambda r: (-r.alignment_score, stakeholders_json_order.get(r.stakeholder_id, 999)),
    )
    if alignment_rows:
        alignment_order_ids = [row.stakeholder_id for row in alignment_rows]
        stakeholder_lookup = {s.get("stakeholder_id"): s for s in stakeholders}
        stakeholders = [stakeholder_lookup[sid] for sid in alignment_order_ids if sid in stakeholder_lookup]'''

if old_block not in content:
    print("ERROR: expected code block not found -- aborting without changes.")
else:
    content = content.replace(old_block, new_block)
    with open(PATH, "w") as f:
        f.write(content)
    print("Patched successfully: pathway ordering now breaks ties using stakeholders_json position, matching compute_and_store_opportunity_alignment()'s own stable-sort tie-break exactly.")
