from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.analytics.engine import (
    compute_all_metrics, get_metric_trend,
    get_engagement_by_type, get_geography, save_snapshot
)
from app.core.security import get_current_user

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/overview")
def analytics_overview(
    days: int = Query(30, ge=1, le=365),
    db: Session = Depends(get_db),
    _: dict = Depends(get_current_user),
):
    metrics = compute_all_metrics(db, days)
    return metrics


@router.get("/engagement")
def analytics_engagement(
    days: int = Query(30, ge=1, le=365),
    db: Session = Depends(get_db),
    _: dict = Depends(get_current_user),
):
    by_type = get_engagement_by_type(db, days)
    trend = get_metric_trend(db, "engagement_index", days)
    return {"by_type": by_type, "trend": trend}


@router.get("/geography")
def analytics_geography(
    db: Session = Depends(get_db),
    _: dict = Depends(get_current_user),
):
    return {"countries": get_geography(db)}


@router.get("/trend/{metric}")
def metric_trend(
    metric: str,
    days: int = Query(90, ge=7, le=365),
    db: Session = Depends(get_db),
    _: dict = Depends(get_current_user),
):
    allowed = {
        "engagement_index", "participation_index",
        "growth_rate", "sentiment_score", "topic_momentum_score"
    }
    if metric not in allowed:
        from fastapi import HTTPException
        raise HTTPException(400, f"Invalid metric. Choose from: {', '.join(allowed)}")
    return {"metric": metric, "trend": get_metric_trend(db, metric, days)}


@router.post("/snapshot")
def create_snapshot(
    db: Session = Depends(get_db),
    _: dict = Depends(get_current_user),
):
    metrics = compute_all_metrics(db)
    snap = save_snapshot(db, {k: v for k, v in metrics.items() if k != "snapshot_date"})
    return {"status": "saved", "snapshot_id": snap.id}
