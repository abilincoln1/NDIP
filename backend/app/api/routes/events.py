from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.db.database import get_db
from app.models.models import Event, EventAttendance, Participant
from app.schemas.schemas import EventCreate, EventOut, AttendEventRequest
from app.core.security import get_current_user

router = APIRouter(prefix="/events", tags=["events"])


@router.post("", response_model=EventOut, status_code=201)
def create_event(
    payload: EventCreate,
    db: Session = Depends(get_db),
    _: dict = Depends(get_current_user),
):
    event = Event(**payload.model_dump())
    db.add(event)
    db.commit()
    db.refresh(event)
    return _with_count(db, event)


@router.get("", response_model=list[EventOut])
def list_events(
    country: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    query = db.query(Event)
    if country:
        query = query.filter(Event.country.ilike(f"%{country}%"))
    events = query.order_by(Event.starts_at.desc()).offset((page - 1) * page_size).limit(page_size).all()
    return [_with_count(db, e) for e in events]


@router.post("/attend", status_code=201)
def attend_event(payload: AttendEventRequest, db: Session = Depends(get_db)):
    event = db.query(Event).filter(Event.id == payload.event_id).first()
    if not event:
        raise HTTPException(404, "Event not found")

    participant = db.query(Participant).filter(
        Participant.id == payload.participant_id,
        Participant.consent_given == True
    ).first()
    if not participant:
        raise HTTPException(404, "Participant not found or consent not given")

    existing = db.query(EventAttendance).filter(
        EventAttendance.event_id == payload.event_id,
        EventAttendance.participant_id == payload.participant_id,
    ).first()
    if existing:
        raise HTTPException(409, "Already registered for this event")

    if event.capacity:
        current = db.query(func.count(EventAttendance.id)).filter(
            EventAttendance.event_id == event.id
        ).scalar()
        if current >= event.capacity:
            raise HTTPException(400, "Event is at capacity")

    attendance = EventAttendance(event_id=payload.event_id, participant_id=payload.participant_id)
    db.add(attendance)
    db.commit()
    return {"status": "registered", "event_id": payload.event_id}


def _with_count(db: Session, event: Event) -> EventOut:
    count = db.query(func.count(EventAttendance.id)).filter(
        EventAttendance.event_id == event.id
    ).scalar() or 0
    out = EventOut.model_validate(event)
    out.attendance_count = count
    return out
