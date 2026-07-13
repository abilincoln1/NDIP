"""
NDIP Leadership Pack API v5.1
Board-ready 5-page intelligence product.
Page 1: Executive Summary (What happened / Why it matters / Key changes)
Page 2: Strategic Narrative Assessment
Page 3: Strategic Risks
Page 4: Strategic Opportunities
Page 5: Confidence & Evidence
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from datetime import datetime, timezone
from app.db.database import get_db
from app.core.security import get_current_user
from app.services.cache import get_cached, set_cached, cache_key, TTL_LEADERSHIP_PACK
from app.analytics.strategic_narratives import get_narrative_analysis
from app.analytics.engine import compute_all_metrics
from app.services.source_quality import get_source_quality_report, get_data_quality_report
from app.services.risk_opportunity import detect_all_risks, detect_all_opportunities
from app.services.narrative_intelligence import generate_situation_room
from app.services.materialised_reads import get_materialised_top_influence_stakeholders
from app.services.stakeholder_influence import get_emerging_stakeholders

router = APIRouter(prefix="/leadership-pack", tags=["leadership-pack"])


@router.get("/")
def leadership_pack(
    days: int = Query(7, ge=1, le=30),
    db: Session = Depends(get_db),
    _: dict = Depends(get_current_user),
):
    ck = cache_key("leadership-pack", f"days={days}")
    cached = get_cached(ck)
    if cached:
        cached["_cached"] = True
        return cached
    from app.services.interpretation_engine import (
        generate_differentiated_assessment,
        generate_comparative_intelligence,
        generate_narrative_competition_analysis,
        generate_outlook_engine,
    )
    narratives = get_narrative_analysis(db, days)
    metrics = compute_all_metrics(db, max(days, 30))
    situation = generate_situation_room(db, days)
    source_quality = get_source_quality_report(db, days)
    data_quality = get_data_quality_report(db)
    risks = detect_all_risks(db, days)
    opportunities = detect_all_opportunities(db, days)
    # Full narrative assessments
    assessments = [generate_differentiated_assessment(n) for n in narratives[:10]]
    comparisons = generate_comparative_intelligence(narratives)
    competition = generate_narrative_competition_analysis(narratives)
    outlook = generate_outlook_engine(narratives, days, risks, opportunities)
    # Diaspora / National / Election split
    diaspora_assessment = next((a for a in assessments if a["narrative"] == "Global Nigerian Engagement"), None)
    national_assessments = [a for a in assessments if a["narrative"] in (
        "Governance", "Economy", "Security", "Elections & Democracy",
        "Energy", "Infrastructure", "Education", "Health", "Investment"
    )]
    election_assessment = next((a for a in assessments if a["narrative"] == "Elections & Democracy"), None)
    # Confidence statement
    limitations = []
    if source_quality["source_count"] < 8:
        limitations.append(f"Intelligence draws from {source_quality['source_count']} active sources — expanding source coverage would improve narrative breadth.")
    if data_quality["nlp_rate"] < 95:
        limitations.append(f"NLP processing rate is {data_quality['nlp_rate']}% — a small proportion of ingested records may not be fully analysed.")
    if days < 7:
        limitations.append(f"This briefing covers only {days} days — a longer window would provide more reliable trend data.")
    if not limitations:
        limitations.append("No significant data quality limitations identified for this reporting period.")
    # National context
    nat_context = situation.get("national_context", "") or ""
    result = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "period_days": days,
        "version": "5.1",
        # PAGE 1 — Executive Summary
        "executive_summary": situation["executive_summary"],
        "what_matters_most": situation.get("what_matters_most", ""),
        "significant_changes": situation.get("significant_changes", []),
        "national_context": nat_context,
        "comparative_intelligence": comparisons,
        "competition_analysis": competition,
        "key_findings": situation.get("key_findings", []),
        # PAGE 2 — Strategic Narrative Assessment
        "narrative_assessments": assessments,
        "diaspora_assessment": diaspora_assessment,
        "national_assessments": national_assessments,
        "election_assessment": election_assessment,
        "narrative_share_of_voice": situation.get("narrative_share_of_voice", []),
        # PAGE 3 — Strategic Risks
        "risks": sorted(risks, key=lambda x: x.get("level_order", 3)),
        # PAGE 4 — Strategic Opportunities
        "opportunities": opportunities,
        # PAGE 5 — Outlook + Confidence
        "outlook": outlook,
        "confidence_statement": {
            "overall_rating": source_quality["overall_confidence_label"],
            "overall_score": round(source_quality["overall_confidence"] * 100),
            "data_quality": data_quality["overall_quality"],
            "source_coverage": f"{source_quality['source_count']} active sources",
            "source_diversity": "High" if source_quality["source_count"] >= 8 else "Moderate" if source_quality["source_count"] >= 4 else "Limited",
            "evidence_volume": f"{source_quality['total_records']:,} records analysed",
            "nlp_success_rate": f"{source_quality['processing_rate']}%",
            "data_freshness": "Last 24 hours" if days <= 1 else f"Last {days} days",
            "limitations": limitations,
            "summary": source_quality["summary"],
        },
        "metrics": {
            "engagement_index": metrics["engagement_index"],
            "sentiment_score": metrics["sentiment_score"],
            "total_participants": metrics["total_participants"],
            "total_records": source_quality["total_records"],
            "source_count": source_quality["source_count"],
        },
    }
    # Add V5.3 modules
    try:
        from app.services.watchlist import generate_watchlist
        result["watchlist"] = generate_watchlist(db, days)
    except Exception:
        result["watchlist"] = {"items": [], "summary": "Watchlist unavailable"}
    try:
        from app.services.gnei import generate_gnei_intelligence
        result["gnei"] = generate_gnei_intelligence(db, days)
    except Exception:
        result["gnei"] = None
    try:
        from app.services.strategic_importance import score_all_narratives, generate_trigger_attribution
        result["strategic_importance"] = score_all_narratives(narratives)
        result["trigger_attributions"] = generate_trigger_attribution(narratives, db, days)
    except Exception:
        result["strategic_importance"] = []
        result["trigger_attributions"] = []
    # V5.6 — Decision Support Performance (Executive Learning Loop)
    try:
        from app.services.recommendation_tracker import get_decision_support_performance_summary
        result["decision_support_performance"] = get_decision_support_performance_summary(db)
    except Exception:
        result["decision_support_performance"] = None
    # V5.8 Phase H — Intelligence Performance (platform-wide learning summary)
    try:
        from app.services.intelligence_learning import run_intelligence_learning_cycle
        result["intelligence_performance"] = run_intelligence_learning_cycle(db)
    except Exception:
        result["intelligence_performance"] = None

    # V6.0 Phase G — Leadership Pack enhancements: Strategic Opportunities,
    # Key Stakeholders, Engagement Priorities, Opportunity Pipeline. Best
    # effort: Leadership Pack must continue working even if V6.0 data is
    # unavailable or the registries are empty.
    try:
        from app.services.opportunity_intelligence import get_top_opportunities, get_opportunity_pipeline_summary
        from app.services.stakeholder_registry import get_top_stakeholders

        result["strategic_opportunities"] = get_top_opportunities(db, limit=5)
        result["key_stakeholders"] = get_top_stakeholders(db, limit=8, days=min(days, 30))
        result["engagement_priorities"] = [
            s for s in result["key_stakeholders"] if s.get("monitoring_priority") in ("High", "Critical")
        ][:5]
        result["opportunity_pipeline"] = get_opportunity_pipeline_summary(db)
    except Exception:
        result["strategic_opportunities"] = []
        result["key_stakeholders"] = []
        result["engagement_priorities"] = []
        result["opportunity_pipeline"] = {}

    # V6.1 Phase H — Stakeholder Influence Summary and Emerging Stakeholders.
    # Separate try/except from the V6.0 block above: V6.1's influence engine
    # is a different module, so a failure here should not affect the V6.0
    # fields that already work.
    try:
        _influence_ranked = get_materialised_top_influence_stakeholders(db, limit=50, days=min(days, 30))
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
        result["priority_decision_makers"] = []

    # V5.8 Phase F — Narrative Intelligence module self-evaluation.
    # Track growth predictions for the top 3 narratives by share of voice,
    # once per Leadership Pack generation (not per get_narrative_analysis call,
    # which would create excessive duplicate tracking given how many modules
    # call that shared utility function).
    try:
        from app.services.recommendation_tracker import record_recommendation
        for n in narratives[:3]:
            direction = n.get("momentum_direction", "stable")
            category = "MONITOR" if direction in ("rising", "stable") else "MONITOR"
            record_recommendation(
                db,
                narrative=n["narrative"],
                recommendation_text=(
                    f"{n['narrative']} discourse is {direction} (momentum {n['momentum']:+.0f}%) "
                    f"at {n['share_of_voice']}% share of voice — expected to continue this trajectory "
                    f"over the next reporting period."
                ),
                category=category,
                priority="Medium",
                confidence=n.get("confidence_label", "Medium"),
                time_horizon="14 days",
                supporting_evidence=f"{n['count']} mentions across {n['source_count']} sources",
                expected_outcome=f"Share of voice and momentum direction consistent with current {direction} trend",
                trigger_metric_name="share_of_voice",
                trigger_metric_value=float(n["share_of_voice"]),
                period_days=days,
                module="narrative_intelligence",
            )
    except Exception:
        try:
            db.rollback()
        except Exception:
            pass
    # V5.8 Phase F — Leadership Pack module self-evaluation.
    # Track the Pack's own 7-day outlook as an evaluable recommendation,
    # distinct from per-narrative tracking (tagged narrative_intelligence above).
    try:
        from app.services.recommendation_tracker import record_recommendation
        top_narrative = narratives[0] if narratives else None
        record_recommendation(
            db,
            narrative=top_narrative["narrative"] if top_narrative else None,
            recommendation_text=outlook.get("7_day", "") if isinstance(outlook, dict) else str(outlook),
            category="MONITOR",
            priority="Medium",
            confidence="Medium",
            time_horizon="7 days",
            supporting_evidence=f"Leadership Pack strategic outlook, {len(narratives)} narratives assessed",
            expected_outcome="Discourse trajectory consistent with 7-day outlook assessment",
            trigger_metric_name="share_of_voice",
            trigger_metric_value=float(top_narrative["share_of_voice"]) if top_narrative else None,
            period_days=days,
            module="leadership_pack",
        )
    except Exception:
        try:
            db.rollback()
        except Exception:
            pass
    set_cached(ck, result, TTL_LEADERSHIP_PACK)
    return result
