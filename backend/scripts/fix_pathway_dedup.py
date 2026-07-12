"""
NDIP V6.0A Phase E Bug Fix #2 -- Deduplicate alignment rows in pathway ordering

BUG: compute_and_store_opportunity_alignment() writes a new
OpportunityAlignmentScore row every time it is called, with no dedup --
this is itself a separate pre-existing issue (flagged for the completion
report), but it means generate_engagement_pathway()'s alignment-based
ordering fix (applied earlier this cycle) queried ALL historical rows,
not one-per-stakeholder, causing the same stakeholder to appear multiple
times in the ranked list and "first" and "second" contact to sometimes
be the same institution.

FIX: take only the MOST RECENT alignment row per distinct stakeholder_id
before building the ranking, rather than every row ever written.

Run: docker exec agora-backend-1 python scripts/fix_pathway_dedup.py
"""
PATH = "/app/app/services/opportunity_intelligence.py"

with open(PATH, "r") as f:
    content = f.read()

old_block = '''    from app.models.models import OpportunityAlignmentScore as _OAS
    alignment_rows = db.query(_OAS).filter(_OAS.opportunity_id == opportunity_id).order_by(_OAS.alignment_score.desc()).all()
    if alignment_rows:
        alignment_order_ids = [row.stakeholder_id for row in alignment_rows]
        stakeholder_lookup = {s.get("stakeholder_id"): s for s in stakeholders}
        stakeholders = [stakeholder_lookup[sid] for sid in alignment_order_ids if sid in stakeholder_lookup]'''

new_block = '''    from app.models.models import OpportunityAlignmentScore as _OAS
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

if old_block not in content:
    print("ERROR: expected code block not found -- aborting without changes.")
else:
    content = content.replace(old_block, new_block)
    with open(PATH, "w") as f:
        f.write(content)
    print("Patched successfully: pathway ordering now dedupes to most-recent alignment row per stakeholder before ranking.")
