"""
NLP Engine v2 - with topic quality controls
Sentiment, topic extraction with validation, narrative detection.
"""
import re
from collections import Counter
from typing import Optional
from textblob import TextBlob
from sqlalchemy.orm import Session

from app.models.models import SentimentRecord, SentimentLabel, SocialPost, Topic
from app.analytics.topic_quality import is_valid_topic, categorise_topic, ALL_EXCLUSIONS, deduplicate_topics, resolve_entity_alias
from datetime import datetime, timezone, timedelta


def classify_sentiment(text: str) -> tuple[SentimentLabel, float]:
    if not text or not text.strip():
        return SentimentLabel.neutral, 0.0
    blob = TextBlob(text[:1000])
    polarity = blob.sentiment.polarity
    if polarity > 0.1:
        label = SentimentLabel.positive
    elif polarity < -0.1:
        label = SentimentLabel.negative
    else:
        label = SentimentLabel.neutral
    return label, round(polarity, 4)


def analyse_and_store(db: Session, post: SocialPost) -> Optional[SentimentRecord]:
    if not post.content_text:
        return None
    if post.sentiment:
        return post.sentiment
    label, score = classify_sentiment(post.content_text)
    record = SentimentRecord(
        post_id=post.id, label=label, score=score, model_used="textblob"
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


def extract_topics(texts: list[str], top_n: int = 30) -> list[tuple[str, int]]:
    """Extract topics with quality filtering — no HTML/UI/metadata terms."""
    word_counts: Counter = Counter()
    for text in texts:
        if not text:
            continue
        # Remove URLs
        text = re.sub(r'http\S+|www\.\S+', '', text.lower())
        # Remove HTML tags
        text = re.sub(r'<[^>]+>', ' ', text)
        # Remove special characters
        text = re.sub(r'[^\w\s\-]', ' ', text)
        words = re.findall(r'\b[a-z][a-z\-]{3,}\b', text)
        # Only count words that pass quality validation
        word_counts.update(w for w in words if is_valid_topic(w))

    raw = word_counts.most_common(top_n * 2)
    deduped = deduplicate_topics(raw)
    return [(t, c) for t, c in deduped if is_valid_topic(t.split()[0]) or len(t.split()) > 1][:top_n]


def store_topics(
    db: Session,
    topics: list[tuple[str, int]],
    platform: Optional[str] = None,
    date_bucket: Optional[datetime] = None,
) -> int:
    """Store validated topics. Returns count of topics stored."""
    from app.analytics.topic_quality import filter_and_enrich_topics
    bucket = date_bucket or datetime.now(timezone.utc).replace(
        hour=0, minute=0, second=0, microsecond=0
    )
    yesterday = bucket - timedelta(days=1)

    # Filter topics through quality controls
    enriched, rejected = filter_and_enrich_topics(topics, source_count=1, total_posts=100)
    stored = 0

    for t in enriched:
        name = t["topic"]
        count = t["count"]
        prev = db.query(Topic).filter(
            Topic.name == name,
            Topic.date_bucket >= yesterday,
            Topic.date_bucket < bucket,
        ).first()
        prev_count = prev.mention_count if prev else 0
        momentum = (count - prev_count) / max(prev_count, 1)

        topic = Topic(
            name=name,
            platform=platform,
            mention_count=count,
            date_bucket=bucket,
            momentum_score=round(momentum, 4),
        )
        db.add(topic)
        stored += 1

    db.commit()
    return stored


def get_top_topics(db: Session, days: int = 7, limit: int = 20) -> list[dict]:
    from sqlalchemy import func
    from datetime import timezone
    since = datetime.now(timezone.utc) - timedelta(days=days)

    rows = db.query(
        Topic.name,
        func.sum(Topic.mention_count).label("total"),
        func.avg(Topic.momentum_score).label("momentum"),
    ).filter(
        Topic.date_bucket >= since
    ).group_by(Topic.name).order_by(
        func.sum(Topic.mention_count).desc()
    ).limit(limit * 2).all()  # fetch extra to allow filtering

    results = []
    for r in rows:
        if not is_valid_topic(r.name):
            continue
        category = categorise_topic(r.name)
        results.append({
            "name": r.name,
            "count": int(r.total),
            "momentum": round(float(r.momentum or 0), 4),
            "category": category,
        })
        if len(results) >= limit:
            break

    return results
