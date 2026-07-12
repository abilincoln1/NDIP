from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.core.security import get_current_user
from app.analytics.intelligence import (
    get_sentiment_trends, get_top_entities, get_narrative_trends,
    get_source_comparison, get_trend_velocity, get_emerging_topics,
    process_unprocessed_batch,
)
from app.services.normalisation import normalise_unprocessed_batch, get_normalisation_stats

router = APIRouter(prefix="/intelligence", tags=["intelligence"])


@router.get("/sentiment-trends")
def sentiment_trends(
    days: int = Query(30, ge=1, le=365),
    platform: str | None = Query(None),
    db: Session = Depends(get_db),
    _: dict = Depends(get_current_user),
):
    return {"trends": get_sentiment_trends(db, days, platform)}


@router.get("/entities")
def top_entities(
    days: int = Query(7, ge=1, le=90),
    label: str | None = Query(None),
    limit: int = Query(20, ge=5, le=50),
    db: Session = Depends(get_db),
    _: dict = Depends(get_current_user),
):
    return {"entities": get_top_entities(db, days, label, limit)}


@router.get("/narratives")
def narrative_trends(
    days: int = Query(30, ge=1, le=365),
    db: Session = Depends(get_db),
    _: dict = Depends(get_current_user),
):
    return {"narratives": get_narrative_trends(db, days)}


@router.get("/source-comparison")
def source_comparison(
    days: int = Query(30, ge=1, le=365),
    db: Session = Depends(get_db),
    _: dict = Depends(get_current_user),
):
    return {"sources": get_source_comparison(db, days)}


@router.get("/trend-velocity")
def trend_velocity(
    days: int = Query(14, ge=7, le=90),
    db: Session = Depends(get_db),
    _: dict = Depends(get_current_user),
):
    return {"velocity": get_trend_velocity(db, days)}


@router.get("/emerging-topics")
def emerging_topics(
    days: int = Query(7, ge=3, le=30),
    db: Session = Depends(get_db),
    _: dict = Depends(get_current_user),
):
    return {"topics": get_emerging_topics(db, days)}


@router.get("/normalisation-stats")
def normalisation_stats(
    db: Session = Depends(get_db),
    _: dict = Depends(get_current_user),
):
    return get_normalisation_stats(db)


@router.post("/process")
def trigger_processing(
    limit: int = Query(200, ge=10, le=1000),
    db: Session = Depends(get_db),
    _: dict = Depends(get_current_user),
):
    normalised = normalise_unprocessed_batch(db, limit)
    processed = process_unprocessed_batch(db, limit)
    return {"normalised": normalised, "nlp_processed": processed}


@router.post("/reprocess")
def reprocess_all_data(
    db: Session = Depends(get_db),
    _: dict = Depends(get_current_user),
):
    """Reprocess all existing data with the upgraded NLP pipeline."""
    from app.analytics.intelligence import reprocess_all
    result = reprocess_all(db)
    return {"status": "complete", **result}


@router.get("/quality-stats")
def quality_stats(
    db: Session = Depends(get_db),
    _: dict = Depends(get_current_user),
):
    from app.analytics.intelligence import get_intelligence_quality_stats
    return get_intelligence_quality_stats(db)
