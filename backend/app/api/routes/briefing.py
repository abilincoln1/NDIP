from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime, timedelta, timezone

from app.db.database import get_db
from app.core.security import get_current_user
from app.analytics.engine import compute_all_metrics
from app.analytics.intelligence import (
    get_sentiment_trends, get_emerging_topics,
    get_narrative_trends, get_top_entities,
)
from app.models.models import NormalisedPost, AnalyticsSnapshot

router = APIRouter(prefix="/briefing", tags=["briefing"])


@router.get("/executive")
def executive_briefing(
    days: int = Query(7, ge=1, le=90),
    db: Session = Depends(get_db),
    _: dict = Depends(get_current_user),
):
    now = datetime.now(timezone.utc)
    since = now - timedelta(days=days)
    prev_since = since - timedelta(days=days)

    # Current metrics
    metrics = compute_all_metrics(db, days)

    # Previous period metrics for comparison
    prev_snap = db.query(AnalyticsSnapshot).filter(
        AnalyticsSnapshot.snapshot_date >= prev_since,
        AnalyticsSnapshot.snapshot_date < since,
    ).order_by(AnalyticsSnapshot.snapshot_date.desc()).first()

    # Sentiment shift
    sentiment_trends = get_sentiment_trends(db, days)
    avg_sentiment_now = (
        sum(t["avg_score"] for t in sentiment_trends[-3:]) / max(len(sentiment_trends[-3:]), 1)
        if sentiment_trends else 0
    )
    avg_sentiment_prev = (
        sum(t["avg_score"] for t in sentiment_trends[:3]) / max(len(sentiment_trends[:3]), 1)
        if len(sentiment_trends) > 3 else 0
    )
    sentiment_shift = round(avg_sentiment_now - avg_sentiment_prev, 4)

    # Emerging topics
    emerging = get_emerging_topics(db, days)

    # Top narratives
    narratives = get_narrative_trends(db, days)[:5]

    # Top entities
    entities = get_top_entities(db, days, limit=10)

    # Anomaly detection
    anomalies = []
    if metrics["growth_rate"] < -0.1:
        anomalies.append({
            "type": "warning",
            "message": f"Participant growth rate is {metrics['growth_rate']*100:.1f}% — significantly negative.",
        })
    if metrics["sentiment_score"] < -0.3:
        anomalies.append({
            "type": "alert",
            "message": f"Aggregate sentiment score is {metrics['sentiment_score']:.2f} — strongly negative discourse detected.",
        })
    if sentiment_shift < -0.2:
        anomalies.append({
            "type": "warning",
            "message": f"Sentiment shifted by {sentiment_shift:.2f} this period — negative trend detected.",
        })
    if len(emerging) > 3:
        anomalies.append({
            "type": "info",
            "message": f"{len(emerging)} emerging topics detected with high velocity.",
        })

    # Key insights
    insights = []
    if metrics["total_participants"] > 0:
        insights.append(f"{metrics['total_participants']} total participants with {metrics['engagement_index']:.2f} engagement index.")
    if narratives:
        top_narrative = narratives[0]["narrative"]
        insights.append(f"Dominant narrative: '{top_narrative}' ({narratives[0]['count']} mentions).")
    if entities:
        top_entity = entities[0]["entity"]
        insights.append(f"Most mentioned entity: '{top_entity}' ({entities[0]['count']} times).")
    if emerging:
        insights.append(f"Emerging topic: '{emerging[0]['topic']}' showing {emerging[0]['velocity']*100:.0f}% velocity increase.")

    # NLP post count
    nlp_count = db.query(func.count(NormalisedPost.id)).filter(
        NormalisedPost.published_at >= since,
        NormalisedPost.nlp_processed == True,
    ).scalar() or 0

    return {
        "period_days": days,
        "generated_at": now.isoformat(),
        "metrics": metrics,
        "sentiment_shift": sentiment_shift,
        "posts_analysed": nlp_count,
        "key_insights": insights,
        "anomalies": anomalies,
        "top_narratives": narratives,
        "top_entities": entities,
        "emerging_topics": emerging,
        "executive_summary": (
            f"Over the past {days} days, the observatory analysed {nlp_count} public posts "
            f"across multiple sources. Participant engagement index stands at "
            f"{metrics['engagement_index']:.2f}. "
            f"{'Sentiment improved' if sentiment_shift > 0 else 'Sentiment declined'} "
            f"by {abs(sentiment_shift):.2f} points. "
            f"{len(anomalies)} anomalies detected requiring attention."
        ),
    }
