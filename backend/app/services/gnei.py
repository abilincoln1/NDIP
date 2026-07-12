"""
NDIP Global Nigerian Engagement Index (GNEI) v5.3
Flagship intelligence capability measuring how Nigeria and Nigerians
are discussed, perceived, engaged with, and represented globally.
"""
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from app.analytics.strategic_narratives import get_narrative_analysis


# ─── GNEI narrative mapping ───────────────────────────────────────────────────
GNEI_NARRATIVES = [
    "Global Nigerian Engagement",
    "Investment",
    "Media Representation",
]

GNEI_INDICATORS = {
    "diaspora": ["diaspora", "overseas nigerian", "abroad", "uk nigerian", "us nigerian", "nigerian community", "remittance", "migrant"],
    "investment": ["investment", "fdi", "foreign direct", "investor", "startup", "venture", "capital", "business"],
    "migration": ["migration", "migrant", "emigration", "immigration", "relocation", "return migration", "brain drain"],
    "remittance": ["remittance", "transfer", "send money", "western union", "wire transfer"],
    "perception": ["reputation", "image", "perception", "representation", "portrayal", "stereotype", "brand"],
    "partnerships": ["partnership", "cooperation", "collaboration", "bilateral", "multilateral", "agreement"],
}

DIASPORA_STRATEGIC_CONTEXT = {
    "high": "Strong global Nigerian engagement indicates an active, mobilised diaspora community. RTIFN is operating in a high-receptivity environment — communications, campaigns, and community initiatives will find a responsive audience.",
    "medium": "Moderate global engagement reflects a diaspora community that is present but not at peak mobilisation. Targeted interventions can increase engagement, particularly around events of direct relevance to overseas Nigerians.",
    "low": "Lower global engagement may reflect community fatigue, competing host-country priorities, or a quiet period in Nigerian national affairs. Monitor for triggering events that typically reignite diaspora engagement.",
}


def compute_gnei_score(narratives: list, metrics: dict) -> dict:
    """Compute GNEI composite score from narrative data."""
    diaspora_nar = next((n for n in narratives if n["narrative"] == "Global Nigerian Engagement"), None)
    investment_nar = next((n for n in narratives if n["narrative"] == "Investment"), None)
    media_nar = next((n for n in narratives if n["narrative"] == "Media Representation"), None)

    # Component scores
    # Diaspora engagement score (0-100): SoV * sentiment factor * momentum factor
    diaspora_sov = diaspora_nar["share_of_voice"] if diaspora_nar else 0
    diaspora_sentiment = diaspora_nar["sentiment_label"] if diaspora_nar else "neutral"
    diaspora_momentum = diaspora_nar["momentum"] if diaspora_nar else 0
    diaspora_direction = diaspora_nar["momentum_direction"] if diaspora_nar else "stable"

    sentiment_factor = 1.2 if diaspora_sentiment == "positive" else 0.8 if diaspora_sentiment == "negative" else 1.0
    momentum_factor = 1.1 if diaspora_direction == "rising" else 0.9 if diaspora_direction == "falling" else 1.0
    diaspora_score = min(100, round(diaspora_sov * 2.0 * sentiment_factor * momentum_factor))

    # International attention score: based on how much non-diaspora international narratives are active
    investment_sov = investment_nar["share_of_voice"] if investment_nar else 0
    media_sov = media_nar["share_of_voice"] if media_nar else 0
    international_score = min(100, round((investment_sov + media_sov) * 3))

    # Global sentiment score
    all_gnei_narratives = [n for n in narratives if n["narrative"] in GNEI_NARRATIVES]
    if all_gnei_narratives:
        positive_count = sum(1 for n in all_gnei_narratives if n["sentiment_label"] == "positive")
        negative_count = sum(1 for n in all_gnei_narratives if n["sentiment_label"] == "negative")
        total = len(all_gnei_narratives)
        global_sentiment_score = round(50 + (positive_count - negative_count) / total * 50)
    else:
        global_sentiment_score = 50

    # Opportunity score: based on positive investment and engagement trends
    opp_score = 0
    if investment_nar and investment_nar["sentiment_label"] == "positive":
        opp_score += 30
    if diaspora_nar and diaspora_nar["momentum_direction"] == "rising":
        opp_score += 25
    if diaspora_sov > 20:
        opp_score += 25
    if media_nar and media_nar["sentiment_label"] == "positive":
        opp_score += 20
    opportunity_score = min(100, opp_score)

    # Narrative diversity score: how many GNEI-related narratives are active
    active_gnei = sum(1 for n in all_gnei_narratives if n["count"] > 0)
    narrative_diversity_score = min(100, active_gnei * 33)

    # Composite GNEI score
    gnei_score = round(
        diaspora_score * 0.40 +
        global_sentiment_score * 0.25 +
        international_score * 0.15 +
        opportunity_score * 0.12 +
        narrative_diversity_score * 0.08
    )

    # GNEI label
    if gnei_score >= 75:
        gnei_label = "Strong"
        engagement_level = "high"
    elif gnei_score >= 55:
        gnei_label = "Moderate"
        engagement_level = "medium"
    elif gnei_score >= 35:
        gnei_label = "Developing"
        engagement_level = "low"
    else:
        gnei_label = "Limited"
        engagement_level = "low"

    return {
        "gnei_score": gnei_score,
        "gnei_label": gnei_label,
        "engagement_level": engagement_level,
        "component_scores": {
            "diaspora_engagement": diaspora_score,
            "global_sentiment": global_sentiment_score,
            "international_attention": international_score,
            "opportunity": opportunity_score,
            "narrative_diversity": narrative_diversity_score,
        },
        "diaspora_sov": diaspora_sov,
        "diaspora_sentiment": diaspora_sentiment,
        "diaspora_momentum": diaspora_momentum,
        "diaspora_direction": diaspora_direction,
    }


