from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.core.security import get_current_user
from app.services.cache import get_cached, set_cached, cache_key, TTL_NATIONAL_PULSE
from app.services.election_intelligence import generate_full_election_intelligence
from app.services.national_pulse_executive import generate_national_pulse_executive
from app.services.national_pulse import compute_national_pulse
from app.services.evidence_layer import get_platform_confidence, get_narrative_evidence
from app.analytics.strategic_narratives import get_narrative_analysis

router = APIRouter(prefix="/national-pulse", tags=["national-pulse"])


@router.get("/")
def national_pulse(
    days: int = Query(7, ge=1, le=30),
    db: Session = Depends(get_db),
    _: dict = Depends(get_current_user),
):
    ck = cache_key("national-pulse", f"days={days}")
    cached = get_cached(ck)
    if cached:
        cached["_cached"] = True
        return cached
    pulse = compute_national_pulse(db, days)
    confidence = get_platform_confidence(db, days)
    pulse["platform_confidence"] = confidence
    set_cached(ck, pulse, TTL_NATIONAL_PULSE)
    return pulse


@router.get("/evidence/{narrative}")
def narrative_evidence(
    narrative: str,
    days: int = Query(7, ge=1, le=30),
    db: Session = Depends(get_db),
    _: dict = Depends(get_current_user),
):
    return get_narrative_evidence(db, narrative, days)


@router.get("/confidence")
def platform_confidence(
    days: int = Query(7, ge=1, le=30),
    db: Session = Depends(get_db),
    _: dict = Depends(get_current_user),
):
    return get_platform_confidence(db, days)


@router.get("/election-intelligence/full")
def election_intelligence_full(
    days: int = Query(30, ge=1, le=90),
    db: Session = Depends(get_db),
    _: dict = Depends(get_current_user),
):
    """Full Election Intelligence — all 10 sections."""
    ck = cache_key("election-intelligence-full", f"days={days}")
    cached = get_cached(ck)
    if cached:
        return cached
    result = generate_full_election_intelligence(db, days)
    set_cached(ck, result, TTL_NATIONAL_PULSE)
    return result


@router.get("/election-intelligence")
def election_intelligence(
    days: int = Query(30, ge=7, le=90),
    db: Session = Depends(get_db),
    _: dict = Depends(get_current_user),
):
    """Monitor election-related discourse — observation only, not influence."""
    from app.analytics.intelligence import get_emerging_topics, get_sentiment_trends
    from app.analytics.engine import compute_all_metrics

    narratives = get_narrative_analysis(db, days)
    elections = next((n for n in narratives if n["narrative"] == "Elections & Democracy"), None)
    governance = next((n for n in narratives if n["narrative"] == "Governance"), None)
    metrics = compute_all_metrics(db, days)
    sentiment = get_sentiment_trends(db, days)

    # Election narrative categories to watch
    election_topics = [
        "Electoral Process", "Democracy", "Political Participation",
        "Election Administration", "Civic Engagement", "Electoral Reform", "Public Trust"
    ]

    # Detect election-related emerging topics
    emerging = get_emerging_topics(db, days)
    election_emerging = [
        t for t in emerging
        if any(kw in t["topic"].lower() for kw in
               ["election", "vote", "inec", "ballot", "campaign", "party", "tribunal",
                "democracy", "electoral", "civic", "president", "senate", "governorship"])
    ]

    # Election readiness assessment
    election_activity = elections["share_of_voice"] if elections else 0
    if election_activity >= 15:
        readiness = "High Activity — Electoral discourse is elevated. Enhanced monitoring recommended."
        readiness_level = "high"
    elif election_activity >= 5:
        readiness = "Moderate Activity — Electoral themes are present in monitored discourse."
        readiness_level = "moderate"
    else:
        readiness = "Low Activity — Electoral discourse is currently below expected levels for a 2027 election cycle."
        readiness_level = "low"

    # 2027 countdown
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc)
    election_2027 = datetime(2027, 2, 1, tzinfo=timezone.utc)
    days_to_election = (election_2027 - now).days

    return {
        "generated_at": now.isoformat(),
        "period_days": days,
        "framework": "Observation only — public narrative monitoring, not influence or targeting",
        "next_election": "Nigeria General Election 2027",
        "days_to_election": days_to_election,
        "election_narrative": elections,
        "governance_narrative": governance,
        "election_activity_pct": round(election_activity, 1),
        "readiness_level": readiness_level,
        "readiness_assessment": readiness,
        "monitoring_categories": election_topics,
        "election_emerging_topics": election_emerging[:5],
        "sentiment_trend": sentiment[-7:] if sentiment else [],
        "overall_sentiment": metrics.get("sentiment_score", 0),
        "outlook": (
            f"With {days_to_election} days until the 2027 Nigerian general election, "
            f"electoral discourse currently represents {election_activity:.0f}% of monitored content. "
            f"{'This is expected to increase significantly as the election approaches.' if election_activity < 10 else 'Electoral discourse is already elevated above baseline levels.'}"
        ),
        "monitoring_note": (
            "This framework monitors publicly available discourse only. "
            "It does not target individuals, influence voters, or engage in political communication. "
            "Intelligence is for strategic awareness purposes only."
        ),
    }

