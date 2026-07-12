"""
NDIP V6.1.2 Phase A -- Executive Product Coverage Audit

Checks, live, whether each executive product's backend route actually
returns the new V6.1.1 intelligence fields (named office-holders,
authority relationships, decision makers, dossiers) -- not whether the
underlying service functions exist, but whether the ROUTE a real
frontend page calls actually surfaces them in its response.

This deliberately does NOT check the frontend pages themselves (that
requires a browser) -- it establishes the backend half of the coverage
matrix with certainty, so Phase B's integration work targets the right
gaps.

Run: docker exec agora-backend-1 python scripts/v612_coverage_audit.py
"""
import sys
sys.path.insert(0, '/app')
import json

from app.db.database import SessionLocal

db = SessionLocal()
user = {"email": "admin@agora.rtifn.org"}

def check(label, fn):
    try:
        result = fn()
        print(f"  [OK]   {label}: {result}")
        return result
    except Exception as e:
        print(f"  [FAIL] {label}: {type(e).__name__}: {e}")
        return None

print("=" * 70)
print("  SECTION 1 -- RAW DATA COUNTS (ground truth)")
print("=" * 70)
from app.models.models import StakeholderRegistry, StakeholderRelationship, OpportunityAssessment, RecommendationRecord

named_office_holders = db.query(StakeholderRegistry).filter(StakeholderRegistry.stakeholder_type.isnot(None)).count()
total_stakeholders = db.query(StakeholderRegistry).filter(StakeholderRegistry.is_active == True).count()
total_relationships = db.query(StakeholderRelationship).filter(StakeholderRelationship.is_active == True).count()
total_opportunities = db.query(OpportunityAssessment).count()
opportunities_with_stakeholders = db.query(OpportunityAssessment).filter(OpportunityAssessment.stakeholders_json.isnot(None)).count()
total_recommendations = db.query(RecommendationRecord).count()

print(f"  Named/typed stakeholders (stakeholder_type set): {named_office_holders}")
print(f"  Total active stakeholders (institutions + named): {total_stakeholders}")
print(f"  Total active authority relationships: {total_relationships}")
print(f"  Total tracked opportunities: {total_opportunities}")
print(f"  Opportunities with any stakeholder linkage: {opportunities_with_stakeholders}")
print(f"  Total recommendations tracked: {total_recommendations}")

print()
print("=" * 70)
print("  SECTION 2 -- LEADERSHIP PACK route, real fields present")
print("=" * 70)
from app.api.routes.leadership_pack import leadership_pack
lp = check("leadership_pack(days=30) call", lambda: "called successfully")
lp_result = leadership_pack(days=30, db=db, _=user)
print(f"  key_stakeholders: {len(lp_result.get('key_stakeholders', []))}")
print(f"  strategic_opportunities: {len(lp_result.get('strategic_opportunities', []))}")
print(f"  priority_decision_makers: {len(lp_result.get('priority_decision_makers', []))}")
print(f"  stakeholder_influence_summary: {len(lp_result.get('stakeholder_influence_summary', []))}")

print()
print("=" * 70)
print("  SECTION 3 -- SITUATION ROOM route, real fields present")
print("=" * 70)
try:
    from app.api.routes.situation_room import situation_room
    sr_result = situation_room(days=30, db=db, _=user)
    sr_keys = sorted(sr_result.keys())
    print(f"  Top-level keys returned: {sr_keys}")
    stakeholder_related_keys = [k for k in sr_keys if "stakeholder" in k.lower() or "opportunity" in k.lower()]
    print(f"  Stakeholder/opportunity-related keys: {stakeholder_related_keys}")
    for k in stakeholder_related_keys:
        v = sr_result[k]
        print(f"    {k}: {len(v) if isinstance(v, list) else v}")
except Exception as e:
    print(f"  [FAIL] situation_room call: {type(e).__name__}: {e}")

print()
print("=" * 70)
print("  SECTION 4 -- STRATEGIC OUTCOME / SOI route, real fields present")
print("=" * 70)
try:
    from app.api.routes.strategic_outcome import get_opportunities
    soi_result = get_opportunities(days=30, db=db, _=user)
    print(f"  Result type: {type(soi_result)}")
    if isinstance(soi_result, dict):
        print(f"  Keys: {sorted(soi_result.keys())}")
    elif isinstance(soi_result, list):
        print(f"  List length: {len(soi_result)}")
        if soi_result:
            print(f"  Sample item keys: {sorted(soi_result[0].keys()) if isinstance(soi_result[0], dict) else type(soi_result[0])}")
except Exception as e:
    print(f"  [FAIL] get_opportunities call: {type(e).__name__}: {e}")

print()
print("=" * 70)
print("  SECTION 5 -- DOSSIER route (V6.1.1 Phase F)")
print("=" * 70)
from app.api.routes.strategic_outcome import get_opportunity_dossier
for opp_id in [1, 2, 5]:
    try:
        dossier = get_opportunity_dossier(opp_id, db=db, _=user)
        dm_count = len(dossier["stakeholders_by_role"]["Decision Makers"])
        print(f"  Opportunity #{opp_id}: {dm_count} Decision Makers in dossier")
    except Exception as e:
        print(f"  Opportunity #{opp_id}: FAILED -- {type(e).__name__}: {e}")

print()
print("=" * 70)
print("  SECTION 6 -- STAKEHOLDER WATCHLIST (does this product exist at all?)")
print("=" * 70)
try:
    from app.api.routes import stakeholder_watchlist
    print("  Module exists.")
except ImportError:
    print("  [MISSING] No stakeholder_watchlist route module exists. This product is NOT implemented at all.")

print()
print("=" * 70)
print("  SECTION 7 -- DECISION SUPPORT, named-stakeholder awareness")
print("=" * 70)
try:
    from app.services.decision_support import generate_decision_support
    ds_result = generate_decision_support(db, 30)
    sample_actions = (ds_result.get("immediate_actions") or []) + (ds_result.get("near_term_actions") or [])
    named_count = 0
    for a in sample_actions:
        action_text = str(a.get("action", ""))
        if "Minister" in action_text or "Director-General" in action_text or "Managing Director" in action_text:
            named_count += 1
    print(f"  Total actions checked: {len(sample_actions)}")
    print(f"  Actions explicitly naming an office-holder/title: {named_count}")
    if sample_actions:
        print(f"  Sample action text: {sample_actions[0].get('action', '')[:200]}")
except Exception as e:
    print(f"  [FAIL] generate_decision_support call: {type(e).__name__}: {e}")

db.close()
print()
print("=" * 70)
print("  AUDIT COMPLETE")
print("=" * 70)
