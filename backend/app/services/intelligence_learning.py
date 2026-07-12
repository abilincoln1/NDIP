"""
NDIP Intelligence Learning Engine v5.8
The platform-wide learning layer sitting above the per-recommendation
tracker (recommendation_tracker.py). Where the tracker answers
"was this one recommendation correct?", this engine answers
"what is NDIP learning across all its recommendations, and how should
that change future confidence weighting?"

Phases implemented here:
  E — Platform-wide learning system (continuous learning from outcomes)
  K — Adaptive recommendation weighting (confidence adjustment from history)
  L — Lessons learned engine
"""
from datetime import datetime, timezone, timedelta
from typing import Optional
from collections import defaultdict
from sqlalchemy.orm import Session

from app.models.models import RecommendationRecord, RecommendationStatus


# ─── Phase K: Adaptive Recommendation Weighting ───────────────────────────────

# Minimum evaluated sample size before we trust a category/narrative's
# historical performance enough to adjust confidence. Below this, we don't
# have enough data to distinguish genuine skill from noise.
MIN_SAMPLE_FOR_WEIGHTING = 5


def compute_adaptive_confidence_weights(db: Session) -> dict:
    """
    Phase K: examine historical accuracy by category and by narrative.
    Categories/narratives that have historically performed well (high average
    outcome_score) get an upward confidence adjustment; those that have
    repeatedly underperformed get a downward adjustment.

    Returns a weighting table that the Decision Support Engine (or any other
    module) can consult when assigning confidence to a NEW recommendation —
    "Security ESCALATE recommendations have historically been 85% accurate,
    so similar new ones can be flagged High confidence by default."

    This does NOT retroactively change any existing recommendation's stored
    confidence — it only informs how NEW recommendations should be weighted.
    """
    scored = db.query(RecommendationRecord).filter(
        RecommendationRecord.outcome_score.isnot(None)
    ).all()

    category_weights = {}
    by_category = defaultdict(list)
    for r in scored:
        by_category[r.recommendation_category].append(r.outcome_score)

    for cat, scores in by_category.items():
        if len(scores) >= MIN_SAMPLE_FOR_WEIGHTING:
            avg = sum(scores) / len(scores)
            adjustment = _score_to_adjustment(avg)
            category_weights[cat] = {
                "sample_size": len(scores),
                "historical_accuracy": round(avg),
                "confidence_adjustment": adjustment,
                "recommended_default_confidence": _adjustment_to_confidence_label(adjustment),
            }
        else:
            category_weights[cat] = {
                "sample_size": len(scores),
                "historical_accuracy": round(sum(scores) / len(scores)) if scores else None,
                "confidence_adjustment": "Insufficient data",
                "recommended_default_confidence": "Medium",  # safe default
            }

    narrative_weights = {}
    by_narrative = defaultdict(list)
    for r in scored:
        if r.narrative:
            by_narrative[r.narrative].append(r.outcome_score)

    for nar, scores in by_narrative.items():
        if len(scores) >= MIN_SAMPLE_FOR_WEIGHTING:
            avg = sum(scores) / len(scores)
            adjustment = _score_to_adjustment(avg)
            narrative_weights[nar] = {
                "sample_size": len(scores),
                "historical_accuracy": round(avg),
                "confidence_adjustment": adjustment,
            }
        else:
            narrative_weights[nar] = {
                "sample_size": len(scores),
                "historical_accuracy": round(sum(scores) / len(scores)) if scores else None,
                "confidence_adjustment": "Insufficient data",
            }

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "total_scored_recommendations": len(scored),
        "minimum_sample_size": MIN_SAMPLE_FOR_WEIGHTING,
        "category_weights": category_weights,
        "narrative_weights": narrative_weights,
        "methodology_note": (
            f"Categories and narratives with fewer than {MIN_SAMPLE_FOR_WEIGHTING} evaluated "
            f"recommendations are marked 'Insufficient data' and default to Medium confidence — "
            f"this prevents the platform from over-confidently adjusting weights based on a "
            f"small number of lucky or unlucky outcomes."
        ),
    }


