from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from datetime import datetime, timedelta, timezone
from app.db.database import get_db
from app.core.security import get_current_user
from app.services.cache import get_cached, set_cached, cache_key, TTL_NARRATIVES
from app.models.models import NamedEntity, NormalisedPost

router = APIRouter(prefix="/entity-intelligence", tags=["entity-intelligence"])


def _get_entity_sentiment(db: Session, entity_name: str, since: datetime) -> str:
    """Get average sentiment for posts mentioning this entity."""
    try:
        posts = db.query(NormalisedPost.sentiment_score).join(
            NamedEntity, NamedEntity.post_id == NormalisedPost.id
        ).filter(
            NamedEntity.name == entity_name,
            NormalisedPost.published_at >= since,
        ).limit(50).all()
        if not posts:
            return "neutral"
        avg = sum(p[0] or 0 for p in posts) / len(posts)
        return "positive" if avg > 0.05 else "negative" if avg < -0.05 else "neutral"
    except Exception:
        return "neutral"


@router.get("/")
def entity_intelligence(
    days: int = Query(7, ge=1, le=30),
    db: Session = Depends(get_db),
    _: dict = Depends(get_current_user),
):
    ck = cache_key("entity-intelligence", f"days={days}")
    cached = get_cached(ck)
    if cached:
        return cached

    since = datetime.now(timezone.utc) - timedelta(days=days)
    prev_since = datetime.now(timezone.utc) - timedelta(days=days * 2)

    # Get NLP status
    try:
        from app.analytics.nlp_enhanced import get_nlp_status
        nlp_status = get_nlp_status()
    except Exception:
        nlp_status = {"spacy_available": False, "entity_extraction": "Fallback", "model": "none"}

    # Get top entities by mention count
    rows = db.query(
        NamedEntity.name,
        NamedEntity.entity_type,
        func.count(NamedEntity.id).label("mention_count"),
    ).join(
        NormalisedPost, NamedEntity.post_id == NormalisedPost.id
    ).filter(
        NormalisedPost.published_at >= since,
    ).group_by(
        NamedEntity.name, NamedEntity.entity_type
    ).order_by(desc("mention_count")).limit(100).all()

    # Get previous period for velocity
    prev_rows = db.query(
        NamedEntity.name,
        func.count(NamedEntity.id).label("prev_count"),
    ).join(
        NormalisedPost, NamedEntity.post_id == NormalisedPost.id
    ).filter(
        NormalisedPost.published_at >= prev_since,
        NormalisedPost.published_at < since,
    ).group_by(NamedEntity.name).all()

    prev_map = {r.name: r.prev_count for r in prev_rows}

    entities = []
    by_type: dict = {}

    for r in rows:
        prev = prev_map.get(r.name, 0)
        velocity = ((r.mention_count - prev) / max(prev, 1) * 100) if prev > 0 else 0
        trend = "rising" if velocity > 20 else "falling" if velocity < -20 else "stable"
        sentiment = _get_entity_sentiment(db, r.name, since)
        entity_type = r.entity_type or "OTHER"
        if entity_type not in by_type:
            by_type[entity_type] = 0
        by_type[entity_type] += 1

        entities.append({
            "name": r.name,
            "entity_type": entity_type,
            "mention_count": r.mention_count,
            "prev_count": prev,
            "velocity": round(velocity, 1),
            "trend": trend,
            "sentiment_label": sentiment,
        })

    # Fastest rising
    fastest_rising = sorted(
        [e for e in entities if e["velocity"] > 0 and e["prev_count"] > 0],
        key=lambda x: x["velocity"], reverse=True
    )[:5]

    result = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "period_days": days,
        "total_entities": len(entities),
        "entities": entities,
        "by_type": by_type,
        "fastest_rising": fastest_rising,
        "nlp_status": nlp_status,
    }

    set_cached(ck, result, TTL_NARRATIVES)
    return result
