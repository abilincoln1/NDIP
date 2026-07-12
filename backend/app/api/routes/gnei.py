from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.core.security import get_current_user
from app.services.cache import get_cached, set_cached, cache_key, TTL_NATIONAL_PULSE

router = APIRouter(prefix="/gnei", tags=["gnei"])


@router.get("/")
def get_gnei(
    days: int = Query(7, ge=1, le=30),
    db: Session = Depends(get_db),
    _: dict = Depends(get_current_user),
):
    ck = cache_key("gnei", f"days={days}")
    cached = get_cached(ck)
    if cached:
        return cached
    from app.services.gnei import generate_gnei_intelligence
    result = generate_gnei_intelligence(db, days)
    set_cached(ck, result, TTL_NATIONAL_PULSE)
    return result