def _score_to_adjustment(avg_score: float) -> str:
    """Map an average outcome score to a plain-English confidence adjustment direction."""
    if avg_score >= 75:
        return "Upgrade"
    elif avg_score >= 50:
        return "Maintain"
    elif avg_score >= 25:
        return "Downgrade"
    else:
        return "Significant downgrade"


def _adjustment_to_confidence_label(adjustment: str) -> str:
    return {
        "Upgrade": "High",
        "Maintain": "Medium",
        "Downgrade": "Low",
        "Significant downgrade": "Low",
    }.get(adjustment, "Medium")


def get_recommended_confidence(db: Session, category: str, narrative: Optional[str] = None) -> str:
    """
    Convenience function for any module generating a NEW recommendation:
    ask the learning engine what confidence level history supports for
    this category/narrative combination, rather than hard-coding it.
    Falls back to Medium if insufficient history exists.
    """
    weights = compute_adaptive_confidence_weights(db)
    cat_weight = weights["category_weights"].get(category)
    if cat_weight and cat_weight["confidence_adjustment"] != "Insufficient data":
        return cat_weight["recommended_default_confidence"]
    return "Medium"


# ─── Phase L: Lessons Learned Engine ──────────────────────────────────────────

def generate_lessons_learned(db: Session, lookback_days: int = 30) -> list:
    """
    Phase L: examine recently evaluated recommendations and surface
    plain-English lessons — patterns the platform should be aware of
    about its own forecasting behaviour.
    """
    cutoff = datetime.now(timezone.utc) - timedelta(days=lookback_days)
    recent = db.query(RecommendationRecord).filter(
        RecommendationRecord.evaluation_date.isnot(None),
        RecommendationRecord.evaluation_date >= cutoff,
    ).all()

    lessons = []

    if not recent:
        return [{
            "lesson": "No recommendations have been evaluated yet in this period.",
            "category": None,
            "evidence_count": 0,
        }]

    # Lesson type 1: category-level systematic over/under-confidence
    by_category = defaultdict(list)
    for r in recent:
        by_category[r.recommendation_category].append(r)

    for cat, recs in by_category.items():
        if len(recs) < MIN_SAMPLE_FOR_WEIGHTING:
            continue
        invalidated = [r for r in recs if r.status == RecommendationStatus.INVALIDATED]
        validated = [r for r in recs if r.status == RecommendationStatus.VALIDATED]
        invalid_rate = len(invalidated) / len(recs)
        valid_rate = len(validated) / len(recs)

        if invalid_rate >= 0.4:
            lessons.append({
                "lesson": (
                    f"{cat} recommendations were invalidated {round(invalid_rate*100)}% of the time "
                    f"over the past {lookback_days} days ({len(invalidated)} of {len(recs)}). "
                    f"This suggests {cat.lower()} warnings during this period were systematically "
                    f"overstated relative to actual discourse movement."
                ),
                "category": cat,
                "evidence_count": len(recs),
                "lesson_type": "overconfidence",
            })
        elif valid_rate >= 0.7:
            lessons.append({
                "lesson": (
                    f"{cat} recommendations proved accurate {round(valid_rate*100)}% of the time "
                    f"over the past {lookback_days} days ({len(validated)} of {len(recs)}). "
                    f"This category's forecasting logic is performing reliably and warrants "
                    f"continued or increased confidence weighting."
                ),
                "category": cat,
                "evidence_count": len(recs),
                "lesson_type": "reliable_pattern",
            })

    # Lesson type 2: narrative-specific timing lessons
    # (e.g. "election discourse accelerated earlier than expected")
    by_narrative = defaultdict(list)
    for r in recent:
        if r.narrative:
            by_narrative[r.narrative].append(r)

    for nar, recs in by_narrative.items():
        if len(recs) < 3:
            continue
        escalate_or_monitor = [r for r in recs if r.recommendation_category in ("ESCALATE", "MONITOR")]
        if not escalate_or_monitor:
            continue
        avg_outcome_value = [r.outcome_metric_value for r in escalate_or_monitor if r.outcome_metric_value is not None]
        avg_trigger_value = [r.trigger_metric_value for r in escalate_or_monitor if r.trigger_metric_value is not None]
        if avg_outcome_value and avg_trigger_value:
            outcome_mean = sum(avg_outcome_value) / len(avg_outcome_value)
            trigger_mean = sum(avg_trigger_value) / len(avg_trigger_value)
            if trigger_mean and outcome_mean > trigger_mean * 1.3:
                lessons.append({
                    "lesson": (
                        f"{nar} discourse accelerated faster than NDIP's monitoring recommendations "
                        f"anticipated during this period — actual levels exceeded the trigger "
                        f"conditions that originally prompted monitoring. Consider lowering the "
                        f"escalation threshold for {nar.lower()} in future cycles."
                    ),
                    "category": nar,
                    "evidence_count": len(escalate_or_monitor),
                    "lesson_type": "timing_underestimate",
                })
            elif trigger_mean and outcome_mean < trigger_mean * 0.7:
                lessons.append({
                    "lesson": (
                        f"{nar} discourse cooled faster than NDIP's monitoring recommendations "
                        f"anticipated during this period. Escalation/monitoring recommendations "
                        f"for {nar.lower()} during this window proved more cautious than the "
                        f"actual discourse trajectory warranted."
                    ),
                    "category": nar,
                    "evidence_count": len(escalate_or_monitor),
                    "lesson_type": "timing_overestimate",
                })

    if not lessons:
        lessons.append({
            "lesson": (
                f"No strong systematic patterns detected in the past {lookback_days} days — "
                f"recommendation outcomes are mixed without a clear directional bias. "
                f"This is itself a reasonable signal that the platform is not currently "
                f"over- or under-confident in a particular direction."
            ),
            "category": None,
            "evidence_count": len(recent),
            "lesson_type": "no_strong_pattern",
        })

    return lessons


