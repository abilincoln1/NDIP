"""
Intelligence Engine v2 — with topic quality controls and confidence scoring.
All outputs validated through topic_quality layer.
"""
import json
import re
from collections import Counter
from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy.orm import Session
from sqlalchemy import func, Integer

from app.models.models import (
    NormalisedPost, NamedEntity, NarrativeTrend, SentimentLabel,
    Topic, AnalyticsSnapshot, SocialMetric
)
from app.analytics.topic_quality import (
    is_valid_topic, categorise_topic, filter_and_enrich_topics, ALL_EXCLUSIONS
)

STOPWORDS = ALL_EXCLUSIONS

NARRATIVE_PATTERNS = [
    ("diaspora_advocacy", ["advocacy", "represent", "policy", "diaspora", "voice", "rights"]),
    ("community_growth", ["community", "grow", "expand", "network", "connect"]),
    ("economic_development", ["economy", "invest", "business", "trade", "finance", "remittance"]),
    ("cultural_identity", ["culture", "identity", "heritage", "tradition", "origin"]),
    ("political_engagement", ["election", "vote", "political", "government", "democracy", "civic"]),
    ("social_challenges", ["challenge", "problem", "crisis", "issue", "concern", "struggle"]),
    ("positive_achievement", ["achieve", "success", "award", "pride", "celebrate", "milestone"]),
    ("media_representation", ["media", "journalism", "narrative", "coverage", "representation"]),
    ("security_concerns", ["security", "safety", "crime", "violence", "conflict", "threat"]),
    ("economic_hardship", ["inflation", "poverty", "unemployment", "hardship", "cost", "price"]),
]

try:
    import spacy
    nlp = spacy.load("en_core_web_sm")
    SPACY_AVAILABLE = True
except Exception:
    nlp = None
    SPACY_AVAILABLE = False

from textblob import TextBlob


def analyse_sentiment(text: str) -> tuple[str, float]:
    if not text or not text.strip():
        return "neutral", 0.0
    blob = TextBlob(text[:1500])
    score = round(blob.sentiment.polarity, 4)
    if score > 0.1: return "positive", score
    elif score < -0.1: return "negative", score
    return "neutral", score


def extract_entities(text: str) -> list[str]:
    """Extract named entities using spaCy when available."""
    try:
        from app.analytics.nlp_enhanced import extract_entities as _spacy_extract
        entities = _spacy_extract(text)
        return [e["name"] for e in entities if e.get("name")]
    except Exception:
        pass
    # Fallback: capitalised phrase extraction
    import re
    pattern = r'\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\b'
    matches = re.findall(pattern, text or "")
    suppress = {
        "Nigeria","Nigerian","Nigerians","Monday","Tuesday","Wednesday","Thursday",
        "Friday","Saturday","Sunday","The","This","That","President","Minister",
        "Governor","Senator","According","However","Meanwhile","Although"
    }
    return [m for m in dict.fromkeys(matches) if m not in suppress and len(m) > 2][:15]


def extract_topics_from_text(text: str, top_n: int = 10) -> list[str]:
    if not text:
        return []
    text_clean = re.sub(r'http\S+|<[^>]+>', '', text.lower())
    text_clean = re.sub(r'[^\w\s\-]', ' ', text_clean)
    words = re.findall(r'\b[a-z][a-z\-]{3,}\b', text_clean)
    filtered = [w for w in words if is_valid_topic(w)]
    counts = Counter(filtered)
    return [w for w, _ in counts.most_common(top_n)]


def detect_narratives(text: str) -> list[str]:
    if not text:
        return []
    text_lower = text.lower()
    matched = []
    for narrative_id, keywords in NARRATIVE_PATTERNS:
        hits = sum(1 for kw in keywords if kw in text_lower)
        if hits >= 2:
            matched.append(narrative_id)
    return matched


