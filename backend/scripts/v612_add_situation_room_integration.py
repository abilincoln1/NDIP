"""
NDIP V6.1.2 Phase B -- Situation Room integration. Adds priority
stakeholders, responsible institutions, and emerging decision makers --
confirmed live as completely absent before this patch (Section 3 of the
coverage audit showed zero stakeholder/opportunity-related keys).

Reuses existing V6.0A/V6.1.1 services (get_top_stakeholders,
get_top_influence_stakeholders, generate_opportunity_dossier) -- no new
computation engine, per spec.

Anchor confirmed live via sed extraction this session, exact text match.

Run: docker exec agora-backend-1 python scripts/v612_add_situation_room_integration.py
"""
PATH = "/app/app/api/routes/situation_room.py"

with open(PATH, "r") as f:
    content = f.read()

old = '''    try:
        from app.services.risk_opportunity import detect_all_risks, detect_all_opportunities
        base["risks"] = detect_all_risks(db, days)
        base["opportunities"] = detect_all_opportunities(db, days)
    except Exception as e:
        base["risks"] = []
        base["opportunities"] = []
    return base'''

new = '''    try:
        from app.services.risk_opportunity import detect_all_risks, detect_all_opportunities
        base["risks"] = detect_all_risks(db, days)
        base["opportunities"] = detect_all_opportunities(db, days)
    except Exception as e:
        base["risks"] = []
        base["opportunities"] = []
    # V6.1.2 Phase B -- Stakeholder Landscape: priority stakeholders,
    # emerging decision makers, and opportunity-linked decision makers.
    # Confirmed live (coverage audit) that this product previously had NO
    # stakeholder/opportunity-related fields at all. Reuses existing
    # V6.0A/V6.1.1 services; introduces no new computation engine.
    try:
        from app.services.stakeholder_registry import get_top_stakeholders
        from app.services.stakeholder_influence import get_top_influence_stakeholders, get_emerging_stakeholders
        base["priority_stakeholders"] = get_top_stakeholders(db, limit=8, days=min(days, 30))
        _influence_ranked = get_top_influence_stakeholders(db, limit=50, days=min(days, 30))
        base["emerging_decision_makers"] = [
            s for s in get_emerging_stakeholders(db, limit=10, days=min(days, 30), _precomputed_ranked=_influence_ranked)
            if s.get("stakeholder_type") is not None
        ][:5]
    except Exception:
        base["priority_stakeholders"] = []
        base["emerging_decision_makers"] = []
    try:
        from app.services.opportunity_dossier import generate_opportunity_dossier
        from app.services.opportunity_intelligence import get_top_opportunities
        opportunity_decision_makers = []
        seen = set()
        for o in get_top_opportunities(db, limit=5):
            opp_id = o.get("id") or o.get("opportunity_id")
            if opp_id is None:
                continue
            try:
                dossier = generate_opportunity_dossier(db, opp_id)
            except Exception:
                continue
            for s in dossier["stakeholders_by_role"].get("Decision Makers", []):
                if s["name"] not in seen:
                    opportunity_decision_makers.append({**s, "related_opportunity": dossier["opportunity_assessment"]})
                    seen.add(s["name"])
        base["opportunity_decision_makers"] = opportunity_decision_makers[:8]
    except Exception:
        base["opportunity_decision_makers"] = []
    return base'''

count = content.count(old)
print(f"Anchor found {count} time(s).")

if count != 1:
    print(f"Expected exactly 1 occurrence, found {count} -- aborting without changes.")
else:
    content = content.replace(old, new, 1)
    with open(PATH, "w") as f:
        f.write(content)
    print("Patched successfully: priority_stakeholders, emerging_decision_makers, opportunity_decision_makers added to Situation Room.")