# ─── Phase E: Platform-Wide Learning Engine Orchestrator ──────────────────────

def compute_strategic_outcome_metrics(db: Session) -> dict:
    """
    V6.0 Phase M — extends Recommendation Effectiveness Tracking with three
    new metrics built on the OutcomeChainLink table (Recommendation ->
    Leadership Action -> Stakeholder Engagement -> Outcome -> Impact).

    Honest about data maturity: these metrics require OutcomeChainLink rows,
    which only exist once a leadership action has actually been logged
    against a recommendation or opportunity (a human/process step, not
    something that accumulates automatically the way RecommendationRecord
    rows do). On a freshly-deployed V6.0, this will correctly report zero
    data rather than a fabricated score — same honesty principle as V5.8's
    "Awaiting evaluation" state for brand-new RecommendationRecord rows.
    """
    from app.models.models import OutcomeChainLink, OpportunityAssessment, OpportunityPipelineStatus

    total_links = db.query(OutcomeChainLink).count()
    links_with_engagement = db.query(OutcomeChainLink).filter(
        OutcomeChainLink.stakeholder_engagement.isnot(None)
    ).count()
    links_with_outcome = db.query(OutcomeChainLink).filter(
        OutcomeChainLink.outcome.isnot(None)
    ).count()

    stakeholder_engagement_success = (
        round(100 * links_with_outcome / links_with_engagement, 1)
        if links_with_engagement > 0 else None
    )

    total_opportunities = db.query(OpportunityAssessment).count()
    secured_opportunities = db.query(OpportunityAssessment).filter(
        OpportunityAssessment.status == OpportunityPipelineStatus.SECURED
    ).count()
    opportunity_conversion_rate = (
        round(100 * secured_opportunities / total_opportunities, 1)
        if total_opportunities > 0 else None
    )

    links_with_impact = db.query(OutcomeChainLink).filter(
        OutcomeChainLink.impact.isnot(None)
    ).count()
    strategic_outcome_success = (
        round(100 * links_with_impact / total_links, 1)
        if total_links > 0 else None
    )

    return {
        "total_outcome_chain_links": total_links,
        "stakeholder_engagement_success": stakeholder_engagement_success,
        "opportunity_conversion_rate": opportunity_conversion_rate,
        "strategic_outcome_success": strategic_outcome_success,
        "total_opportunities_tracked": total_opportunities,
        "opportunities_secured": secured_opportunities,
        "data_maturity_note": (
            "No outcome chain data recorded yet — these metrics require a leadership "
            "action to be logged against a recommendation before they can be computed."
            if total_links == 0 else None
        ),
    }


