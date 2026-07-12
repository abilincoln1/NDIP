"""
National Pulse Engine
Produces a single 0-100 score summarising Nigerian public discourse.
Inputs: Governance, Economy, Security, Elections, Energy, Infrastructure, Sentiment, Stability.
"""
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from app.analytics.strategic_narratives import get_narrative_analysis, STRATEGIC_NARRATIVES
from app.analytics.engine import compute_all_metrics
from app.analytics.intelligence import get_sentiment_trends


# ─── Pulse scoring weights ────────────────────────────────────────────────────
PULSE_WEIGHTS = {
    "Governance":            {"weight": 0.18, "ideal_sov": 20, "max_sov": 40},
    "Economy":               {"weight": 0.18, "ideal_sov": 15, "max_sov": 35},
    "Security":              {"weight": 0.15, "ideal_sov": 12, "max_sov": 30},
    "Elections & Democracy": {"weight": 0.12, "ideal_sov": 8,  "max_sov": 25},
    "Energy":                {"weight": 0.10, "ideal_sov": 6,  "max_sov": 20},
    "Infrastructure":        {"weight": 0.08, "ideal_sov": 5,  "max_sov": 20},
}

SENTIMENT_WEIGHT = 0.12
STABILITY_WEIGHT = 0.07


def _score_narrative(nar: dict, config: dict) -> float:
    """Score a narrative 0-1 based on coverage and sentiment."""
    sov = nar["share_of_voice"]
    ideal = config["ideal_sov"]
    coverage_score = min(sov / ideal, 1.0) if sov <= ideal * 2 else max(0, 1 - (sov - ideal * 2) / ideal)

    sentiment = nar["sentiment_label"]
    sentiment_score = 0.8 if sentiment == "positive" else 0.5 if sentiment == "neutral" else 0.25

    return (coverage_score * 0.6 + sentiment_score * 0.4)


def _interpret_score(score: int, narratives: list[dict], sentiment: float) -> str:
    dominant = narratives[0]["narrative"] if narratives else "Unknown"
    second = narratives[1]["narrative"] if len(narratives) > 1 else ""
    security = next((n for n in narratives if n["narrative"] == "Security"), None)
    economy = next((n for n in narratives if n["narrative"] == "Economy"), None)

    parts = []

    if score >= 75:
        parts.append("Nigeria's public discourse is broadly stable and constructive.")
    elif score >= 55:
        parts.append("Nigeria's public discourse remains generally stable.")
    elif score >= 40:
        parts.append("Nigeria's public discourse shows signs of stress in key areas.")
    else:
        parts.append("Nigeria's public discourse indicates significant public concern across multiple areas.")

    parts.append(f"**{dominant}** continues to dominate discussion")
    if second:
        parts.append(f"while **{second}** remains prominent.")
    else:
        parts.append(".")

    if security and security["sentiment_label"] == "negative" and security["share_of_voice"] > 15:
        parts.append(f"Security concerns are elevated ({security['share_of_voice']:.0f}% share of voice) and warrant close monitoring.")
    if economy and economy["share_of_voice"] > 10:
        sentiment_word = "positive" if economy["sentiment_label"] == "positive" else "cautious" if economy["sentiment_label"] == "neutral" else "concerned"
        parts.append(f"Economic discourse is {sentiment_word}.")

    if sentiment > 0.1:
        parts.append("Overall public sentiment is slightly positive.")
    elif sentiment < -0.1:
        parts.append("Overall public sentiment has turned negative — this is a signal requiring attention.")
    else:
        parts.append("Public sentiment is broadly neutral.")

    return " ".join(parts)


def _trend_text(score: int, prev_score: int) -> str:
    delta = score - prev_score
    if delta > 5:
        return f"improving (+{delta:.0f} points from previous period)"
    elif delta < -5:
        return f"declining ({delta:.0f} points from previous period)"
    else:
        return "stable (within normal range)"


