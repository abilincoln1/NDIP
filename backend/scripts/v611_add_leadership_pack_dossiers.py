"""
NDIP V6.1.1 Phase H -- Leadership Pack enhancement: add dossier-derived
Decision Makers / Authority Map summary, per spec, without touching any
existing field.

Anchor confirmed live via sed extraction this session, exact text match.

Run: docker exec agora-backend-1 python scripts/v611_add_leadership_pack_dossiers.py
"""
PATH = "/app/app/api/routes/leadership_pack.py"

with open(PATH, "r") as f:
    content = f.read()

old = '''    try:
        from app.services.stakeholder_influence import get_top_influence_stakeholders, get_emerging_stakeholders
        _influence_ranked = get_top_influence_stakeholders(db, limit=50, days=min(days, 30))
        result["stakeholder_influence_summary"] = _influence_ranked[:8]
        result["emerging_stakeholders"] = get_emerging_stakeholders(db, limit=5, days=min(days, 30), _precomputed_ranked=_influence_ranked)
    except Exception:
        result["stakeholder_influence_summary"] = []
        result["emerging_stakeholders"] = []'''

new = '''    try:
        from app.services.stakeholder_influence import get_top_influence_stakeholders, get_emerging_stakeholders
        _influence_ranked = get_top_influence_stakeholders(db, limit=50, days=min(days, 30))
        result["stakeholder_influence_summary"] = _influence_ranked[:8]
        result["emerging_stakeholders"] = get_emerging_stakeholders(db, limit=5, days=min(days, 30), _precomputed_ranked=_influence_ranked)
    except Exception:
        result["stakeholder_influence_summary"] = []
        result["emerging_stakeholders"] = []
    # V6.1.1 Phase H — Priority Stakeholders / Decision Makers / Authority Map.
    # Best-effort: derives from the same OpportunityAssessment rows already
    # fetched above via get_top_opportunities, classifying each opportunity's
    # required_stakeholders by their real stakeholder_type into the dossier's
    # Decision Makers / Funding Sources / Implementation buckets. Does not
    # recompute alignment or readiness -- reuses generate_opportunity_dossier,
    # which itself reuses the existing V6.0A execution-plan engine.
    try:
        from app.services.opportunity_dossier import generate_opportunity_dossier
        priority_decision_makers = []
        seen_names = set()
        for opp in result.get("strategic_opportunities", [])[:5]:
            opp_id = opp.get("id") or opp.get("opportunity_id")
            if opp_id is None:
                continue
            try:
                dossier = generate_opportunity_dossier(db, opp_id)
            except Exception:
                continue
            for s in dossier["stakeholders_by_role"].get("Decision Makers", []):
                if s["name"] not in seen_names:
                    priority_decision_makers.append({
                        "name": s["name"],
                        "stakeholder_type": s["stakeholder_type"],
                        "alignment_score": s["alignment_score"],
                        "related_opportunity": dossier["opportunity_assessment"],
                    })
                    seen_names.add(s["name"])
        result["priority_decision_makers"] = priority_decision_makers[:8]
    except Exception:
        result["priority_decision_makers"] = []'''

count = content.count(old)
print(f"Anchor found {count} time(s).")

if count != 1:
    print(f"Expected exactly 1 occurrence, found {count} -- aborting without changes.")
else:
    content = content.replace(old, new, 1)
    with open(PATH, "w") as f:
        f.write(content)
    print("Patched successfully: priority_decision_makers field added to Leadership Pack.")
