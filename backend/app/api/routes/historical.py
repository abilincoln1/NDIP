from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime, timedelta, timezone
from app.db.database import get_db
from app.core.security import get_current_user
from app.services.cache import get_cached, set_cached, cache_key, TTL_HISTORICAL
from app.analytics.intelligence import get_sentiment_trends, get_narrative_trends
from app.analytics.strategic_narratives import get_narrative_analysis
from app.analytics.engine import compute_all_metrics
from app.models.models import NormalisedPost, AnalyticsSnapshot

router = APIRouter(prefix="/historical", tags=["historical"])


def _detect_trend_type(values: list[float]) -> str:
    if len(values) < 3:
        return "insufficient data"
    first_half = values[:len(values)//2]
    second_half = values[len(values)//2:]
    avg_first = sum(first_half) / len(first_half)
    avg_second = sum(second_half) / len(second_half)
    change = (avg_second - avg_first) / max(abs(avg_first), 0.001)
    if change > 0.2:
        return "sustained growth"
    elif change > 0.05:
        return "trend acceleration"
    elif change < -0.2:
        return "sustained decline"
    elif change < -0.05:
        return "trend deceleration"
    return "stable"


@router.get("/overview")
def historical_overview(
    db: Session = Depends(get_db),
    _: dict = Depends(get_current_user),
):
    ck = cache_key("historical-overview")
    cached = get_cached(ck)
    if cached:
        return cached
    periods = [
        {"days": 7, "label": "7 days"},
        {"days": 30, "label": "30 days"},
        {"days": 90, "label": "90 days"},
    ]
    results = []
    for period in periods:
        metrics = compute_all_metrics(db, period["days"])
        narratives = get_narrative_analysis(db, period["days"])
        sentiment = get_sentiment_trends(db, period["days"])

        sentiment_scores = [t["avg_score"] for t in sentiment]
        sentiment_trend = _detect_trend_type(sentiment_scores)

        dominant = narratives[0]["narrative"] if narratives else "None"
        rising = sorted(narratives, key=lambda x: x.get("momentum", 0), reverse=True)
        fastest_rising = rising[0]["narrative"] if rising else "None"

        results.append({
            "period": period["label"],
            "days": period["days"],
            "engagement_index": metrics["engagement_index"],
            "sentiment_score": metrics["sentiment_score"],
            "total_posts": db.query(func.count(NormalisedPost.id)).filter(
                NormalisedPost.published_at >= datetime.now(timezone.utc) - timedelta(days=period["days"]),
                NormalisedPost.nlp_processed == True,
            ).scalar() or 0,
            "dominant_narrative": dominant,
            "fastest_rising": fastest_rising,
            "sentiment_trend": sentiment_trend,
            "narrative_count": len(narratives),
        })

    result = {"periods": results}
    set_cached(ck, result, TTL_HISTORICAL)
    return result


@router.get("/sentiment")
def historical_sentiment(
    days: int = Query(30, ge=7, le=180),
    db: Session = Depends(get_db),
    _: dict = Depends(get_current_user),
):
    ck = cache_key("historical-sentiment", f"days={days}")
    cached = get_cached(ck)
    if cached:
        return cached
    trends = get_sentiment_trends(db, days)
    scores = [t["avg_score"] for t in trends]
    trend_type = _detect_trend_type(scores)

    # Detect shifts - periods where sentiment changed significantly
    shifts = []
    for i in range(1, len(trends)):
        delta = trends[i]["avg_score"] - trends[i-1]["avg_score"]
        if abs(delta) > 0.15:
            shifts.append({
                "date": trends[i]["date"],
                "direction": "positive shift" if delta > 0 else "negative shift",
                "magnitude": round(abs(delta), 3),
            })

    result = {
        "trend_type": trend_type,
        "data": trends,
        "shifts": shifts,
        "summary": f"Over {days} days, sentiment shows a {trend_type} pattern. "
                   f"{len(shifts)} significant shift(s) detected.",
    }
    set_cached(ck, result, TTL_HISTORICAL)
    return result


@router.get("/narratives")
def historical_narratives(
    days: int = Query(30, ge=7, le=180),
    db: Session = Depends(get_db),
    _: dict = Depends(get_current_user),
):
    current = get_narrative_analysis(db, days)
    previous = get_narrative_analysis(db, days * 2)

    prev_map = {n["narrative"]: n for n in previous}
    shifts = []
    for nar in current:
        prev = prev_map.get(nar["narrative"])
        if prev:
            sov_change = nar["share_of_voice"] - prev["share_of_voice"]
            if abs(sov_change) > 3:
                shifts.append({
                    "narrative": nar["narrative"],
                    "current_sov": nar["share_of_voice"],
                    "previous_sov": prev["share_of_voice"],
                    "change": round(sov_change, 1),
                    "direction": "increasing" if sov_change > 0 else "decreasing",
                    "plain_english": (
                        f"**{nar['narrative']}** share of voice {'increased' if sov_change > 0 else 'decreased'} "
                        f"by {abs(sov_change):.0f}% compared to the previous period."
                    ),
                })

    return {
        "current_narratives": current,
        "narrative_shifts": sorted(shifts, key=lambda x: abs(x["change"]), reverse=True),
        "days": days,
    }


@router.get("/participation")
def historical_participation(
    db: Session = Depends(get_db),
    _: dict = Depends(get_current_user),
):
    snapshots = db.query(AnalyticsSnapshot).order_by(
        AnalyticsSnapshot.snapshot_date.asc()
    ).limit(90).all()

    data = [{
        "date": s.snapshot_date.strftime("%Y-%m-%d") if s.snapshot_date else "",
        "engagement_index": round(float(s.engagement_index or 0), 2),
        "total_participants": s.total_participants or 0,
        "total_engagements": s.total_engagements or 0,
        "sentiment_score": round(float(s.sentiment_score or 0), 3),
    } for s in snapshots]

    engagement_values = [d["engagement_index"] for d in data]
    trend = _detect_trend_type(engagement_values)

    result = {
        "data": data,
        "trend_type": trend,
        "data_points": len(data),
        "summary": f"Engagement shows a {trend} pattern across {len(data)} recorded snapshots.",
    }
    set_cached(cache_key("historical-participation"), result, TTL_HISTORICAL)
    return result
