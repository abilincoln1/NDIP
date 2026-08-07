"""
Geography Repository (Phase D.1)
Pure data-access layer over ng_states / ng_lgas / ng_wards / ng_polling_units.
No business logic, no caching here — that belongs in the service layer.
"""
from typing import Optional
from sqlalchemy.orm import Session

from app.models.models import NgState, NgLga, NgWard, NgPollingUnit


class GeographyRepository:
    def __init__(self, db: Session):
        self.db = db

    # ─── States ─────────────────────────────────────────────────────
    def list_states(self) -> list[NgState]:
        return self.db.query(NgState).order_by(NgState.id).all()

    def get_state(self, state_id: int) -> Optional[NgState]:
        return self.db.query(NgState).filter(NgState.id == state_id).first()

    # ─── LGAs ───────────────────────────────────────────────────────
    def list_lgas_by_state(self, state_id: int) -> list[NgLga]:
        return (
            self.db.query(NgLga)
            .filter(NgLga.state_id == state_id)
            .order_by(NgLga.name)
            .all()
        )

    def get_lga(self, lga_id: int) -> Optional[NgLga]:
        return self.db.query(NgLga).filter(NgLga.id == lga_id).first()

    # ─── Wards ──────────────────────────────────────────────────────
    def list_wards_by_lga(self, lga_id: int) -> list[NgWard]:
        return (
            self.db.query(NgWard)
            .filter(NgWard.lga_id == lga_id)
            .order_by(NgWard.name)
            .all()
        )

    def get_ward(self, ward_id: int) -> Optional[NgWard]:
        return self.db.query(NgWard).filter(NgWard.id == ward_id).first()

    # ─── Polling Units ──────────────────────────────────────────────
    def list_polling_units_by_ward(self, ward_id: int) -> list[NgPollingUnit]:
        return (
            self.db.query(NgPollingUnit)
            .filter(NgPollingUnit.ward_id == ward_id)
            .order_by(NgPollingUnit.name)
            .all()
        )

    # ─── Search (partial match across states / LGAs / wards) ────────
    def search(self, q: str, limit: int = 25) -> dict:
        pattern = f"%{q}%"

        states = (
            self.db.query(NgState)
            .filter(NgState.name.ilike(pattern))
            .order_by(NgState.name)
            .limit(limit)
            .all()
        )
        lgas = (
            self.db.query(NgLga)
            .filter(NgLga.name.ilike(pattern))
            .order_by(NgLga.name)
            .limit(limit)
            .all()
        )
        wards = (
            self.db.query(NgWard)
            .filter(NgWard.name.ilike(pattern))
            .order_by(NgWard.name)
            .limit(limit)
            .all()
        )
        return {"states": states, "lgas": lgas, "wards": wards}

    # ─── Integrity / stats (used by seed-integrity tests & admin checks) ──
    def counts(self) -> dict:
        return {
            "states": self.db.query(NgState).count(),
            "lgas": self.db.query(NgLga).count(),
            "wards": self.db.query(NgWard).count(),
            "polling_units": self.db.query(NgPollingUnit).count(),
        }
