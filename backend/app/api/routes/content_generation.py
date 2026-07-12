"""
NDIP Content Generation API

Newsletters and social content prompts, generated from data NDIP already
computes (Leadership Pack, National Pulse, GNEI). No new data sources.

WhatsApp: there is no automatic send. See content_generation.py module
docstring for why -- WhatsApp has no open API for posting into arbitrary
groups. These endpoints return WhatsApp-ready plain text for manual
pasting, or for use with a real WhatsApp Business API integration if RTIFN
sets one up.
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.core.security import get_current_user

router = APIRouter(prefix="/content", tags=["content-generation"])


@router.get("/newsletter/executive")
def get_executive_newsletter(
    days: int = Query(7, ge=1, le=30),
    db: Session = Depends(get_db),
    _: dict = Depends(get_current_user),
):
    from app.api.routes.leadership_pack import leadership_pack
    from app.services.content_generation import generate_executive_newsletter

    lp_data = leadership_pack(days=days, db=db, _=_)
    return generate_executive_newsletter(lp_data)


@router.get("/newsletter/pulse")
def get_pulse_newsletter(
    days: int = Query(7, ge=1, le=30),
    db: Session = Depends(get_db),
    _: dict = Depends(get_current_user),
):
    from app.api.routes.national_pulse import national_pulse
    from app.services.content_generation import generate_pulse_newsletter

    np_data = national_pulse(days=days, db=db, _=_)
    return generate_pulse_newsletter(np_data)


@router.get("/instagram/video-prompts")
def get_instagram_video_prompts(
    days: int = Query(7, ge=1, le=30),
    limit: int = Query(3, ge=1, le=6),
    db: Session = Depends(get_db),
    _: dict = Depends(get_current_user),
):
    from app.api.routes.national_pulse import national_pulse
    from app.services.gnei import generate_gnei_intelligence
    from app.services.content_generation import generate_instagram_video_prompts

    np_data = national_pulse(days=days, db=db, _=_)
    try:
        gnei_data = generate_gnei_intelligence(db, days)
    except Exception:
        gnei_data = None

    prompts = generate_instagram_video_prompts(np_data, gnei_data, limit=limit)
    return {"period_days": days, "prompts": prompts}
