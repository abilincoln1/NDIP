from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.db.database import get_db
from app.models.models import Participant
from app.schemas.schemas import ParticipantCreate, ParticipantOut
from app.core.security import get_current_user

router = APIRouter(prefix="/participants", tags=["participants"])


@router.post("", response_model=ParticipantOut, status_code=201)
def register_participant(payload: ParticipantCreate, db: Session = Depends(get_db)):
    """Opt-in registration. Email is hashed before storage — never stored plain."""
    email_hash = payload.email_hash()
    existing = db.query(Participant).filter(Participant.email_hash == email_hash).first()
    if existing:
        raise HTTPException(status_code=409, detail="Already registered with this email")

    participant = Participant(
        email_hash=email_hash,
        country=payload.country,
        city=payload.city,
        profession=payload.profession,
        skills=payload.skills,
        interests=payload.interests,
        consent_given=payload.consent_given,
    )
    db.add(participant)
    db.commit()
    db.refresh(participant)
    return participant


@router.get("", response_model=list[ParticipantOut])
def list_participants(
    country: str | None = Query(None),
    profession: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    _: dict = Depends(get_current_user),  # requires auth
):
    query = db.query(Participant).filter(Participant.consent_given == True)
    if country:
        query = query.filter(Participant.country.ilike(f"%{country}%"))
    if profession:
        query = query.filter(Participant.profession.ilike(f"%{profession}%"))

    return query.offset((page - 1) * page_size).limit(page_size).all()


@router.get("/count")
def participant_count(db: Session = Depends(get_db)):
    total = db.query(func.count(Participant.id)).filter(Participant.consent_given == True).scalar()
    return {"total": total}
