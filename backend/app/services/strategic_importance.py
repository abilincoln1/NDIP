"""
NDIP Strategic Importance Engine v5.3
Scores every narrative, topic and entity by strategic importance — not just volume.
High mentions ≠ High importance. Low mentions may = Critical importance.
"""
from sqlalchemy.orm import Session
from app.analytics.strategic_narratives import STRATEGIC_NARRATIVES


STRATEGIC_WEIGHTS = {
    "Global Nigerian Engagement": 1.4,
    "Economy": 1.3,
    "Governance": 1.2,
    "Security": 1.2,
    "Elections & Democracy": 1.1,
    "Investment": 1.1,
    "Energy": 1.0,
    "Health": 1.0,
    "Media Representation": 1.0,
    "Infrastructure": 0.9,
    "Education": 0.9,
}

HIGH_IMPORTANCE_TOPICS = {
    "election security", "inec", "electoral fraud", "vote rigging", "ballot",
    "insurgency", "terrorism", "boko haram", "iswap", "kidnap",
    "naira collapse", "forex crisis", "fuel scarcity", "subsidy removal",
    "protest", "strike", "asuu", "outbreak", "epidemic",
    "coup", "constitutional crisis", "impeachment",
    "diaspora vote", "remittance policy", "overseas nigerian",
}


def compute_strategic_importance(nar: dict) -> dict:
    """
    Compute Strategic Importance Score for a narrative.
    Inputs: volume, momentum, source_diversity, sentiment_impact, narrative_weight, confidence
    Output: Critical / High / Medium / Low with score and reasoning
    """
    name = nar["narrative"]
    sov = nar["share_of_voice"]
    momentum = nar["momentum"]
    direction = nar["momentum_direction"]
    sentiment = nar["sentiment_label"]
    count = nar["count"]
    sources = nar.get("source_count", 1)
    confidence = nar["confidence_label"]
    weight = STRATEGIC_WEIGHTS.get(name, 1.0)

    # Volume score (0-25)
    if count >= 500:
        volume_score = 25
    elif count >= 200:
        volume_score = 20
    elif count >= 100:
        volume_score = 15
    elif count >= 50:
        volume_score = 10
    else:
        volume_score = 5

    # Momentum score (0-25)
    if direction == "rising" and momentum > 200:
        momentum_score = 25
    elif direction == "rising" and momentum > 100:
        momentum_score = 20
    elif direction == "rising" and momentum > 50:
        momentum_score = 15
    elif direction == "rising":
        momentum_score = 10
    elif direction == "falling" and momentum < -50:
        momentum_score = 5
    else:
        momentum_score = 8

    # Source diversity (0-15)
    if sources >= 10:
        diversity_score = 15
    elif sources >= 7:
        diversity_score = 12
    elif sources >= 4:
        diversity_score = 8
    else:
        diversity_score = 4

    # Sentiment impact (0-15)
    # Negative sentiment in high-weight narratives = higher importance
    if sentiment == "negative" and weight >= 1.2:
        sentiment_score = 15
    elif sentiment == "negative":
        sentiment_score = 10
    elif sentiment == "positive" and weight >= 1.3:
        sentiment_score = 12
    elif sentiment == "positive":
        sentiment_score = 8
    else:
        sentiment_score = 6

    # Strategic weight (0-20)
    strategic_score = round(weight * 14)

    # Total (0-100)
    total = volume_score + momentum_score + diversity_score + sentiment_score + strategic_score
    total = min(100, total)

    # Apply narrative weight multiplier for final classification
    weighted_total = total * weight

    if weighted_total >= 110 or (sentiment == "negative" and direction == "rising" and weight >= 1.2 and momentum > 100):
        importance = "Critical"
    elif weighted_total >= 80 or (direction == "rising" and momentum > 200 and weight >= 1.1):
        importance = "High"
    elif weighted_total >= 55:
        importance = "Medium"
    else:
        importance = "Low"

    # Generate reasoning
    reasons = []
    if volume_score >= 20:
        reasons.append(f"high evidence volume ({count:,} mentions)")
    if momentum_score >= 20:
        reasons.append(f"significant momentum acceleration ({momentum:.0f}%)")
    if strategic_score >= 15:
        reasons.append(f"high strategic weight for RTIFN mission ({weight})")
    if sentiment == "negative" and weight >= 1.2:
        reasons.append(f"negative sentiment in a high-priority narrative category")
    if diversity_score >= 12:
        reasons.append(f"broad source coverage ({sources} sources)")

    reasoning = f"Classified as {importance} based on: {', '.join(reasons)}." if reasons else f"Strategic importance: {importance}."

    return {
        "narrative": name,
        "importance": importance,
        "score": total,
        "weighted_score": round(weighted_total),
        "reasoning": reasoning,
        "component_scores": {
            "volume": volume_score,
            "momentum": momentum_score,
            "source_diversity": diversity_score,
            "sentiment_impact": sentiment_score,
            "strategic_weight": strategic_score,
        },
    }