@router.get("/executive")
def national_pulse_executive(
    days: int = Query(7, ge=1, le=30),
    db: Session = Depends(get_db),
    _: dict = Depends(get_current_user),
):
    """National Pulse Executive Intelligence — full decision-support layer."""
    ck = cache_key("national-pulse-executive", f"days={days}")
    cached = get_cached(ck)
    if cached:
        return cached
    pulse = compute_national_pulse(db, days)
    confidence = get_platform_confidence(db, days)
    exec_intel = generate_national_pulse_executive(db, days, pulse.get("pulse_score", 67), pulse.get("pulse_label", "Stable"))
    from app.analytics.strategic_narratives import get_narrative_analysis
    narratives = get_narrative_analysis(db, days)
    source_diversity_str = confidence.get("source_diversity", "12 active sources")
    try:
        active_source_count = int(source_diversity_str.split()[0])
    except (ValueError, IndexError):
        active_source_count = 12

    result = {
        **pulse,
        "executive_intelligence": exec_intel,
        "platform_confidence": confidence,
        "narrative_components": narratives,
        # Flattened fields for frontend convenience — matched to evidence_layer.py keys
        "confidence_label": confidence.get("overall_label", "High"),
        "source_count": active_source_count,
        "total_records": pulse.get("total_records", 0),
        "nlp_rate": confidence.get("nlp_success_rate", 0),
    }
    set_cached(ck, result, TTL_NATIONAL_PULSE)
    return result


@router.get("/polarisation")
def get_polarisation(
    days: int = Query(7, ge=1, le=30),
    db: Session = Depends(get_db),
    _: dict = Depends(get_current_user),
):
    """Polarisation Intelligence Engine."""
    ck = cache_key("polarisation", f"days={days}")
    cached = get_cached(ck)
    if cached:
        return cached
    from app.services.polarisation import compute_narrative_polarisation
    result = compute_narrative_polarisation(db, days)
    set_cached(ck, result, TTL_NATIONAL_PULSE)
    return result


@router.get("/executive-actions")
def get_executive_actions(
    days: int = Query(7, ge=1, le=30),
    db: Session = Depends(get_db),
    _: dict = Depends(get_current_user),
):
    """Executive Actions Engine."""
    ck = cache_key("executive-actions", f"days={days}")
    cached = get_cached(ck)
    if cached:
        return cached
    from app.services.executive_actions import generate_executive_actions
    result = generate_executive_actions(db, days)
    set_cached(ck, result, TTL_NATIONAL_PULSE)
    return result


