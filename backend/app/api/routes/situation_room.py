from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.core.security import get_current_user
from app.services.cache import get_cached, set_cached, cache_key, TTL_SITUATION_ROOM, TTL_BRIEF

router = APIRouter(prefix="/situation-room", tags=["situation-room"])


@router.get("/")
def situation_room(
    days: int = Query(7, ge=1, le=30),
    db: Session = Depends(get_db),
    _: dict = Depends(get_current_user),
):
    ck = cache_key("situation-room", f"days={days}")
    cached = get_cached(ck)
    if cached:
        cached["_cached"] = True
        return cached
    try:
        from app.services.narrative_intelligence import generate_situation_room
        base = generate_situation_room(db, days)
    except Exception as e:
        base = {"error": str(e), "executive_summary": f"Error loading situation room: {e}", "key_findings": [], "narrative_share_of_voice": [], "risks": [], "opportunities": [], "emerging_topics": [], "significant_changes": [], "outlook": "", "what_matters_most": "", "recommended_monitoring": [], "generated_at": "", "period_days": days}
    try:
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
    return base


@router.get("/brief/{period}")
def executive_brief(
    period: str,
    db: Session = Depends(get_db),
    _: dict = Depends(get_current_user),
):
    days_map = {"daily": 1, "weekly": 7, "monthly": 30}
    days = days_map.get(period, 7)
    ck = cache_key("brief", f"period={period}")
    cached = get_cached(ck)
    if cached:
        cached["_cached"] = True
        return cached
    try:
        from app.services.narrative_intelligence import generate_brief
        base = generate_brief(db, period, days)
    except Exception as e:
        import traceback
        base = {
            "brief_type": period, "period_days": days,
            "generated_at": "", "executive_summary": f"Brief generation error: {str(e)}",
            "key_findings": [], "engagement_overview": "", "geographic_overview": "",
            "narrative_analysis": [], "narrative_share_of_voice": [],
            "sentiment_analysis": "", "risks": [], "opportunities": [],
            "emerging_topics": [], "recommended_monitoring": [], "outlook": "",
            "error_detail": traceback.format_exc()
        }
    
    try:
        from app.services.comparative_intelligence import get_narrative_comparisons
        base["comparisons"] = get_narrative_comparisons(db, days)
    except Exception as e:
        base["comparisons"] = {}

    try:
        from app.services.source_quality import get_source_quality_report, get_data_quality_report
        base["source_quality"] = get_source_quality_report(db, days)
        base["data_quality"] = get_data_quality_report(db)
    except Exception as e:
        base["source_quality"] = None
        base["data_quality"] = None

    try:
        from app.services.risk_opportunity import detect_all_risks, detect_all_opportunities
        base["risks"] = detect_all_risks(db, days)
        base["opportunities"] = detect_all_opportunities(db, days)
    except Exception as e:
        base["risks"] = []
        base["opportunities"] = []

    return base


@router.get("/comparisons")
def narrative_comparisons(
    days: int = Query(7, ge=1, le=90),
    db: Session = Depends(get_db),
    _: dict = Depends(get_current_user),
):
    from app.services.comparative_intelligence import get_narrative_comparisons
    return get_narrative_comparisons(db, days)


@router.get("/source-quality")
def source_quality(
    days: int = Query(7, ge=1, le=90),
    db: Session = Depends(get_db),
    _: dict = Depends(get_current_user),
):
    from app.services.source_quality import get_source_quality_report
    return get_source_quality_report(db, days)


@router.get("/data-quality")
def data_quality(
    db: Session = Depends(get_db),
    _: dict = Depends(get_current_user),
):
    from app.services.source_quality import get_data_quality_report
    return get_data_quality_report(db)


@router.get("/risks")
def all_risks(
    days: int = Query(7, ge=1, le=30),
    db: Session = Depends(get_db),
    _: dict = Depends(get_current_user),
):
    from app.services.risk_opportunity import detect_all_risks
    return {"risks": detect_all_risks(db, days)}


@router.get("/opportunities")
def all_opportunities(
    days: int = Query(7, ge=1, le=30),
    db: Session = Depends(get_db),
    _: dict = Depends(get_current_user),
):
    from app.services.risk_opportunity import detect_all_opportunities
    return {"opportunities": detect_all_opportunities(db, days)}