def compute_stakeholder_effectiveness_scores(db: Session) -> dict:
    """
    V6.1 Phase J — Stakeholder Effectiveness Score. For each stakeholder
    named in at least one OutcomeChainLink (via opportunity linkage),
    measures what fraction of their engagements progressed to a recorded
    outcome. This is distinct from V6.0's stakeholder_engagement_success
    (a single platform-wide rate) — this metric is per-stakeholder, so
    leadership can see which specific institutions tend to follow through
    on engagement versus which tend to stall.

    Honest about data maturity: returns an empty dict with a maturity note
    if no OutcomeChainLink rows exist yet, the same pattern as every other
    learning metric in this platform.
    """
    import json
    from app.models.models import OutcomeChainLink, OpportunityAssessment, StakeholderRegistry

    links = db.query(OutcomeChainLink).filter(OutcomeChainLink.opportunity_id.isnot(None)).all()
    if not links:
        return {"stakeholders": [], "data_maturity_note": "No outcome chain data linked to opportunities yet — this metric requires at least one logged engagement."}

    opp_ids = {l.opportunity_id for l in links}
    opportunities = {o.id: o for o in db.query(OpportunityAssessment).filter(OpportunityAssessment.id.in_(opp_ids)).all()}
    stakeholder_lookup = {s.id: s.name for s in db.query(StakeholderRegistry).all()}

    per_stakeholder = {}
    for link in links:
        opp = opportunities.get(link.opportunity_id)
        if not opp or not opp.stakeholders_json:
            continue
        try:
            named = json.loads(opp.stakeholders_json)
        except (json.JSONDecodeError, TypeError):
            continue
        for s in named:
            sid = s.get("stakeholder_id")
            if sid is None:
                continue
            bucket = per_stakeholder.setdefault(sid, {"engaged": 0, "outcomes": 0})
            if link.stakeholder_engagement:
                bucket["engaged"] += 1
            if link.outcome:
                bucket["outcomes"] += 1

    results = []
    for sid, counts in per_stakeholder.items():
        effectiveness = round(100 * counts["outcomes"] / counts["engaged"], 1) if counts["engaged"] > 0 else None
        results.append({
            "stakeholder_id": sid,
            "name": stakeholder_lookup.get(sid, "Unknown"),
            "engagements": counts["engaged"],
            "outcomes_recorded": counts["outcomes"],
            "effectiveness_score": effectiveness,
        })
    results.sort(key=lambda r: r["effectiveness_score"] or 0, reverse=True)
    return {"stakeholders": results, "data_maturity_note": None}