def _outlook_text(score: int, narratives: list[dict], risks: list) -> str:
    rising_negative = [n for n in narratives
                       if n["momentum_direction"] == "rising" and n["sentiment_label"] == "negative"]
    high_risks = [r for r in risks if r.get("level") in ("Critical", "Warning")]

    if rising_negative:
        return (f"The 14-day outlook is cautious. **{rising_negative[0]['narrative']}** negative discourse "
                f"is rising and may intensify. Leadership should prepare contingency communications.")
    elif high_risks:
        return (f"The 14-day outlook is stable but watchful. {high_risks[0]['title']} requires ongoing monitoring.")
    elif score >= 65:
        return ("The 14-day outlook is positive. Current stability in national discourse provides "
                "a favourable environment for diaspora engagement and community initiatives.")
    else:
        return ("The 14-day outlook is neutral. Continue monitoring key narratives for signs of shift.")


def compute_national_pulse(db: Session, days: int = 7) -> dict:
    narratives = get_narrative_analysis(db, days)
    metrics = compute_all_metrics(db, max(days, 30))
    sentiment_trends = get_sentiment_trends(db, days)

    # Compute previous period for comparison
    prev_narratives = get_narrative_analysis(db, days * 2)
    nar_map = {n["narrative"]: n for n in narratives}
    prev_map = {n["narrative"]: n for n in prev_narratives}

    # Score each narrative component
    component_scores = {}
    weighted_sum = 0.0
    total_weight = 0.0

    for narrative, config in PULSE_WEIGHTS.items():
        nar = nar_map.get(narrative)
        if nar:
            s = _score_narrative(nar, config)
        else:
            s = 0.1  # penalise missing coverage
        component_scores[narrative] = round(s * 100, 1)
        weighted_sum += s * config["weight"]
        total_weight += config["weight"]

    # Sentiment component
    avg_sentiment = metrics.get("sentiment_score", 0)
    sentiment_score = (avg_sentiment + 1) / 2  # normalise -1→1 to 0→1
    weighted_sum += sentiment_score * SENTIMENT_WEIGHT
    total_weight += SENTIMENT_WEIGHT

    # Stability component — penalise extreme concentration
    top_sov = narratives[0]["share_of_voice"] if narratives else 50
    stability_score = max(0, 1 - max(0, top_sov - 40) / 60)
    weighted_sum += stability_score * STABILITY_WEIGHT
    total_weight += STABILITY_WEIGHT

    # Final score 0-100
    raw = weighted_sum / total_weight if total_weight > 0 else 0.5
    pulse_score = round(raw * 100)

    # Previous pulse (simplified)
    prev_component_sum = 0
    for narrative, config in PULSE_WEIGHTS.items():
        prev = prev_map.get(narrative)
        if prev:
            prev_component_sum += _score_narrative(prev, config) * config["weight"]
    prev_pulse = round((prev_component_sum / sum(c["weight"] for c in PULSE_WEIGHTS.values())) * 100)

    # Risks (simplified inline)
    from app.services.risk_opportunity import detect_all_risks, detect_all_opportunities
    risks = detect_all_risks(db, days)
    opportunities = detect_all_opportunities(db, days)

    # Narrative evidence breakdown
    evidence_by_narrative = []
    for nar in narratives[:8]:
        evidence_by_narrative.append({
            "narrative": nar["narrative"],
            "share_of_voice": nar["share_of_voice"],
            "count": nar["count"],
            "sentiment_label": nar["sentiment_label"],
            "momentum_direction": nar["momentum_direction"],
            "momentum": nar["momentum"],
            "confidence_label": nar["confidence_label"],
            "source_count": nar.get("source_count", 1),
            "score": component_scores.get(nar["narrative"], 50),
        })

    result = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "period_days": days,
        "pulse_score": pulse_score,
        "pulse_label": "Stable" if pulse_score >= 65 else "Moderate" if pulse_score >= 45 else "Stressed",
        "pulse_color": "green" if pulse_score >= 65 else "amber" if pulse_score >= 45 else "red",
        "pulse_trend": _trend_text(pulse_score, prev_pulse),
        "prev_pulse_score": prev_pulse,
        "interpretation": _interpret_score(pulse_score, narratives, avg_sentiment),
        "outlook": _outlook_text(pulse_score, narratives, risks),
        "component_scores": component_scores,
        "narrative_evidence": evidence_by_narrative,
        "dominant_narrative": narratives[0]["narrative"] if narratives else "None",
        "sentiment_score": round(avg_sentiment, 3),
        "sentiment_label": "positive" if avg_sentiment > 0.05 else "negative" if avg_sentiment < -0.05 else "neutral",
        "stability_score": round(stability_score * 100),
        "risks": risks,
        "opportunities": opportunities,
        "national_diaspora_linkage": _generate_linkage(narratives),
        "total_records": sum(n["count"] for n in narratives),
    }

    # V5.8 Phase F — National Pulse module self-evaluation.
    # Track the pulse outlook and top risk as evaluable recommendations.
    try:
        from app.services.recommendation_tracker import record_recommendation
        record_recommendation(
            db,
            narrative=result["dominant_narrative"] if result["dominant_narrative"] != "None" else None,
            recommendation_text=result["outlook"],
            category="MONITOR",
            priority="Medium",
            confidence="Medium",
            time_horizon="14 days",
            supporting_evidence=f"National Pulse score={pulse_score}, sentiment={result['sentiment_label']}",
            expected_outcome="Pulse score trajectory and narrative trends consistent with outlook",
            trigger_metric_name="pulse_score",
            trigger_metric_value=float(pulse_score),
            period_days=days,
            module="national_pulse",
        )
        if risks:
            top_risk = risks[0]
            record_recommendation(
                db,
                narrative=result["dominant_narrative"] if result["dominant_narrative"] != "None" else None,
                recommendation_text=top_risk.get("title", "") + " — " + top_risk.get("description", ""),
                category="ESCALATE" if top_risk.get("level") in ("Critical", "HIGH") else "MONITOR",
                priority=str(top_risk.get("level", "Medium")).title(),
                confidence="Medium",
                time_horizon="14 days",
                supporting_evidence="National Pulse risk detection",
                expected_outcome="Risk materialises or resolves consistent with assessed level",
                trigger_metric_name="pulse_score",
                trigger_metric_value=float(pulse_score),
                period_days=days,
                module="national_pulse",
            )
    except Exception:
        try:
            db.rollback()
        except Exception:
            pass

    return result


def _generate_linkage(narratives: list[dict]) -> str:
    """Generate national-diaspora linkage analysis."""
    diaspora = next((n for n in narratives if n["narrative"] == "Global Nigerian Engagement"), None)
    national = [n for n in narratives if n["narrative"] in
                ("Governance", "Economy", "Security", "Elections & Democracy", "Energy")]

    if not diaspora or not national:
        return ""

    drivers = [n for n in national if n["share_of_voice"] > 10]
    driver_text = " and ".join(
        f"**{d['narrative']}** ({d['share_of_voice']:.0f}%)" for d in drivers[:3]
    )

    direction = "increased" if diaspora["momentum_direction"] == "rising" else "remained active"

    if drivers:
        return (
            f"Global Nigerian Engagement discourse {direction} during this period, coinciding with "
            f"elevated national discussion around {driver_text}. "
            f"This pattern suggests overseas Nigerian communities are actively tracking and responding "
            f"to developments within Nigeria — a characteristic diaspora behaviour during periods of "
            f"heightened national activity."
        )
    return (
        f"Global Nigerian Engagement discourse {direction} during this period. "
        f"Diaspora discussion appears to be driven primarily by community-specific factors "
        f"rather than responses to specific national events."
    )
