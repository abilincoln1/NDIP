"""
Source Quality Engine & Data Quality Assessment
Gives executives confidence scoring on every intelligence output.
"""
from datetime import datetime, timedelta, timezone
from sqlalchemy.orm import Session
from sqlalchemy import func, Integer
from app.models.models import NormalisedPost, SocialPost, ConnectorHealthLog


def get_source_quality_report(db: Session, days: int = 7) -> dict:
    since = datetime.now(timezone.utc) - timedelta(days=days)

    # Volume per source
    rows = db.query(
        NormalisedPost.source_platform,
        func.count(NormalisedPost.id).label("total"),
        func.sum(func.cast(NormalisedPost.nlp_processed == True, Integer)).label("processed"),
        func.max(NormalisedPost.ingested_at).label("last_seen"),
    ).filter(
        NormalisedPost.published_at >= since
    ).group_by(NormalisedPost.source_platform).all()

    now = datetime.now(timezone.utc)
    sources = []
    total_records = 0
    total_processed = 0

    for r in rows:
        freshness_hours = (now - r.last_seen.replace(tzinfo=timezone.utc)).total_seconds() / 3600 if r.last_seen else 999
        freshness_label = "Last hour" if freshness_hours < 1 else \
                          f"Last {int(freshness_hours)}h" if freshness_hours < 24 else \
                          f"Last {int(freshness_hours/24)}d"
        freshness_score = 1.0 if freshness_hours < 24 else 0.7 if freshness_hours < 72 else 0.3

        proc = int(r.processed or 0)
        processing_rate = round(proc / max(r.total, 1) * 100, 1)
        quality_score = round((processing_rate / 100) * 0.5 + freshness_score * 0.5, 2)

        sources.append({
            "platform": r.source_platform.replace("_", " ").title(),
            "platform_id": r.source_platform,
            "total_records": r.total,
            "nlp_processed": proc,
            "processing_rate": processing_rate,
            "last_seen": freshness_label,
            "freshness_score": freshness_score,
            "quality_score": quality_score,
            "quality_label": "High" if quality_score >= 0.7 else "Medium" if quality_score >= 0.4 else "Low",
        })
        total_records += r.total
        total_processed += proc

    # Overall confidence
    source_count = len(sources)
    overall_processing = round(total_processed / max(total_records, 1) * 100, 1)
    diversity_score = min(source_count / 5, 1.0)
    overall_confidence = round((overall_processing / 100 * 0.6 + diversity_score * 0.4), 2)

    return {
        "sources": sorted(sources, key=lambda x: x["total_records"], reverse=True),
        "total_records": total_records,
        "total_processed": total_processed,
        "processing_rate": overall_processing,
        "source_count": source_count,
        "overall_confidence": overall_confidence,
        "overall_confidence_label": "High" if overall_confidence >= 0.7 else "Medium" if overall_confidence >= 0.4 else "Low",
        "summary": f"Intelligence based on {total_records} records from {source_count} sources. "
                   f"NLP processing rate: {overall_processing}%. "
                   f"Overall confidence: {'High' if overall_confidence >= 0.7 else 'Medium' if overall_confidence >= 0.4 else 'Low'}.",
    }


def get_data_quality_report(db: Session) -> dict:
    from app.models.models import Topic, NamedEntity
    from app.analytics.topic_quality import is_valid_topic

    total_raw = db.query(func.count(SocialPost.id)).scalar() or 0
    total_norm = db.query(func.count(NormalisedPost.id)).scalar() or 0
    total_nlp = db.query(func.count(NormalisedPost.id)).filter(
        NormalisedPost.nlp_processed == True
    ).scalar() or 0

    # Topic quality
    all_topics = db.query(Topic.name).distinct().all()
    valid_topics = sum(1 for (t,) in all_topics if is_valid_topic(t))
    invalid_topics = len(all_topics) - valid_topics

    flags = []
    if total_nlp / max(total_norm, 1) < 0.8:
        flags.append({"type": "Warning", "message": f"Only {total_nlp/max(total_norm,1)*100:.0f}% of records NLP-processed."})
    if invalid_topics > valid_topics * 0.2:
        flags.append({"type": "Information", "message": f"{invalid_topics} low-quality topics detected and filtered."})
    if total_norm / max(total_raw, 1) < 0.9:
        flags.append({"type": "Information", "message": f"{total_raw - total_norm} raw records pending normalisation."})

    return {
        "total_ingested": total_raw,
        "total_normalised": total_norm,
        "total_nlp_processed": total_nlp,
        "normalisation_rate": round(total_norm / max(total_raw, 1) * 100, 1),
        "nlp_rate": round(total_nlp / max(total_norm, 1) * 100, 1),
        "valid_topics": valid_topics,
        "invalid_topics_filtered": invalid_topics,
        "topic_quality_rate": round(valid_topics / max(len(all_topics), 1) * 100, 1),
        "flags": flags,
        "overall_quality": "High" if not flags else "Medium" if len(flags) <= 1 else "Low",
    }
