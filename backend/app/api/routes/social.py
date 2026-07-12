from fastapi import APIRouter, Depends, Query, BackgroundTasks
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.connectors.registry import run_ingest, get_connector_status
from app.analytics.engine import get_sentiment_distribution
from app.analytics.nlp import get_top_topics
from app.models.models import SocialPost, SocialMetric
from app.core.security import get_current_user
from sqlalchemy import func

router = APIRouter(prefix="/social", tags=["social"])


@router.get("/overview")
def social_overview(
    db: Session = Depends(get_db),
    _: dict = Depends(get_current_user),
):
    platform_counts = dict(
        db.query(SocialPost.platform, func.count(SocialPost.id))
        .group_by(SocialPost.platform).all()
    )
    total = sum(platform_counts.values())
    connectors = get_connector_status()

    return {
        "platform_counts": {str(k): v for k, v in platform_counts.items()},
        "total_posts_analysed": total,
        "connector_status": connectors,
    }


@router.get("/sentiment")
def social_sentiment(
    days: int = Query(30, ge=1, le=365),
    db: Session = Depends(get_db),
    _: dict = Depends(get_current_user),
):
    return get_sentiment_distribution(db, days)


@router.get("/topics")
def social_topics(
    days: int = Query(7, ge=1, le=90),
    limit: int = Query(20, ge=5, le=50),
    db: Session = Depends(get_db),
    _: dict = Depends(get_current_user),
):
    return {"topics": get_top_topics(db, days, limit)}


@router.post("/ingest")
async def trigger_ingest(
    query: str = Query(..., min_length=2),
    platforms: str | None = Query(None, description="Comma-separated platform names"),
    background_tasks: BackgroundTasks = BackgroundTasks(),
    db: Session = Depends(get_db),
    _: dict = Depends(get_current_user),
):
    platform_list = [p.strip() for p in platforms.split(",")] if platforms else None
    result = await run_ingest(db, query, platform_list)
    return {"status": "completed", "summary": result}
