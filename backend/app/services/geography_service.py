"""
Geography Service (Phase D.1)

Business logic + caching layer on top of GeographyRepository. Uses the
project's existing Redis cache mechanism (app.services.cache) — same
get_cached/set_cached/cache_key functions every other route uses.

States and LGAs are cached (they change essentially never once seeded)
as plain dicts (via StateOut/LgaOut .model_dump()) since the cache layer
JSON-serializes everything. Wards and search are returned as raw ORM
objects — not cached, and left for the router's response_model
(WardOut / SearchResultOut, both from_attributes=True) to serialize,
exactly like participants.py / events.py do.
"""
from sqlalchemy.orm import Session

from app.repositories.geography_repository import GeographyRepository
from app.schemas.geography_schemas import StateOut, LgaOut
from app.services.cache import get_cached, set_cached, cache_key

# Reference data changes essentially never — cache generously.
TTL_GEOGRAPHY_STATES = 21600  # 6 hours
TTL_GEOGRAPHY_LGAS = 21600    # 6 hours


class GeographyService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = GeographyRepository(db)

    def get_states(self) -> list[dict]:
        ck = cache_key("geography", "states")
        cached = get_cached(ck)
        if cached is not None:
            return cached
        rows = self.repo.list_states()
        result = [StateOut.model_validate(r).model_dump() for r in rows]
        set_cached(ck, result, TTL_GEOGRAPHY_STATES)
        return result

    def get_lgas_by_state(self, state_id: int) -> list[dict] | None:
        state = self.repo.get_state(state_id)
        if state is None:
            return None
        ck = cache_key("geography", "lgas", state_id)
        cached = get_cached(ck)
        if cached is not None:
            return cached
        rows = self.repo.list_lgas_by_state(state_id)
        result = [LgaOut.model_validate(r).model_dump() for r in rows]
        set_cached(ck, result, TTL_GEOGRAPHY_LGAS)
        return result

    def get_wards_by_lga(self, lga_id: int):
        """Returns None if lga_id doesn't exist, else a (possibly empty) list
        of NgWard ORM rows for the router's response_model to serialize."""
        lga = self.repo.get_lga(lga_id)
        if lga is None:
            return None
        return self.repo.list_wards_by_lga(lga_id)

    def search(self, q: str, limit: int = 25) -> dict:
        q = (q or "").strip()
        if len(q) < 2:
            return {"query": q, "states": [], "lgas": [], "wards": []}
        raw = self.repo.search(q, limit=limit)
        return {"query": q, "states": raw["states"], "lgas": raw["lgas"], "wards": raw["wards"]}

    def get_seed_stats(self) -> dict:
        """Used by the seed-integrity check / admin endpoints."""
        return self.repo.counts()
