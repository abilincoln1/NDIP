"""
NDIP V6.0A Phase E Bug Fix -- Engagement Pathway Stakeholder Ordering

BUG: generate_engagement_pathway() picked "first contact" / "second
contact" from opp.stakeholders_json in raw stored order (which reflects
mention-count order from opportunity DETECTION), rather than from the
opportunity's actual computed alignment scores. This caused the
engagement sequence to recommend approaching a Moderate-alignment
stakeholder before a Strong-alignment one, directly contradicting the
"Who matters?" ranking shown elsewhere in the same execution plan.

FIX: re-rank stakeholders by their stored OpportunityAlignmentScore
(falling back to stored order only if no alignment scores exist yet)
before selecting first/second contact.

This patches the live file directly in the running container -- run this
once to apply the fix, which edits
/app/app/services/opportunity_intelligence.py in place.

Run: docker exec agora-backend-1 python scripts/fix_pathway_ordering.py
"""
import re

PATH = "/app/app/services/opportunity_intelligence.py"

with open(PATH, "r") as f:
    content = f.read()

old_block = '''    stakeholders = []
    if opp.stakeholders_json:
        try:
            stakeholders = json.loads(opp.stakeholders_json)
        except (json.JSONDecodeError, TypeError):
            pass

    pathway = EngagementPathway(opportunity_id=opportunity_id, is_current=True)
    db.add(pathway)
    db.flush()

    first_contact = stakeholders[0]["name"] if stakeholders else None
    second_contact = stakeholders[1]["name"] if len(stakeholders) > 1 else None'''

new_block = '''    stakeholders = []
    if opp.stakeholders_json:
        try:
            stakeholders = json.loads(opp.stakeholders_json)
        except (json.JSONDecodeError, TypeError):
            pass

    # Bug fix (V6.0A activation cycle): stakeholders_json is stored in
    # DETECTION order (raw mention count at the time the opportunity was
    # first found), which has no relationship to alignment strength. The
    # engagement pathway's "first contact" must reflect the opportunity's
    # actual computed alignment ranking, not the incidental detection
    # order -- otherwise this function can recommend approaching a
    # Moderate-alignment stakeholder before a Strong-alignment one,
    # contradicting the "Who matters?" section of the same execution plan.
    from app.models.models import OpportunityAlignmentScore as _OAS
    alignment_rows = db.query(_OAS).filter(_OAS.opportunity_id == opportunity_id).order_by(_OAS.alignment_score.desc()).all()
    if alignment_rows:
        alignment_order_ids = [row.stakeholder_id for row in alignment_rows]
        stakeholder_lookup = {s.get("stakeholder_id"): s for s in stakeholders}
        stakeholders = [stakeholder_lookup[sid] for sid in alignment_order_ids if sid in stakeholder_lookup]

    pathway = EngagementPathway(opportunity_id=opportunity_id, is_current=True)
    db.add(pathway)
    db.flush()

    first_contact = stakeholders[0]["name"] if stakeholders else None
    second_contact = stakeholders[1]["name"] if len(stakeholders) > 1 else None'''

if old_block not in content:
    print("ERROR: expected code block not found -- file may already be patched, or differs from what was inspected. Aborting without changes.")
else:
    content = content.replace(old_block, new_block)
    with open(PATH, "w") as f:
        f.write(content)
    print("Patched successfully: generate_engagement_pathway now re-ranks stakeholders by alignment score before selecting first/second contact.")