def check_nlp_pipeline_health(db: Session, sample_size: int = 10) -> dict:
    """
    Read-only health check: exercises the real entity-extraction path on a
    small sample of pending posts WITHOUT writing anything to the database,
    so it's safe to call from risk-detection logic (which should never have
    side effects of its own).

    This exists because a backlog-percentage check alone can't distinguish
    "nothing has run yet" from "it ran and crashed on every single post" —
    both show the same low processed percentage. This was exactly how the
    V5.4 entity-extraction bug (ent["text"] on a plain string, guaranteed
    TypeError on every post) went undetected: the pipeline reported "Done"
    on every run while genuinely processing zero posts, every time.

    Returns: {"sample_size": int, "errors": int, "error_rate": float,
              "sample_error": str | None}
    """
    posts = db.query(NormalisedPost).filter(
        NormalisedPost.nlp_processed == False,
        NormalisedPost.text.isnot(None),
    ).limit(sample_size).all()

    if not posts:
        return {"sample_size": 0, "errors": 0, "error_rate": 0.0, "sample_error": None}

    from app.analytics.nlp_enhanced import extract_entities as _extract_entities_full
    errors = 0
    sample_error = None
    for post in posts:
        try:
            text = post.text or ""
            raw_entities = _extract_entities_full(text)
            # Exercise the same dict access process_post relies on, without
            # committing anything — this is what would have caught the bug.
            for e in raw_entities:
                _ = e["name"]
                _ = e.get("entity_type", "OTHER")
        except Exception as e:
            errors += 1
            if sample_error is None:
                sample_error = f"{type(e).__name__}: {e}"

    return {
        "sample_size": len(posts),
        "errors": errors,
        "error_rate": errors / len(posts),
        "sample_error": sample_error,
    }


def process_post(db: Session, post: NormalisedPost) -> NormalisedPost:
    if post.nlp_processed:
        return post
    text = post.text or ""
    label, score = analyse_sentiment(text)
    post.sentiment_label = label
    post.sentiment_score = score

    # Use the real entity extractor (nlp_enhanced.extract_entities), which
    # returns list[dict] with keys "name"/"entity_type" — not the lossy
    # list[str] wrapper previously used here, which caused every single
    # entity-storage attempt below to crash with "string indices must be
    # integers, not 'str'" (ent["text"] on a plain string). entities_json
    # is documented on the model as a JSON list of {text, label}, so we
    # normalise to that shape here.
    from app.analytics.nlp_enhanced import extract_entities as _extract_entities_full
    raw_entities = _extract_entities_full(text)
    entities = [
        {"text": e["name"], "label": e.get("entity_type", "OTHER")}
        for e in raw_entities if e.get("name")
    ]
    post.entities_json = json.dumps(entities)

    topics = extract_topics_from_text(text)
    post.topics_json = json.dumps(topics)
    narratives = detect_narratives(text)
    post.narrative_tags = json.dumps(narratives)
    bucket = (post.published_at or post.ingested_at).replace(
        hour=0, minute=0, second=0, microsecond=0
    )
    for ent in entities[:10]:
        db.add(NamedEntity(
            post_id=post.id, text=ent["text"], label=ent["label"],
            platform=post.source_platform, date_bucket=bucket,
        ))
    post.nlp_processed = True
    post.nlp_processed_at = datetime.now(timezone.utc)
    db.add(post)
    db.commit()
    db.refresh(post)
    return post


def process_unprocessed_batch(db: Session, limit: int = 200) -> int:
    """
    Process up to `limit` pending posts. Returns the count successfully
    processed. For richer failure visibility (needed to distinguish "ran
    cleanly with nothing pending" from "ran and every attempt failed
    silently"), see process_unprocessed_batch_with_stats below.
    """
    processed, _errors = process_unprocessed_batch_with_stats(db, limit)
    return processed


def process_unprocessed_batch_with_stats(db: Session, limit: int = 200) -> tuple[int, int]:
    """
    Same as process_unprocessed_batch, but returns (processed_count,
    error_count) so callers can detect a 100%-failure batch — which looks
    identical to "nothing was pending" if only the success count is read,
    and was exactly how the V5.4 entity-extraction bug stayed invisible
    for an extended period despite the reprocessing script reporting
    "Done" on every run.
    """
    posts = db.query(NormalisedPost).filter(
        NormalisedPost.nlp_processed == False,
        NormalisedPost.text.isnot(None),
    ).limit(limit).all()
    count = 0
    errors = 0
    for post in posts:
        try:
            process_post(db, post)
            count += 1
        except Exception as e:
            print(f"[NLP] Error processing post {post.id}: {e}")
            errors += 1
    return count, errors