def run_intelligence_learning_cycle(db: Session) -> dict:
    """
    Phase E: the top-level learning orchestrator. Combines adaptive weighting
    and lessons learned into a single "what has NDIP learned" report, intended
    to be the data source for the Intelligence Performance Dashboard (Phase G)
    and the Leadership Pack's INTELLIGENCE PERFORMANCE section (Phase H).
    """
    from app.services.recommendation_tracker import compute_decision_quality_metrics

    metrics = compute_decision_quality_metrics(db)
    weights = compute_adaptive_confidence_weights(db)
    lessons = generate_lessons_learned(db)

    # Best / weakest performing recommendations (Phase I requirement)
    scored = db.query(RecommendationRecord).filter(
        RecommendationRecord.outcome_score.isnot(None)
    ).order_by(RecommendationRecord.outcome_score.desc()).all()

    best_recommendations = [_summarise_record(r) for r in scored[:5]]
    weakest_recommendations = [_summarise_record(r) for r in scored[-5:]] if len(scored) > 5 else []

    # V6.0 Phase M — Strategic Outcome Intelligence metrics, additive.
    try:
        strategic_outcome_metrics = compute_strategic_outcome_metrics(db)
    except Exception:
        strategic_outcome_metrics = None

    # V6.1 Phase J — Stakeholder Effectiveness Score, additive.
    try:
        stakeholder_effectiveness = compute_stakeholder_effectiveness_scores(db)
    except Exception:
        stakeholder_effectiveness = None

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "platform_learning_score": metrics.get("platform_learning_score"),
        "decision_quality_metrics": metrics,
        "adaptive_confidence_weights": weights,
        "lessons_learned": lessons,
        "best_recommendations": best_recommendations,
        "weakest_recommendations": weakest_recommendations,
        "recommendations_improved_count": len([
            w for w in weights["category_weights"].values()
            if w.get("confidence_adjustment") == "Upgrade"
        ]),
        "strategic_outcome_metrics": strategic_outcome_metrics,
        "stakeholder_effectiveness": stakeholder_effectiveness,
    }


def _summarise_record(r: RecommendationRecord) -> dict:
    return {
        "id": r.id,
        "module": r.module,
        "narrative": r.narrative,
        "category": r.recommendation_category,
        "recommendation_text": r.recommendation_text,
        "status": r.status,
        "outcome_score": r.outcome_score,
        "outcome_notes": r.outcome_notes,
        "created_at": r.created_at.isoformat() if r.created_at else None,
    }


# ─── Phase F: Per-Module Self-Evaluation ──────────────────────────────────────

MODULE_TRACKED_METRICS = {
    "national_pulse": ["Pulse outlook accuracy", "Narrative trend accuracy", "Risk assessment accuracy"],
    "situation_room": ["Watchlist accuracy", "Emerging topic accuracy", "Narrative competition accuracy"],
    "leadership_pack": ["Strategic assessment accuracy", "Executive action accuracy", "Outlook accuracy"],
    "election_intelligence": ["Election outlook accuracy", "Election risk accuracy", "Election opportunity accuracy", "Election monitoring accuracy"],
    "gnei": ["Diaspora engagement forecast accuracy", "Global sentiment forecast accuracy", "Opportunity forecast accuracy"],
    "entity_intelligence": ["Entity momentum accuracy", "Influence prediction accuracy", "Emerging entity detection accuracy"],
    "narrative_intelligence": ["Narrative growth prediction accuracy", "Narrative displacement prediction accuracy", "Narrative concentration forecast accuracy"],
}


def get_module_self_evaluation(db: Session, module: str) -> dict:
    """
    Phase F: per-module self-evaluation. Returns accuracy specifically for
    recommendations tagged with this module, plus the list of metric names
    this module is expected to track per the V5.8 specification (even if
    not all of them have evaluated data yet).
    """
    module_recs = db.query(RecommendationRecord).filter(
        RecommendationRecord.module == module,
    ).all()

    evaluated = [r for r in module_recs if r.outcome_score is not None]
    avg_accuracy = round(sum(r.outcome_score for r in evaluated) / len(evaluated)) if evaluated else None

    return {
        "module": module,
        "tracked_metrics": MODULE_TRACKED_METRICS.get(module, []),
        "recommendations_generated": len(module_recs),
        "recommendations_evaluated": len(evaluated),
        "average_accuracy": avg_accuracy,
        "status": (
            "No data yet" if not module_recs
            else "Awaiting evaluation" if not evaluated
            else "Active"
        ),
    }


def get_all_modules_self_evaluation(db: Session) -> dict:
    """Phase F across every tracked module — used by the Intelligence Performance Dashboard."""
    return {
        module: get_module_self_evaluation(db, module)
        for module in MODULE_TRACKED_METRICS.keys()
    }