def generate_gnei_assessment(score_data: dict, narratives: list) -> dict:
    """Generate analyst-grade GNEI assessment."""
    gnei_score = score_data["gnei_score"]
    gnei_label = score_data["gnei_label"]
    engagement_level = score_data["engagement_level"]
    diaspora_sov = score_data["diaspora_sov"]
    diaspora_sentiment = score_data["diaspora_sentiment"]
    diaspora_momentum = score_data["diaspora_momentum"]
    diaspora_direction = score_data["diaspora_direction"]

    # What happened
    if diaspora_sov >= 30:
        what_happened = (
            f"Global Nigerian Engagement dominates monitored discourse at {diaspora_sov:.0f}% share of voice — "
            f"the single largest narrative category. International discourse about Nigeria and Nigerians "
            f"is at an elevated level, indicating a period of heightened global attention."
        )
    elif diaspora_sov >= 15:
        what_happened = (
            f"Global Nigerian Engagement is a major theme in monitored discourse at {diaspora_sov:.0f}% share of voice. "
            f"International and diaspora discourse is active and building."
        )
    else:
        what_happened = (
            f"Global Nigerian Engagement registers at {diaspora_sov:.0f}% share of voice. "
            f"International discourse about Nigeria and Nigerians is present but at moderate levels."
        )

    # Why it matters
    why_matters = (
        "The Global Nigerian Engagement Index measures RTIFN's primary intelligence mandate — "
        "how Nigeria and Nigerians are discussed, perceived, and engaged with across global media and community discourse. "
        f"A GNEI score of {gnei_score}/100 ({gnei_label}) indicates "
        f"{'strong diaspora community mobilisation and international attention' if gnei_score >= 75 else 'moderate but active diaspora engagement' if gnei_score >= 55 else 'developing engagement levels with room for growth'}. "
        f"{DIASPORA_STRATEGIC_CONTEXT[engagement_level]}"
    )

    # What changed
    if diaspora_direction == "rising" and diaspora_momentum > 100:
        what_changed = (
            f"Global Nigerian Engagement discourse accelerated dramatically — up {diaspora_momentum:.0f}% compared to the previous period. "
            f"This exceptional surge typically indicates a significant triggering event or a sustained media campaign around Nigerian diaspora issues."
        )
    elif diaspora_direction == "rising":
        what_changed = (
            f"Global Nigerian Engagement discourse increased by {diaspora_momentum:.0f}% compared to the previous period — "
            f"a meaningful build in diaspora community engagement."
        )
    elif diaspora_direction == "falling":
        what_changed = (
            f"Global Nigerian Engagement discourse declined by {abs(diaspora_momentum):.0f}% compared to the previous period. "
            f"Monitor whether this reflects temporary news cycle displacement or a genuine reduction in diaspora engagement."
        )
    else:
        what_changed = (
            "Global Nigerian Engagement discourse remained broadly stable compared to the previous period. "
            "No significant momentum shift detected."
        )

    # Strategic implications
    implications = []
    if diaspora_sentiment == "positive" and diaspora_sov > 20:
        implications.append("Strong positive diaspora discourse creates an optimal environment for RTIFN community campaigns, membership drives, and policy advocacy.")
    if diaspora_sentiment == "negative":
        implications.append("Negative diaspora sentiment requires proactive community engagement. RTIFN should identify and address the specific concerns driving negative discourse.")
    investment_nar = next((n for n in narratives if n["narrative"] == "Investment"), None)
    if investment_nar and investment_nar["sentiment_label"] == "positive":
        implications.append(f"Positive investment discourse ({investment_nar['share_of_voice']:.0f}% share of voice) creates an opportunity to position diaspora communities as investment partners and amplify diaspora investment narratives.")
    if not implications:
        implications.append("Current GNEI levels support routine diaspora engagement activities. No exceptional opportunities or concerns identified.")

    return {
        "what_happened": what_happened,
        "why_it_matters": why_matters,
        "what_changed": what_changed,
        "strategic_implications": implications,
    }


