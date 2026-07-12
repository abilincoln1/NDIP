from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime, timedelta, timezone

from app.db.database import get_db
from app.core.security import get_current_user
from app.connectors.registry import get_connector_status, get_recent_health
from app.models.models import ConnectorHealthLog, IngestionJob, SocialPost, NormalisedPost
from app.services.normalisation import get_normalisation_stats

router = APIRouter(prefix="/data-health", tags=["data-health"])


@router.get("/overview")
def health_overview(
    db: Session = Depends(get_db),
    _: dict = Depends(get_current_user),
):
    connector_status = get_connector_status()
    configured = sum(1 for c in connector_status if c["configured"])
    total = len(connector_status)

    norm_stats = get_normalisation_stats(db)

    # Latest ingest job
    latest_job = db.query(IngestionJob).order_by(
        IngestionJob.started_at.desc()
    ).first()

    # Data freshness
    latest_post = db.query(func.max(SocialPost.fetched_at)).scalar()

    return {
        "connectors_configured": configured,
        "connectors_total": total,
        "connector_health_pct": round(configured / max(total, 1) * 100, 1),
        "normalisation": norm_stats,
        "latest_ingest": latest_job.started_at.isoformat() if latest_job else None,
        "latest_post_fetched": latest_post.isoformat() if latest_post else None,
        "data_fresh": (
            (datetime.now(timezone.utc) - latest_post).total_seconds() < 86400
            if latest_post else False
        ),
    }


@router.get("/connectors")
def connector_health(
    hours: int = Query(24, ge=1, le=168),
    db: Session = Depends(get_db),
    _: dict = Depends(get_current_user),
):
    configured = get_connector_status()
    health = get_recent_health(db, hours)
    health_map = {h["platform"]: h for h in health}

    result = []
    for c in configured:
        h = health_map.get(c["platform"], {})
        result.append({
            "platform": c["platform"],
            "configured": c["configured"],
            "type": c.get("type", "api"),
            "last_status": h.get("last_status", "never_run"),
            "last_checked": h.get("last_checked"),
            "total_fetched_24h": h.get("total_fetched", 0),
            "total_new_24h": h.get("total_new", 0),
            "error_count": h.get("errors", 0),
        })
    return {"connectors": result}


@router.get("/ingestion-volume")
def ingestion_volume(
    days: int = Query(30, ge=1, le=90),
    db: Session = Depends(get_db),
    _: dict = Depends(get_current_user),
):
    since = datetime.now(timezone.utc) - timedelta(days=days)
    rows = db.query(
        func.date_trunc('day', SocialPost.fetched_at).label("day"),
        func.count(SocialPost.id).label("count"),
    ).filter(
        SocialPost.fetched_at >= since
    ).group_by("day").order_by("day").all()

    return {
        "volume": [{"date": str(r.day)[:10], "count": r.count} for r in rows]
    }


@router.get("/jobs")
def recent_jobs(
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    _: dict = Depends(get_current_user),
):
    jobs = db.query(IngestionJob).order_by(
        IngestionJob.started_at.desc()
    ).limit(limit).all()

    return {"jobs": [{
        "id": j.id,
        "query": j.query,
        "platforms": j.platforms,
        "status": j.status,
        "total_fetched": j.total_fetched,
        "total_new": j.total_new,
        "total_normalised": j.total_normalised,
        "started_at": j.started_at.isoformat(),
        "completed_at": j.completed_at.isoformat() if j.completed_at else None,
    } for j in jobs]}


@router.get("/errors")
def recent_errors(
    hours: int = Query(24, ge=1, le=168),
    db: Session = Depends(get_db),
    _: dict = Depends(get_current_user),
):
    since = datetime.now(timezone.utc) - timedelta(hours=hours)
    errors = db.query(ConnectorHealthLog).filter(
        ConnectorHealthLog.status == "error",
        ConnectorHealthLog.checked_at >= since,
    ).order_by(ConnectorHealthLog.checked_at.desc()).limit(50).all()

    return {"errors": [{
        "platform": e.platform,
        "error": e.error_message,
        "checked_at": e.checked_at.isoformat(),
    } for e in errors]}