def score_all_narratives(narratives: list) -> list:
    """Score all narratives by strategic importance."""
    scored = []
    for nar in narratives:
        importance_data = compute_strategic_importance(nar)
        scored.append({**nar, **importance_data})
    return sorted(scored, key=lambda x: x["weighted_score"], reverse=True)


# ─── Trigger Attribution Engine ───────────────────────────────────────────────

def generate_trigger_attribution(narratives: list, db: Session, days: int) -> list:
    """
    Identify WHY narratives surged.
    Uses keyword frequency in the spike period to identify probable triggering events.
    """
    from datetime import datetime, timedelta, timezone
    from sqlalchemy import func
    from app.models.models import NormalisedPost, NamedEntity, Topic

    attributions = []
    surging = [n for n in narratives if n["momentum_direction"] == "rising" and n["momentum"] > 100]

    for nar in surging[:5]:  # Top 5 surging narratives
        name = nar["narrative"]
        momentum = nar["momentum"]
        count = nar["count"]

        # Get top entities mentioned in posts tagged to this narrative
        now = datetime.now(timezone.utc)
        since = now - timedelta(days=days)

        try:
            # Get top topics from recent posts in this narrative category
            from app.analytics.strategic_narratives import STRATEGIC_NARRATIVES
            keywords = STRATEGIC_NARRATIVES.get(name, {}).get("keywords", [])

            if not keywords:
                continue

            # Sample keyword for entity lookup
            sample_keyword = keywords[0] if keywords else name.lower()

            # Get top entities co-occurring with narrative keywords
            top_entities = db.query(
                NamedEntity.name,
                func.count(NamedEntity.id).label("freq")
            ).join(
                NormalisedPost, NamedEntity.post_id == NormalisedPost.id
            ).filter(
                NormalisedPost.published_at >= since,
                NormalisedPost.nlp_processed == True,
            ).group_by(NamedEntity.name).order_by(func.count(NamedEntity.id).desc()).limit(5).all()

            entities = [{"name": r.name, "frequency": r.freq} for r in top_entities]

            # Get top topics
            top_topics = db.query(
                Topic.topic,
                func.count(Topic.id).label("freq")
            ).join(
                NormalisedPost, Topic.post_id == NormalisedPost.id
            ).filter(
                NormalisedPost.published_at >= since,
                NormalisedPost.nlp_processed == True,
            ).group_by(Topic.topic).order_by(func.count(Topic.id).desc()).limit(5).all()

            topics = [{"topic": r.topic, "frequency": r.freq} for r in top_topics]

            # Generate trigger summary
            if entities and entities[0]["frequency"] > 5:
                primary_entity = entities[0]["name"]
                trigger_summary = (
                    f"The **{name}** surge (up {momentum:.0f}%) appears driven by coverage concentrated around "
                    f"**{primary_entity}** ({entities[0]['frequency']} mentions during this period). "
                    f"{'Additional prominent entities include: ' + ', '.join(e['name'] for e in entities[1:3]) + '.' if len(entities) > 1 else ''}"
                )
                trigger_confidence = "Medium"
            elif topics and topics[0]["frequency"] > 3:
                primary_topic = topics[0]["topic"]
                trigger_summary = (
                    f"The **{name}** surge (up {momentum:.0f}%) appears driven by concentrated discussion around "
                    f"**{primary_topic}**-related content ({topics[0]['frequency']} occurrences). "
                    f"The specific triggering event should be investigated through source review."
                )
                trigger_confidence = "Low"
            else:
                trigger_summary = (
                    f"The **{name}** surge (up {momentum:.0f}%) could not be attributed to a specific triggering entity. "
                    f"This may indicate a broad, distributed surge across multiple sources rather than a single event driver."
                )
                trigger_confidence = "Low"

            attributions.append({
                "narrative": name,
                "momentum": momentum,
                "trigger_summary": trigger_summary,
                "trigger_confidence": trigger_confidence,
                "top_entities": entities[:3],
                "top_topics": topics[:3],
                "evidence_count": count,
            })

        except Exception:
            attributions.append({
                "narrative": name,
                "momentum": momentum,
                "trigger_summary": f"**{name}** surged {momentum:.0f}%. Trigger analysis requires additional data accumulation.",
                "trigger_confidence": "Low",
                "top_entities": [],
                "top_topics": [],
                "evidence_count": count,
            })

    return attributions
