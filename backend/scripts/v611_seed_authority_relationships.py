"""
NDIP V6.1.1 Phase C -- Authority Graph Seed

Connects the Phase A office-holder rows to their institutions using the
spec's authority-relationship vocabulary (HOLDS_OFFICE, LEADS, OVERSEES,
APPOINTS, REGULATES, IMPLEMENTS), building the actual graph the spec
calls for -- not just defining the relationship types, but using them.

This is data, not business logic: looked up by stakeholder NAME (must
match Phase A's seeded names and the existing V6.0 institutional names
exactly), so it is safe to extend later via the registry admin UI
without a code change.

Run: docker exec agora-backend-1 python scripts/v611_seed_authority_relationships.py
"""
import sys
sys.path.insert(0, '/app')

from app.db.database import SessionLocal
from app.models.models import StakeholderRegistry, StakeholderRelationship, RelationshipType


# (from_name, relationship_type, to_name, description)
AUTHORITY_SEED = [
    # Office-holder HOLDS_OFFICE / LEADS their institution
    ("Minister of Power", RelationshipType.OVERSEES, "Federal Ministry of Power",
     "Minister of Power holds ministerial authority over the Federal Ministry of Power."),
    ("Minister of Environment", RelationshipType.OVERSEES, "Federal Ministry of Environment",
     "Minister of Environment holds ministerial authority over the Federal Ministry of Environment."),
    ("Minister of Power", RelationshipType.OVERSEES, "Rural Electrification Agency",
     "REA reports to the Minister of Power within the federal power sector portfolio."),
    ("Managing Director, Rural Electrification Agency", RelationshipType.LEADS, "Rural Electrification Agency",
     "The Managing Director leads REA's day-to-day institutional operations."),
    ("Chairman, Nigerian Electricity Regulatory Commission", RelationshipType.LEADS, "Nigerian Electricity Regulatory Commission",
     "The Chairman leads NERC's day-to-day institutional operations."),
    ("Managing Director, Transmission Company of Nigeria", RelationshipType.LEADS, "Transmission Company of Nigeria",
     "The Managing Director leads TCN's day-to-day institutional operations."),
    ("Director-General, National Council on Climate Change", RelationshipType.LEADS, "National Council on Climate Change",
     "The Director-General leads NCCC's day-to-day institutional operations."),
    ("Director-General, National Environmental Standards and Regulations Enforcement Agency", RelationshipType.LEADS,
     "National Environmental Standards and Regulations Enforcement Agency",
     "The Director-General leads NESREA's day-to-day institutional operations."),
    ("Director-General, Infrastructure Concession Regulatory Commission", RelationshipType.LEADS, "Infrastructure Concession Regulatory Commission",
     "The Director-General leads ICRC's day-to-day institutional operations."),
    ("Director-General, Bureau of Public Procurement", RelationshipType.LEADS, "Bureau of Public Procurement",
     "The Director-General leads BPP's day-to-day institutional operations."),
    ("Managing Director, Nigeria Sovereign Investment Authority", RelationshipType.LEADS, "Nigerian Sovereign Investment Authority",
     "The Managing Director leads NSIA's day-to-day institutional operations."),

    # Regulatory authority
    ("Nigerian Electricity Regulatory Commission", RelationshipType.REGULATES, "Rural Electrification Agency",
     "NERC regulates the electricity market within which REA's programmes operate."),
    ("National Environmental Standards and Regulations Enforcement Agency", RelationshipType.REGULATES, "Federal Ministry of Environment",
     "NESREA enforces environmental standards within the Ministry of Environment's policy domain."),

    # Implementation authority
    ("Rural Electrification Agency", RelationshipType.IMPLEMENTS, "Federal Ministry of Power",
     "REA implements rural electrification programmes on behalf of the Federal Ministry of Power."),

    # Appointment authority (President appoints ministers; Governor appoints commissioners)
    ("Office of the President", RelationshipType.APPOINTS, "Minister of Power",
     "The President appoints the Minister of Power."),
    ("Office of the President", RelationshipType.APPOINTS, "Minister of Environment",
     "The President appoints the Minister of Environment."),
    ("Governor (State-Level)", RelationshipType.APPOINTS, "State Commissioner for Energy",
     "The State Governor appoints the State Commissioner for Energy (generic role, applies across states)."),
    ("Governor (State-Level)", RelationshipType.APPOINTS, "State Commissioner for Environment",
     "The State Governor appoints the State Commissioner for Environment (generic role, applies across states)."),

    # Legislative oversight
    ("Senate Committee Chair on Power", RelationshipType.OVERSEES, "Federal Ministry of Power",
     "The Senate Power Committee provides legislative oversight of the power sector."),
    ("Senate Committee Chair on Environment and Climate Change", RelationshipType.OVERSEES, "Federal Ministry of Environment",
     "The Senate Environment and Climate Change Committee provides legislative oversight."),

    # Development finance leadership -> institution
    ("World Bank Nigeria Country Director", RelationshipType.LEADS, "World Bank",
     "The Country Director leads the World Bank's Nigeria country programme."),
    ("African Development Bank Nigeria Country Director", RelationshipType.LEADS, "African Development Bank",
     "The Country Director leads AfDB's Nigeria country programme."),
]


