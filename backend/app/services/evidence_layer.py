"""
Evidence Layer & Executive Confidence System
Every insight shows: evidence count, sources, confidence, freshness.
Platform-wide confidence score with reasoning.
"""
from datetime import datetime, timedelta, timezone
from sqlalchemy.orm import Session
from sqlalchemy import func, text
from app.models.models import NormalisedPost, SocialPost


def get_narrative_evidence(db: Session, narrative: str, days: int = 7) -> dict:
    """Get full evidence breakdown for a narrative."""
    since = datetime.now(timezone.utc) - timedelta(days=days)

    # Count by source platform
    rows = db.query(
        NormalisedPost.source_platform,
        func.count(NormalisedPost.id).label("count"),
        func.max(NormalisedPost.ingested_at).label("last_seen"),
    ).filter(
        NormalisedPost.published_at >= since,
        NormalisedPost.nlp_processed == True,
    ).group_by(NormalisedPost.source_platform).all()

    now = datetime.now(timezone.utc)
    sources = []
    total = 0
    api_count = 0
    rss_count = 0
    freshest = None

    for r in rows:
        source_type = "api" if r.source_platform in ("youtube", "newsapi", "gdelt", "reddit", "twitter") else "rss"
        last = r.last_seen.replace(tzinfo=timezone.utc) if r.last_seen else now
        hours_ago = (now - last).total_seconds() / 3600

        if freshest is None or last > freshest:
            freshest = last

        sources.append({
            "platform": r.source_platform.replace("_", " ").title(),
            "count": r.count,
            "type": source_type,
            "freshness_hours": round(hours_ago, 1),
        })
        total += r.count
        if source_type == "api":
            api_count += r.count
        else:
            rss_count += r.count

    freshness_hours = (now - freshest).total_seconds() / 3600 if freshest else 999
    freshness_label = (
        "Last hour" if freshness_hours < 1 else
        f"Last {int(freshness_hours)}h" if freshness_hours < 24 else
        f"Last {int(freshness_hours/24)}d"
    )

    source_count = len(sources)
    diversity_score = min(source_count / 8, 1.0)
    volume_score = min(total / 100, 1.0)
    freshness_score = 1.0 if freshness_hours < 24 else 0.6 if freshness_hours < 72 else 0.2
    confidence = round((diversity_score * 0.4 + volume_score * 0.3 + freshness_score * 0.3) * 100)

    return {
        "narrative": narrative,
        "total_records": total,
        "source_count": source_count,
        "sources": sorted(sources, key=lambda x: x["count"], reverse=True)[:6],
        "api_records": api_count,
        "rss_records": rss_count,
        "freshness": freshness_label,
        "freshness_hours": round(freshness_hours, 1),
        "confidence_score": confidence,
        "confidence_label": "High" if confidence >= 70 else "Medium" if confidence >= 40 else "Low",
        "diversity_label": "High" if source_count >= 6 else "Medium" if source_count >= 3 else "Low",
    }


def get_platform_confidence(db: Session, days: int = 7) -> dict:
    """Platform-wide confidence score with full reasoning."""
    since = datetime.now(timezone.utc) - timedelta(days=days)

    total_records = db.query(func.count(NormalisedPost.id)).filter(
        NormalisedPost.published_at >= since
    ).scalar() or 0

    processed = db.query(func.count(NormalisedPost.id)).filter(
        NormalisedPost.published_at >= since,
        NormalisedPost.nlp_processed == True,
    ).scalar() or 0

    source_rows = db.query(
        NormalisedPost.source_platform,
        func.count(NormalisedPost.id).label("cnt"),
    ).filter(
        NormalisedPost.published_at >= since
    ).group_by(NormalisedPost.source_platform).all()

    source_count = len(source_rows)
    total_vol = sum(r.cnt for r in source_rows)
    top_source_pct = (max(r.cnt for r in source_rows) / max(total_vol, 1) * 100) if source_rows else 100
    nlp_rate = round(processed / max(total_records, 1) * 100, 1)

    # Component scores
    volume_score = min(total_records / 500, 1.0)
    diversity_score = min(source_count / 10, 1.0)
    concentration_score = max(0, 1 - max(0, top_source_pct - 50) / 50)
    nlp_score = nlp_rate / 100

    overall = round((volume_score * 0.25 + diversity_score * 0.30 +
                     concentration_score * 0.20 + nlp_score * 0.25) * 100)

    reasons = []
    if source_count >= 8:
        reasons.append(f"{source_count} active sources providing diverse coverage")
    elif source_count >= 4:
        reasons.append(f"{source_count} active sources — moderate diversity")
    else:
        reasons.append(f"Only {source_count} active sources — limited diversity")

    reasons.append(f"{total_records:,} records analysed in the {days}-day window")

    if nlp_rate >= 95:
        reasons.append(f"{nlp_rate}% NLP success rate")
    else:
        reasons.append(f"{nlp_rate}% NLP processing rate — some records incomplete")

    if top_source_pct > 70:
        reasons.append(f"Source concentration risk: one source accounts for {top_source_pct:.0f}% of content")

    return {
        "overall_score": overall,
        "overall_label": "High" if overall >= 70 else "Medium" if overall >= 45 else "Low",
        "source_diversity": f"{source_count} active sources",
        "source_diversity_score": round(diversity_score * 100),
        "evidence_volume": f"{total_records:,} records",
        "evidence_volume_score": round(volume_score * 100),
        "data_freshness": "Last 24 hours" if days <= 1 else f"Last {days} days",
        "nlp_success_rate": nlp_rate,
        "coverage_quality": "High" if source_count >= 8 and nlp_rate >= 90 else "Medium" if source_count >= 4 else "Low",
        "narrative_reliability": "High" if total_records >= 200 else "Medium" if total_records >= 50 else "Low",
        "reasoning": reasons,
        "summary": (
            f"Overall confidence: **{overall}%**. "
            f"Based on {total_records:,} records from {source_count} sources "
            f"with {nlp_rate}% NLP processing rate."
        ),
    }
