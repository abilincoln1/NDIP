"""
NDIP Entity Influence Intelligence v5.4
Transforms entity listing into influence assessment.
Scores: Influence, Momentum, Sentiment, Visibility, Leadership Index.
"""
from datetime import datetime, timezone, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import func


def compute_entity_influence_scores(db: Session, days: int) -> dict:
    from app.models.models import NamedEntity, NormalisedPost

    since = datetime.now(timezone.utc) - timedelta(days=days)
    prev_since = datetime.now(timezone.utc) - timedelta(days=days * 2)

    # Current period entities
    current = db.query(
        NamedEntity.text.label("name"),
        NamedEntity.label.label("entity_type"),
        func.count(NamedEntity.id).label("mentions"),
        func.avg(NormalisedPost.sentiment_score).label("avg_sentiment"),
        func.count(func.distinct(NormalisedPost.source_platform)).label("source_count"),
    ).join(NormalisedPost, NamedEntity.post_id == NormalisedPost.id).filter(
        NormalisedPost.published_at >= since,
    ).group_by(NamedEntity.text, NamedEntity.label).order_by(func.count(NamedEntity.id).desc()).limit(50).all()

    # Previous period for momentum
    prev = db.query(
        NamedEntity.text.label("name"),
        func.count(NamedEntity.id).label("prev_mentions"),
    ).join(NormalisedPost, NamedEntity.post_id == NormalisedPost.id).filter(
        NormalisedPost.published_at >= prev_since,
        NormalisedPost.published_at < since,
    ).group_by(NamedEntity.text).all()

    prev_map = {r.name: r.prev_mentions for r in prev}

    # Total mentions for visibility calculation
    total_mentions = sum(r.mentions for r in current) or 1

    entities = []
    for r in current:
        mentions = r.mentions
        prev_mentions = prev_map.get(r.name, 0)
        avg_sent = float(r.avg_sentiment or 0)
        sources = r.source_count or 1

        # Momentum
        if prev_mentions > 0:
            momentum = round((mentions - prev_mentions) / prev_mentions * 100, 1)
        else:
            momentum = 0
        momentum_direction = "rising" if momentum > 20 else "falling" if momentum < -20 else "stable"

        # Visibility score (0-100): share of total entity mentions
        visibility_score = min(100, round(mentions / total_mentions * 1000))

        # Sentiment score (0-100): 50=neutral, 100=very positive, 0=very negative
        sentiment_score = min(100, max(0, round(50 + avg_sent * 100)))
        sentiment_label = "positive" if avg_sent > 0.05 else "negative" if avg_sent < -0.05 else "neutral"

        # Influence score: visibility * source diversity * momentum factor
        momentum_factor = 1.2 if momentum > 50 else 1.1 if momentum > 0 else 0.9
        influence_score = min(100, round(visibility_score * (sources / 3) * momentum_factor))

        # Entity Leadership Index: composite
        leadership_index = min(100, round(
            influence_score * 0.4 +
            visibility_score * 0.3 +
            (100 - abs(50 - sentiment_score)) * 0.2 +
            min(sources * 10, 30) * 0.1
        ))

        entities.append({
            "name": r.name,
            "entity_type": r.entity_type or "UNKNOWN",
            "mentions": mentions,
            "prev_mentions": prev_mentions,
            "momentum": momentum,
            "momentum_direction": momentum_direction,
            "source_count": sources,
            "visibility_score": visibility_score,
            "sentiment_score": sentiment_score,
            "sentiment_label": sentiment_label,
            "influence_score": influence_score,
            "leadership_index": leadership_index,
        })

    # Rankings
    most_influential = sorted(entities, key=lambda x: x["influence_score"], reverse=True)[:5]
    fastest_rising = sorted([e for e in entities if e["momentum"] > 20 and e["prev_mentions"] > 0],
                            key=lambda x: x["momentum"], reverse=True)[:5]
    declining = sorted([e for e in entities if e["momentum"] < -20 and e["prev_mentions"] > 0],
                       key=lambda x: x["momentum"])[:3]
    highest_visibility = sorted(entities, key=lambda x: x["visibility_score"], reverse=True)[:5]

    # By type
    people = sorted([e for e in entities if e["entity_type"] == "PERSON"],
                   key=lambda x: x["influence_score"], reverse=True)[:5]
    orgs = sorted([e for e in entities if e["entity_type"] in ("ORGANISATION", "ORG")],
                 key=lambda x: x["influence_score"], reverse=True)[:5]
    locations = sorted([e for e in entities if e["entity_type"] in ("LOCATION", "GPE")],
                      key=lambda x: x["influence_score"], reverse=True)[:5]

    # Entity Watchlist — high influence + rising or negative sentiment
    watchlist = []
    for e in most_influential:
        if e["momentum_direction"] == "rising" and e["momentum"] > 50:
            watchlist.append({
                "entity": e["name"],
                "type": e["entity_type"],
                "alert": f"Rising influence — {e['momentum']:.0f}% momentum increase",
                "priority": "High",
            })
        elif e["sentiment_label"] == "negative" and e["influence_score"] > 20:
            watchlist.append({
                "entity": e["name"],
                "type": e["entity_type"],
                "alert": f"High-influence entity with negative sentiment",
                "priority": "Medium",
            })

    result = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "period_days": days,
        "total_entities": len(entities),
        "entities": entities,
        "most_influential": most_influential,
        "fastest_rising": fastest_rising,
        "declining": declining,
        "highest_visibility": highest_visibility,
        "people": people,
        "organisations": orgs,
        "locations": locations,
        "entity_watchlist": watchlist[:5],
    }

    # V5.8 Phase F — Entity Intelligence module self-evaluation.
    # Track momentum predictions for the fastest-rising entity and an
    # influence-persistence prediction for the top-influence entity.
    try:
        from app.services.recommendation_tracker import record_recommendation
        if fastest_rising:
            e = fastest_rising[0]
            record_recommendation(
                db,
                narrative=None,
                recommendation_text=(
                    f"{e['name']} ({e['entity_type']}) momentum is rising at {e['momentum']:+.0f}% — "
                    f"expected to maintain elevated visibility over the next reporting period."
                ),
                category="MONITOR",
                priority="Medium",
                confidence="Medium",
                time_horizon="14 days",
                supporting_evidence=f"{e['mentions']} mentions across {e['source_count']} sources",
                expected_outcome="Entity mention volume and momentum direction consistent with current trend",
                trigger_metric_name="mentions",
                trigger_metric_value=float(e["mentions"]),
                period_days=days,
                module="entity_intelligence",
            )
        if most_influential:
            e = most_influential[0]
            record_recommendation(
                db,
                narrative=None,
                recommendation_text=(
                    f"{e['name']} ({e['entity_type']}) remains the most influential tracked entity "
                    f"(influence score {e['influence_score']}) — expected to retain top influence "
                    f"ranking over the next reporting period."
                ),
                category="MONITOR",
                priority="Medium",
                confidence="Medium",
                time_horizon="14 days",
                supporting_evidence=f"Influence score={e['influence_score']}, leadership index={e['leadership_index']}",
                expected_outcome="Entity retains comparable influence ranking",
                trigger_metric_name="influence_score",
                trigger_metric_value=float(e["influence_score"]),
                period_days=days,
                module="entity_intelligence",
            )
    except Exception:
        try:
            db.rollback()
        except Exception:
            pass

    return result
