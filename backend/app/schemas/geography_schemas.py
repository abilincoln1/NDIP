"""
Geography Schemas (Phase D.1)

Matches the existing app/schemas/schemas.py convention exactly: real
pydantic BaseModel classes with `class Config: from_attributes = True` so
they validate directly from SQLAlchemy ORM rows, used as `response_model=`
on the router (see app/api/routes/geography.py), same as
participants.py / events.py etc.

(Earlier draft of this file avoided pydantic based on an outdated
assumption that it was broken in this environment — schemas.py proves
otherwise, so this version follows the real, working convention.)
"""
from typing import Optional
from pydantic import BaseModel


class StateOut(BaseModel):
    id: int
    name: str
    code: str

    class Config:
        from_attributes = True


class LgaOut(BaseModel):
    id: int
    name: str
    code: Optional[str]
    state_id: int

    class Config:
        from_attributes = True


class WardOut(BaseModel):
    id: int
    name: str
    code: Optional[str]
    lga_id: int

    class Config:
        from_attributes = True


class PollingUnitOut(BaseModel):
    id: int
    name: str
    code: Optional[str]
    ward_id: int

    class Config:
        from_attributes = True


class SearchResultOut(BaseModel):
    query: str
    states: list[StateOut]
    lgas: list[LgaOut]
    wards: list[WardOut]
