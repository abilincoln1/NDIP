from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.models.models import Engagement, EngagementType
from app.schemas.schemas import EngagementCreate, EngagementSummary
from app.analytics.engine import compute_engagement_index, compute_growth_rate, get_engagement_by_type
from app.core.security import get_current_user

router = APIRouter(prefix="/engagement", tags=["engagement"])


@router.post("", status_code=201)
def record_engagement(payload: EngagementCreate, db: Session = Depends(get_db)):
    eng = Engagement(
        participant_id=payload.participant_id,
        engagement_type=EngagementType(payload.engagement_type),
        source=payload.source,
        metadata_json=payload.metadata_json,
    )
    db.add(eng)
    db.commit()
    return {"status": "recorded", "id": eng.id}


@router.get("/summary", response_model=EngagementSummary)
def engagement_summary(
    days: int = Query(30, ge=1, le=365),
    db: Session = Depends(get_db),
    _: dict = Depends(get_current_user),
):
    from sqlalchemy import func
    total = db.query(func.count(Engagement.id)).scalar() or 0
    by_type = get_engagement_by_type(db, days)
    ei = compute_engagement_index(db, days)
    gr = compute_growth_rate(db, days)

    return EngagementSummary(
        total_engagements=total,
        by_type=by_type,
        period_days=days,
        engagement_index=ei,
        growth_rate=gr,
    )