def seed_relationships(db):
    lookup = {s.name: s.id for s in db.query(StakeholderRegistry).all()}
    created = 0
    skipped = 0
    missing_names = set()

    for from_name, rel_type, to_name, description in AUTHORITY_SEED:
        from_id = lookup.get(from_name)
        to_id = lookup.get(to_name)
        if from_id is None:
            missing_names.add(from_name)
            continue
        if to_id is None:
            missing_names.add(to_name)
            continue

        existing = db.query(StakeholderRelationship).filter(
            StakeholderRelationship.from_stakeholder_id == from_id,
            StakeholderRelationship.to_stakeholder_id == to_id,
            StakeholderRelationship.relationship_type == rel_type,
        ).first()
        if existing:
            skipped += 1
            continue

        db.add(StakeholderRelationship(
            from_stakeholder_id=from_id, to_stakeholder_id=to_id,
            relationship_type=rel_type, description=description,
        ))
        created += 1

    db.commit()
    return created, skipped, missing_names


def main():
    print("=" * 70)
    print("  NDIP V6.1.1 Phase C -- Authority Graph Seed")
    print("=" * 70)
    db = SessionLocal()
    try:
        created, skipped, missing = seed_relationships(db)
        print(f"\n  Authority relationships: {created} created, {skipped} already existed (skipped)")
        if missing:
            print(f"\n  WARNING -- {len(missing)} stakeholder name(s) referenced in the seed were not found in the registry:")
            for name in sorted(missing):
                print(f"    - {name}")
            print("  These relationships were skipped. This is most likely a name mismatch")
            print("  between this seed and the actual Phase A seed or pre-existing institutional names --")
            print("  worth checking directly rather than assuming, since it affects real graph coverage.")

        from app.models.models import StakeholderRelationship
        total = db.query(StakeholderRelationship).filter(StakeholderRelationship.is_active == True).count()
        print(f"\n  Total active StakeholderRelationship rows (all relationship types combined): {total}")

        from sqlalchemy import func
        by_type = db.query(StakeholderRelationship.relationship_type, func.count(StakeholderRelationship.id)).filter(
            StakeholderRelationship.is_active == True
        ).group_by(StakeholderRelationship.relationship_type).all()
        print("\n  Relationship count by type:")
        for t, count in by_type:
            print(f"    {t:20s} {count}")
    finally:
        db.close()
    print("\n" + "=" * 70)
    print("  Seed complete")
    print("=" * 70)


if __name__ == "__main__":
    main()
