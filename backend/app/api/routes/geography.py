"""
Geography Router (Phase D.1)

GET /api/v2/geography/states
GET /api/v2/geography/lgas/{state_id}
GET /api/v2/geography/wards/{lga_id}
GET /api/v2/geography/search?q=

Matches the existing route convention (see participants.py): declare
response_model and return bare ORM objects/dicts, let pydantic handle
serialization.

NOTE on auth: this is public reference data (states/LGAs/wards used to
populate dropdowns, e.g. during onboarding before a user is authenticated),
so these routes are intentionally NOT behind get_current_user, unlike
watchlist.py / participants.py's list endpoint. If this platform requires
every endpoint authenticated, add `_: dict = Depends(get_current_user)`
to each route below.
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.schemas.geography_schemas import StateOut, LgaOut, WardOut, SearchResultOut
from app.services.geography_service import GeographyService

router = APIRouter(prefix="/api/v2/geography", tags=["geography"])


@router.get("/states", response_model=list[StateOut])
def list_states(db: Session = Depends(get_db)):
    return GeographyService(db).get_states()


@router.get("/lgas/{state_id}", response_model=list[LgaOut])
def list_lgas(state_id: int, db: Session = Depends(get_db)):
    result = GeographyService(db).get_lgas_by_state(state_id)
    if result is None:
        raise HTTPException(status_code=404, detail=f"State {state_id} not found")
    return result


@router.get("/wards/{lga_id}", response_model=list[WardOut])
def list_wards(lga_id: int, db: Session = Depends(get_db)):
    result = GeographyService(db).get_wards_by_lga(lga_id)
    if result is None:
        raise HTTPException(status_code=404, detail=f"LGA {lga_id} not found")
    return result


@router.get("/search", response_model=SearchResultOut)
def search_geography(
    q: str = Query(..., min_length=1, description="Partial match across state, LGA, and ward names"),
    limit: int = Query(25, ge=1, le=100),
    db: Session = Depends(get_db),
):
    return GeographyService(db).search(q, limit=limit)
