"""
NDIP V6.1.2 Phase B -- Strategic Opportunity Intelligence dashboard
integration. Adds dossier-derived Decision Makers / Funding Sources /
Implementation breakdown to the real, confirmed consumer-facing
/strategic-outcome/dashboard route, reusing generate_opportunity_dossier
(no new computation engine, per the spec's explicit rule).

Anchor confirmed live via sed extraction this session.

Run: docker exec agora-backend-1 python scripts/v612_add_soi_dossier_integration.py
"""
PATH = "/app/app/api/routes/strategic_outcome.py"

with open(PATH, "r") as f:
    content = f.read()

old = '''    return {
        "period_days": days,
        "generation_summary": generation_result,
        "top_opportunities": top_opportunities,
        "stakeholder_rankings": top_stakeholders,
        "engagement_priorities": engagement_priorities,
        "opportunity_pipeline": pipeline_summary_data,
        "strategic_value_distribution": value_counts,
        "decision_quality_metrics": learning_cycle.get("decision_quality_metrics"),
        "strategic_outcome_metrics": learning_cycle.get("strategic_outcome_metrics"),
        "platform_learning_score": learning_cycle.get("platform_learning_score"),
    }'''

new = '''    # V6.1.2 Phase B -- dossier-derived Decision Makers / Funding Sources /
    # Implementation breakdown per opportunity, reusing
    # generate_opportunity_dossier (no new computation engine; classifies
    # the same already-computed alignment data by real stakeholder_type).
    opportunity_dossiers = []
    try:
        from app.services.opportunity_dossier import generate_opportunity_dossier
        for o in top_opportunities[:10]:
            opp_id = o.get("id") or o.get("opportunity_id")
            if opp_id is None:
                continue
            try:
                dossier = generate_opportunity_dossier(db, opp_id)
                opportunity_dossiers.append({
                    "opportunity_id": opp_id,
                    "title": dossier["opportunity_assessment"],
                    "decision_makers": dossier["stakeholders_by_role"]["Decision Makers"],
                    "funding_sources": dossier["stakeholders_by_role"]["Funding Sources"],
                    "implementation": dossier["stakeholders_by_role"]["Implementation"],
                    "data_quality_notes": dossier["data_quality_notes"],
                })
            except Exception:
                continue
    except Exception:
        opportunity_dossiers = []

    return {
        "period_days": days,
        "generation_summary": generation_result,
        "top_opportunities": top_opportunities,
        "stakeholder_rankings": top_stakeholders,
        "engagement_priorities": engagement_priorities,
        "opportunity_pipeline": pipeline_summary_data,
        "strategic_value_distribution": value_counts,
        "decision_quality_metrics": learning_cycle.get("decision_quality_metrics"),
        "strategic_outcome_metrics": learning_cycle.get("strategic_outcome_metrics"),
        "platform_learning_score": learning_cycle.get("platform_learning_score"),
        "opportunity_dossiers": opportunity_dossiers,
    }'''

count = content.count(old)
print(f"Anchor found {count} time(s).")

if count != 1:
    print(f"Expected exactly 1 occurrence, found {count} -- aborting without changes.")
else:
    content = content.replace(old, new, 1)
    with open(PATH, "w") as f:
        f.write(content)
    print("Patched successfully: opportunity_dossiers field added to /strategic-outcome/dashboard.")