def reprocess_all(db: Session) -> dict:
    """Reprocess all posts with the upgraded pipeline."""
    # Reset nlp_processed flag
    db.query(NormalisedPost).update({"nlp_processed": False})
    db.commit()
    # Clear invalid topics
    from app.models.models import Topic as TopicModel, NamedEntity as NEModel
    deleted_topics = 0
    all_topics = db.query(TopicModel).all()
    for t in all_topics:
        if not is_valid_topic(t.name):
            db.delete(t)
            deleted_topics += 1
    db.commit()
    # Reprocess
    total = 0
    batch = 200
    while True:
        processed = process_unprocessed_batch(db, batch)
        total += processed
        if processed < batch:
            break
    return {"reprocessed": total, "invalid_topics_removed": deleted_topics}


def get_sentiment_trends(db: Session, days: int = 30, platform: Optional[str] = None) -> list[dict]:
    since = datetime.now(timezone.utc) - timedelta(days=days)
    query = db.query(NormalisedPost).filter(
        NormalisedPost.published_at >= since,
        NormalisedPost.nlp_processed == True,
    )
    if platform:
        query = query.filter(NormalisedPost.source_platform == platform)
    posts = query.all()
    by_day: dict = {}
    for p in posts:
        day = p.published_at.strftime("%Y-%m-%d") if p.published_at else "unknown"
        if day not in by_day:
            by_day[day] = {"positive": 0, "neutral": 0, "negative": 0, "total": 0, "score_sum": 0.0}
        by_day[day][p.sentiment_label or "neutral"] += 1
        by_day[day]["total"] += 1
        by_day[day]["score_sum"] += p.sentiment_score or 0.0
    result = []
    for day in sorted(by_day.keys()):
        d = by_day[day]
        total = max(d["total"], 1)
        result.append({
            "date": day,
            "positive_pct": round(d["positive"] / total * 100, 1),
            "neutral_pct": round(d["neutral"] / total * 100, 1),
            "negative_pct": round(d["negative"] / total * 100, 1),
            "avg_score": round(d["score_sum"] / total, 4),
            "total": d["total"],
        })
    return result


def get_top_entities(db: Session, days: int = 7, label: Optional[str] = None, limit: int = 20) -> list[dict]:
    since = datetime.now(timezone.utc) - timedelta(days=days)
    query = db.query(
        NamedEntity.text, NamedEntity.label,
        func.count(NamedEntity.id).label("count")
    ).filter(NamedEntity.date_bucket >= since)
    if label:
        query = query.filter(NamedEntity.label == label)
    rows = query.group_by(NamedEntity.text, NamedEntity.label).order_by(
        func.count(NamedEntity.id).desc()
    ).limit(limit * 2).all()
    results = []
    for r in rows:
        if not is_valid_topic(r.text.split()[0] if r.text else ""):
            continue
        results.append({"entity": r.text, "type": r.label, "count": r.count})
        if len(results) >= limit:
            break
    return results


def get_narrative_trends(db: Session, days: int = 30) -> list[dict]:
    since = datetime.now(timezone.utc) - timedelta(days=days)
    posts = db.query(NormalisedPost).filter(
        NormalisedPost.published_at >= since,
        NormalisedPost.narrative_tags.isnot(None),
        NormalisedPost.nlp_processed == True,
    ).all()
    counts: Counter = Counter()
    sentiment_by_narrative: dict = {}
    for post in posts:
        try:
            tags = json.loads(post.narrative_tags or "[]")
        except Exception:
            tags = []
        for tag in tags:
            counts[tag] += 1
            if tag not in sentiment_by_narrative:
                sentiment_by_narrative[tag] = []
            if post.sentiment_score is not None:
                sentiment_by_narrative[tag].append(post.sentiment_score)
    result = []
    for narrative, count in counts.most_common(15):
        scores = sentiment_by_narrative.get(narrative, [])
        avg_sentiment = round(sum(scores) / len(scores), 4) if scores else 0.0
        result.append({
            "narrative": narrative.replace("_", " ").title(),
            "narrative_id": narrative,
            "count": count,
            "avg_sentiment": avg_sentiment,
        })
    return result


