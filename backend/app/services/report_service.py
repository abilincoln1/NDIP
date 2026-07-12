"""
Reporting service — generates neutral, factual intelligence reports.
Tone: analytical, non-persuasive, aggregated data only.
"""
import json
from datetime import datetime, timezone
from sqlalchemy.orm import Session

from app.models.models import Report, ReportPeriod, Engagement, Participant
from app.analytics.engine import (
    compute_all_metrics, get_engagement_by_type,
    get_geography, get_sentiment_distribution
)
from app.analytics.nlp import get_top_topics
from sqlalchemy import func


def generate_report(
    db: Session,
    period: str,
    period_start: datetime,
    period_end: datetime,
    title: str | None = None,
) -> Report:
    """
    Generate a complete intelligence report for the given period.
    All data is aggregated — no individual-level content.
    """
    days = max((period_end - period_start).days, 1)

    # Collect all data sections
    metrics = compute_all_metrics(db, days=days)
    engagement_by_type = get_engagement_by_type(db, days=days)
    geography = get_geography(db)
    sentiment = get_sentiment_distribution(db, days=days)
    topics = get_top_topics(db, days=days, limit=15)

    # Anomaly detection: flag metrics outside expected ranges
    anomalies = []
    if metrics["growth_rate"] < -0.05:
        anomalies.append("Participant growth rate is negative — review engagement channels.")
    if metrics["sentiment_score"] < -0.3:
        anomalies.append("Aggregate sentiment score below -0.3 — review public discourse data.")
    if metrics["engagement_index"] < 0.1:
        anomalies.append("Engagement index below threshold — participation activity is low.")

    # Event attendance summary
    from app.models.models import EventAttendance, Event
    event_count = db.query(func.count(Event.id)).filter(
        Event.starts_at >= period_start,
        Event.starts_at <= period_end,
    ).scalar() or 0

    attendance_count = db.query(func.count(EventAttendance.id)).filter(
        EventAttendance.registered_at >= period_start,
        EventAttendance.registered_at <= period_end,
    ).scalar() or 0

    report_content = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "period": {"start": period_start.isoformat(), "end": period_end.isoformat(), "days": days},
        "summary": {
            "total_participants": metrics["total_participants"],
            "new_participants": metrics["new_participants_7d"],
            "total_engagements": metrics["total_engagements"],
            "events_held": event_count,
            "event_attendances": attendance_count,
        },
        "metrics": {
            "engagement_index": metrics["engagement_index"],
            "participation_index": metrics["participation_index"],
            "growth_rate": metrics["growth_rate"],
            "sentiment_score": metrics["sentiment_score"],
            "topic_momentum_score": metrics["topic_momentum_score"],
        },
        "engagement_breakdown": engagement_by_type,
        "geography": geography[:20],  # top 20 countries
        "sentiment": sentiment,
        "top_topics": topics,
        "anomalies": anomalies,
        "note": (
            "This report contains aggregated, anonymised data only. "
            "No individual-level data is included. "
            "All analysis is factual and non-persuasive."
        ),
    }

    report = Report(
        title=title or f"{period.capitalize()} Report — {period_start.date()} to {period_end.date()}",
        period=ReportPeriod(period),
        period_start=period_start,
        period_end=period_end,
        content_json=json.dumps(report_content, default=str),
        generated_by="analytics_engine_v1",
    )
    db.add(report)
    db.commit()
    db.refresh(report)
    return report