@router.get("/entity-influence")
def get_entity_influence(
    days: int = Query(7, ge=1, le=30),
    db: Session = Depends(get_db),
    _: dict = Depends(get_current_user),
):
    """Entity Influence Intelligence."""
    ck = cache_key("entity-influence", f"days={days}")
    cached = get_cached(ck)
    if cached:
        return cached
    from app.services.entity_influence import compute_entity_influence_scores
    result = compute_entity_influence_scores(db, days)
    set_cached(ck, result, TTL_NATIONAL_PULSE)
    return result

@router.get("/decision-support")
def get_decision_support(
    days: int = Query(7, ge=1, le=30),
    db: Session = Depends(get_db),
    _: dict = Depends(get_current_user),
):
    """Decision Support Engine — time-horizoned leadership actions."""
    ck = cache_key("decision-support", f"days={days}")
    cached = get_cached(ck)
    if cached:
        return cached
    from app.services.decision_support import generate_decision_support
    result = generate_decision_support(db, days)
    set_cached(ck, result, TTL_NATIONAL_PULSE)
    return result



@router.get("/decision-support/performance")
def get_decision_support_performance(
    db: Session = Depends(get_db),
    _: dict = Depends(get_current_user),
):
    """V5.6 — Decision Support Performance Summary (Executive Learning Loop)."""
    from app.services.recommendation_tracker import get_decision_support_performance_summary
    return get_decision_support_performance_summary(db)


@router.get("/decision-support/recommendations")
def get_tracked_recommendations(
    limit: int = Query(20, ge=1, le=100),
    status: str = Query(None),
    db: Session = Depends(get_db),
    _: dict = Depends(get_current_user),
):
    """V5.6 — Recent tracked recommendations with evaluation status."""
    from app.services.recommendation_tracker import get_recent_recommendations
    return {"recommendations": get_recent_recommendations(db, limit, status)}


@router.post("/decision-support/run-evaluation")
def trigger_evaluation_cycle(
    db: Session = Depends(get_db),
    _: dict = Depends(get_current_user),
):
    """V5.6 — Manually trigger an evaluation cycle for eligible OPEN recommendations."""
    from app.services.recommendation_tracker import run_evaluation_cycle
    return run_evaluation_cycle(db)


@router.get("/intelligence-learning/cycle")
def get_intelligence_learning_cycle(
    db: Session = Depends(get_db),
    _: dict = Depends(get_current_user),
):
    """V5.8 — Full Intelligence Learning Engine cycle: metrics, weights, lessons learned."""
    from app.services.intelligence_learning import run_intelligence_learning_cycle
    return run_intelligence_learning_cycle(db)


@router.get("/intelligence-learning/confidence-weights")
def get_confidence_weights(
    db: Session = Depends(get_db),
    _: dict = Depends(get_current_user),
):
    """V5.8 Phase K — Adaptive confidence weighting table by category and narrative."""
    from app.services.intelligence_learning import compute_adaptive_confidence_weights
    return compute_adaptive_confidence_weights(db)


@router.get("/intelligence-learning/lessons-learned")
def get_lessons_learned(
    lookback_days: int = Query(30, ge=1, le=180),
    db: Session = Depends(get_db),
    _: dict = Depends(get_current_user),
):
    """V5.8 Phase L — Lessons learned from recent recommendation evaluations."""
    from app.services.intelligence_learning import generate_lessons_learned
    return {"lessons": generate_lessons_learned(db, lookback_days)}


@router.get("/intelligence-learning/module-self-evaluation")
def get_module_self_evaluation(
    module: str = Query(None),
    db: Session = Depends(get_db),
    _: dict = Depends(get_current_user),
):
    """V5.8 Phase F — Per-module self-evaluation, or all modules if no module specified."""
    from app.services.intelligence_learning import get_module_self_evaluation, get_all_modules_self_evaluation
    if module:
        return get_module_self_evaluation(db, module)
    return get_all_modules_self_evaluation(db)