def get_source_comparison(db: Session, days: int = 30) -> list[dict]:
    since = datetime.now(timezone.utc) - timedelta(days=days)
    rows = db.query(
        NormalisedPost.source_platform,
        func.count(NormalisedPost.id).label("total"),
        func.avg(NormalisedPost.sentiment_score).label("avg_sentiment"),
        func.sum(func.cast(NormalisedPost.sentiment_label == "positive", Integer)).label("positive"),
        func.sum(func.cast(NormalisedPost.sentiment_label == "negative", Integer)).label("negative"),
    ).filter(
        NormalisedPost.published_at >= since,
        NormalisedPost.nlp_processed == True,
    ).group_by(NormalisedPost.source_platform).all()
    return [{
        "platform": r.source_platform,
        "total": r.total,
        "avg_sentiment": round(float(r.avg_sentiment or 0), 4),
        "positive": r.positive or 0,
        "negative": r.negative or 0,
    } for r in rows]


def get_trend_velocity(db: Session, days: int = 14) -> list[dict]:
    now = datetime.now(timezone.utc)
    mid = now - timedelta(days=days // 2)
    start = now - timedelta(days=days)
    def count_topics(posts):
        c: Counter = Counter()
        for p in posts:
            try:
                topics = json.loads(p.topics_json or "[]")
                c.update(t for t in topics if is_valid_topic(t))
            except Exception:
                pass
        return c
    recent = db.query(NormalisedPost).filter(
        NormalisedPost.published_at >= mid,
        NormalisedPost.topics_json.isnot(None),
        NormalisedPost.nlp_processed == True,
    ).all()
    older = db.query(NormalisedPost).filter(
        NormalisedPost.published_at >= start,
        NormalisedPost.published_at < mid,
        NormalisedPost.topics_json.isnot(None),
        NormalisedPost.nlp_processed == True,
    ).all()
    recent_counts = count_topics(recent)
    older_counts = count_topics(older)
    velocity = []
    for topic, count in recent_counts.most_common(30):
        if not is_valid_topic(topic):
            continue
        old_count = older_counts.get(topic, 0)
        vel = (count - old_count) / max(old_count, 1)
        category = categorise_topic(topic)
        velocity.append({
            "topic": topic,
            "category": category,
            "recent_count": count,
            "older_count": old_count,
            "velocity": round(vel, 4),
            "trending": vel > 0.5,
        })
    velocity.sort(key=lambda x: x["velocity"], reverse=True)
    return velocity[:15]


def get_emerging_topics(db: Session, days: int = 7) -> list[dict]:
    velocity = get_trend_velocity(db, days=days * 2)
    return [t for t in velocity if t["trending"] and t["older_count"] < 10][:10]


def get_intelligence_quality_stats(db: Session) -> dict:
    """Stats for the Intelligence Quality dashboard."""
    from app.models.models import Topic as TopicModel
    total_posts = db.query(func.count(NormalisedPost.id)).scalar() or 0
    processed = db.query(func.count(NormalisedPost.id)).filter(
        NormalisedPost.nlp_processed == True
    ).scalar() or 0
    total_topics = db.query(func.count(TopicModel.id)).scalar() or 0
    # Count what would be rejected
    all_topic_names = db.query(TopicModel.name).distinct().all()
    valid = sum(1 for (t,) in all_topic_names if is_valid_topic(t))
    invalid = len(all_topic_names) - valid
    return {
        "total_posts": total_posts,
        "posts_processed": processed,
        "posts_pending": total_posts - processed,
        "processing_rate": round(processed / max(total_posts, 1) * 100, 1),
        "unique_topics": len(all_topic_names),
        "valid_topics": valid,
        "invalid_topics": invalid,
        "topic_quality_rate": round(valid / max(len(all_topic_names), 1) * 100, 1),
    }
