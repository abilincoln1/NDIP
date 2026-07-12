"""
Analytics Engine — computes Engagement Index, Participation Index,
Growth Rate, Sentiment Score, and Topic Momentum from stored data.
All outputs are aggregated; no individual profiling.
"""
from datetime import datetime, timedelta, timezone
from typing import Optional
import pandas as pd
import numpy as np
from sqlalchemy.orm import Session
from sqlalchemy import func, text

from app.models.models import (
    Participant, Engagement, EventAttendance, SentimentRecord,
    Topic, AnalyticsSnapshot, SocialMetric
)


def _days_ago(days: int) -> datetime:
    return datetime.now(timezone.utc) - timedelta(days=days)


# ─── Core metric computations ─────────────────────────────────────────────────

def compute_engagement_index(db: Session, days: int = 30) -> float:
    """
    Engagement Index = total interactions in period / total participants
    Range: 0 → unbounded (>1 means participants engaged multiple times)
    """
    since = _days_ago(days)
    total_participants = db.query(func.count(Participant.id)).filter(
        Participant.consent_given == True
    ).scalar() or 1

    total_interactions = db.query(func.count(Engagement.id)).filter(
        Engagement.created_at >= since
    ).scalar() or 0

    return round(total_interactions / total_participants, 4)


def compute_participation_index(db: Session, days: int = 30) -> float:
    """
    Participation Index = unique active participants / total participants
    Range: 0.0 → 1.0
    """
    since = _days_ago(days)
    total = db.query(func.count(Participant.id)).filter(
        Participant.consent_given == True
    ).scalar() or 1

    active = db.query(func.count(Engagement.participant_id.distinct())).filter(
        Engagement.created_at >= since,
        Engagement.participant_id.isnot(None)
    ).scalar() or 0

    return round(min(active / total, 1.0), 4)


def compute_growth_rate(db: Session, days: int = 30) -> float:
    """
    Growth Rate = (new participants - churned) / total participants
    Churn proxy: participants with no engagement in 2× the period.
    """
    since = _days_ago(days)
    churn_threshold = _days_ago(days * 2)

    total = db.query(func.count(Participant.id)).filter(
        Participant.consent_given == True
    ).scalar() or 1

    new = db.query(func.count(Participant.id)).filter(
        Participant.created_at >= since,
        Participant.consent_given == True
    ).scalar() or 0

    # Participants with zero engagement over 2× period (proxy for churn)
    inactive_ids = db.query(Engagement.participant_id).filter(
        Engagement.created_at >= churn_threshold,
        Engagement.participant_id.isnot(None)
    ).distinct().subquery()

    churned = db.query(func.count(Participant.id)).filter(
        Participant.id.not_in(inactive_ids),
        Participant.consent_given == True
    ).scalar() or 0

    return round((new - churned) / total, 4)


def compute_sentiment_score(db: Session, days: int = 30) -> float:
    """
    Aggregate sentiment score: mean of all sentiment records in period.
    Range: -1.0 → 1.0
    """
    since = _days_ago(days)
    result = db.query(func.avg(SentimentRecord.score)).filter(
        SentimentRecord.created_at >= since
    ).scalar()
    return round(float(result or 0.0), 4)


def compute_topic_momentum(db: Session, days: int = 30) -> float:
    """
    Topic Momentum Score = mean momentum_score of topics in period.
    """
    since = _days_ago(days)
    result = db.query(func.avg(Topic.momentum_score)).filter(
        Topic.date_bucket >= since,
        Topic.momentum_score.isnot(None)
    ).scalar()
    return round(float(result or 0.0), 4)


def compute_all_metrics(db: Session, days: int = 30) -> dict:
    since = _days_ago(days)

    total_participants = db.query(func.count(Participant.id)).filter(
        Participant.consent_given == True
    ).scalar() or 0

    total_engagements = db.query(func.count(Engagement.id)).filter(
        Engagement.created_at >= since
    ).scalar() or 0

    new_7d = db.query(func.count(Participant.id)).filter(
        Participant.created_at >= _days_ago(7),
        Participant.consent_given == True
    ).scalar() or 0

    return {
        "engagement_index": compute_engagement_index(db, days),
        "participation_index": compute_participation_index(db, days),
        "growth_rate": compute_growth_rate(db, days),
        "sentiment_score": compute_sentiment_score(db, days),
        "topic_momentum_score": compute_topic_momentum(db, days),
        "total_participants": total_participants,
        "total_engagements": total_engagements,
        "new_participants_7d": new_7d,
        "snapshot_date": datetime.now(timezone.utc),
    }


# ─── Trend data ───────────────────────────────────────────────────────────────

def get_metric_trend(db: Session, metric: str, days: int = 90) -> list[dict]:
    """Return historical snapshots for a specific metric."""
    since = _days_ago(days)
    snapshots = db.query(AnalyticsSnapshot).filter(
        AnalyticsSnapshot.snapshot_date >= since
    ).order_by(AnalyticsSnapshot.snapshot_date).all()

    return [
        {
            "date": s.snapshot_date.isoformat(),
            "value": getattr(s, metric, None),
        }
        for s in snapshots
        if getattr(s, metric, None) is not None
    ]


def get_engagement_by_type(db: Session, days: int = 30) -> dict:
    since = _days_ago(days)
    rows = db.query(
        Engagement.engagement_type,
        func.count(Engagement.id).label("count")
    ).filter(
        Engagement.created_at >= since
    ).group_by(Engagement.engagement_type).all()

    return {r.engagement_type: r.count for r in rows}


def get_geography(db: Session) -> list[dict]:
    """Aggregated participant counts by country."""
    rows = db.query(
        Participant.country,
        func.count(Participant.id).label("count")
    ).filter(
        Participant.consent_given == True,
        Participant.country.isnot(None)
    ).group_by(Participant.country).order_by(
        func.count(Participant.id).desc()
    ).all()

    return [{"country": r.country, "count": r.count} for r in rows]


# ─── Snapshot persistence ─────────────────────────────────────────────────────

def save_snapshot(db: Session, metrics: dict) -> AnalyticsSnapshot:
    snap = AnalyticsSnapshot(**{k: v for k, v in metrics.items()})
    db.add(snap)
    db.commit()
    db.refresh(snap)
    return snap


# ─── Sentiment distribution ───────────────────────────────────────────────────

def get_sentiment_distribution(db: Session, days: int = 30) -> dict:
    since = _days_ago(days)
    total = db.query(func.count(SentimentRecord.id)).filter(
        SentimentRecord.created_at >= since
    ).scalar() or 1

    rows = db.query(
        SentimentRecord.label,
        func.count(SentimentRecord.id).label("count")
    ).filter(
        SentimentRecord.created_at >= since
    ).group_by(SentimentRecord.label).all()

    dist = {r.label: r.count for r in rows}
    return {
        "positive_pct": round(dist.get("positive", 0) / total * 100, 1),
        "neutral_pct": round(dist.get("neutral", 0) / total * 100, 1),
        "negative_pct": round(dist.get("negative", 0) / total * 100, 1),
        "overall_score": compute_sentiment_score(db, days),
    }