def generate_gnei_intelligence(db: Session, days: int = 7) -> dict:
    """Generate full GNEI intelligence module."""
    from app.analytics.engine import compute_all_metrics
    from app.services.source_quality import get_source_quality_report

    narratives = get_narrative_analysis(db, days)
    metrics = compute_all_metrics(db, max(days, 30))
    source_quality = get_source_quality_report(db, days)

    score_data = compute_gnei_score(narratives, metrics)
    assessment = generate_gnei_assessment(score_data, narratives)

    # Narrative breakdown
    gnei_narratives = [n for n in narratives if n["narrative"] in GNEI_NARRATIVES]

    # Emerging global narratives
    emerging = sorted(
        [n for n in narratives if n["momentum_direction"] == "rising" and n["momentum"] > 50],
        key=lambda x: x["momentum"], reverse=True
    )[:3]

    # Outlook
    score = score_data["gnei_score"]
    direction = score_data["diaspora_direction"]

    if direction == "rising":
        outlook = f"The GNEI outlook is positive. Current upward momentum in diaspora engagement discourse suggests the index will strengthen over the next 14 days. This is an optimal period for community outreach and strategic communications."
    elif direction == "falling":
        outlook = f"GNEI momentum is declining. Monitor for stabilisation over the next 7 days. If the decline persists, consider targeted diaspora engagement initiatives to reverse the trend."
    else:
        outlook = f"GNEI is stable at {score}/100. Stable engagement levels provide a predictable environment for community programming. No significant shifts anticipated in the short term."

    # Confidence
    total_gnei_records = sum(n["count"] for n in gnei_narratives)
    if total_gnei_records > 500:
        confidence = "High"
    elif total_gnei_records > 100:
        confidence = "Medium"
    else:
        confidence = "Low"

    result = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "period_days": days,
        "gnei_score": score_data["gnei_score"],
        "gnei_label": score_data["gnei_label"],
        "component_scores": score_data["component_scores"],
        "assessment": assessment,
        "gnei_narratives": gnei_narratives,
        "emerging_global_narratives": emerging,
        "outlook": outlook,
        "confidence": confidence,
        "total_gnei_records": total_gnei_records,
        "source_count": source_quality.get("source_count", 12),
        "score_data": score_data,
    }

    # V5.8 Phase A/H — track the GNEI outlook as an evaluable recommendation.
    # Best-effort: never let tracking failures block GNEI intelligence generation.
    try:
        from app.services.recommendation_tracker import record_recommendation
        category = "ENGAGE" if direction == "rising" else "MONITOR"
        record_recommendation(
            db,
            narrative="Global Nigerian Engagement",
            recommendation_text=outlook,
            category=category,
            priority="Medium",
            confidence="Medium",
            time_horizon="14 days",
            supporting_evidence=f"GNEI outlook forecast, score={score}",
            expected_outcome=f"GNEI score trajectory consistent with {direction} direction",
            trigger_metric_name="gnei_score",
            trigger_metric_value=float(score),
            period_days=days,
            module="gnei",
        )
    except Exception:
        try:
            db.rollback()
        except Exception:
            pass

    return result
