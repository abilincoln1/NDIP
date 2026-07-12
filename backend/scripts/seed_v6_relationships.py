"""
NDIP V6.1 Phase B -- Stakeholder Relationship Seed Script

Populates StakeholderRelationship with a baseline of known, real
institutional relationships (REPORTS_TO, OWNS_PROGRAMME, FUNDS, REGULATES,
PARTNERS_WITH). Same principle as V6.0's registry seed: this is DATA, not
business logic -- running again is safe (skips existing pairs), and new
relationships can be added later via the registry-management routes/UI
(Phase K) with no code change.

Relationships are looked up by exact stakeholder name against the
StakeholderRegistry rows already seeded in scripts/seed_v6_registries.py --
this script must be run AFTER that one.

Run: docker exec agora-backend-1 python scripts/seed_v6_relationships.py
"""
import sys
sys.path.insert(0, '/app')

from app.db.database import SessionLocal
from app.models.models import StakeholderRegistry, StakeholderRelationship, RelationshipType


# (from_name, to_name, relationship_type, description, relevant_category)
RELATIONSHIP_SEED = [
    # Energy sector hierarchy
    ("Rural Electrification Agency", "Federal Ministry of Power", RelationshipType.REPORTS_TO,
     "REA operates under the supervisory authority of the Federal Ministry of Power.", "ENERGY"),
    ("Nigerian Electricity Regulatory Commission", "Federal Ministry of Power", RelationshipType.REPORTS_TO,
     "NERC is the independent regulator for the power sector, established under the Ministry's policy framework.", "ENERGY"),
    ("Transmission Company of Nigeria", "Federal Ministry of Power", RelationshipType.REPORTS_TO,
     "TCN operates under the Federal Ministry of Power.", "ENERGY"),
    ("Nigerian Electricity Regulatory Commission", "Rural Electrification Agency", RelationshipType.REGULATES,
     "NERC regulates electricity tariffs and licensing relevant to REA-led mini-grid and rural electrification programmes.", "RURAL_ELECTRIFICATION"),
    ("Rural Electrification Agency", "Federal Ministry of Environment", RelationshipType.PARTNERS_WITH,
     "REA's renewable mini-grid and rural electrification programmes intersect with national climate and environmental policy.", "RENEWABLE_ENERGY"),

    # Climate & environment
    ("National Council on Climate Change", "Federal Ministry of Environment", RelationshipType.PARTNERS_WITH,
     "NCCC coordinates national climate policy in partnership with the Ministry of Environment's regulatory mandate.", "CLIMATE_FINANCE"),
    ("National Environmental Standards and Regulations Enforcement Agency", "Federal Ministry of Environment", RelationshipType.REPORTS_TO,
     "NESREA operates under the Federal Ministry of Environment.", "WASTE_MANAGEMENT"),
    ("Ecological Fund Office", "Federal Ministry of Environment", RelationshipType.FUNDS,
     "The Ecological Fund Office provides funding for ecological and environmental remediation programmes.", "CLIMATE_FINANCE"),
    ("Green Bond Programme", "Federal Ministry of Finance", RelationshipType.FUNDS,
     "Nigeria's sovereign green bond programme is administered under the Federal Ministry of Finance.", "GREEN_INVESTMENT"),

    # Infrastructure & PPP
    ("Infrastructure Concession Regulatory Commission", "Federal Ministry of Finance", RelationshipType.REPORTS_TO,
     "ICRC regulates public-private partnership concessions under the Ministry of Finance's fiscal oversight.", "PPP"),
    ("Infrastructure Corporation of Nigeria", "Nigerian Sovereign Investment Authority", RelationshipType.PARTNERS_WITH,
     "InfraCorp and NSIA both operate as infrastructure-financing vehicles with overlapping mandates.", "INFRASTRUCTURE"),
    ("Bureau of Public Enterprises", "Federal Ministry of Finance", RelationshipType.REPORTS_TO,
     "BPE operates under the Ministry of Finance's privatisation and public enterprise oversight mandate.", "PPP"),
    ("Bureau of Public Procurement", "Office of the President", RelationshipType.REPORTS_TO,
     "BPP's regulatory mandate over federal procurement is anchored at the Presidency.", "PPP"),

    # Energy ministry oversight of upstream/midstream
    ("Nigerian National Petroleum Company Limited", "Federal Ministry of Power", RelationshipType.PARTNERS_WITH,
     "NNPC's gas-to-power initiatives intersect with the Ministry of Power's electricity generation mandate.", "ENERGY"),
    ("Energy Commission of Nigeria", "Federal Ministry of Power", RelationshipType.PARTNERS_WITH,
     "ECN coordinates national energy policy planning alongside the Ministry of Power.", "ENERGY_ACCESS"),

    # Development finance funding relationships
    ("World Bank", "Rural Electrification Agency", RelationshipType.FUNDS,
     "The World Bank has historically been a significant funder of Nigerian rural electrification and mini-grid programmes.", "RURAL_ELECTRIFICATION"),
    ("African Development Bank", "Federal Ministry of Power", RelationshipType.FUNDS,
     "AfDB funds multiple Nigerian energy access and power sector reform programmes.", "ENERGY_ACCESS"),
    ("International Finance Corporation", "Rural Electrification Agency", RelationshipType.FUNDS,
     "IFC provides private-sector financing instruments supporting REA-led programmes.", "RENEWABLE_ENERGY"),
    ("Africa Finance Corporation", "Infrastructure Corporation of Nigeria", RelationshipType.PARTNERS_WITH,
     "AFC and InfraCorp co-finance large-scale Nigerian infrastructure projects.", "INFRASTRUCTURE"),
    ("Africa50", "Infrastructure Concession Regulatory Commission", RelationshipType.PARTNERS_WITH,
     "Africa50 partners on PPP-structured infrastructure concessions regulated by ICRC.", "PPP"),

    # Diaspora
    ("Nigerians in Diaspora Commission", "Office of the Vice President", RelationshipType.REPORTS_TO,
     "NiDCOM operates under the supervision of the Office of the Vice President.", "DIASPORA_INVESTMENT"),
    ("RTIFN", "Nigerians in Diaspora Commission", RelationshipType.PARTNERS_WITH,
     "RTIFN engages with NiDCOM as the Nigerian government's formal diaspora engagement body.", "DIASPORA_INVESTMENT"),

    # State-level generic hierarchy
    ("Deputy Governor (State-Level)", "Governor (State-Level)", RelationshipType.REPORTS_TO,
     "Generic state-government reporting line.", None),
    ("State Ministry of Energy (Generic)", "Governor (State-Level)", RelationshipType.REPORTS_TO,
     "Generic state-government reporting line.", "ENERGY"),
    ("State PPP Office (Generic)", "Infrastructure Concession Regulatory Commission", RelationshipType.PARTNERS_WITH,
     "State PPP offices typically coordinate with the federal ICRC framework on concession structuring.", "PPP"),
]


def seed_relationships(db):
    created = 0
    skipped = 0
    missing_stakeholders = set()

    name_to_id = {s.name: s.id for s in db.query(StakeholderRegistry).all()}

    for from_name, to_name, rel_type, description, category in RELATIONSHIP_SEED:
        from_id = name_to_id.get(from_name)
        to_id = name_to_id.get(to_name)
        if from_id is None:
            missing_stakeholders.add(from_name)
            continue
        if to_id is None:
            missing_stakeholders.add(to_name)
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
            relevant_category=category,
        ))
        created += 1

    db.commit()
    return created, skipped, missing_stakeholders


def main():
    print("=" * 60)
    print("  NDIP V6.1 -- Stakeholder Relationship Seed")
    print("=" * 60)
    db = SessionLocal()
    try:
        created, skipped, missing = seed_relationships(db)
        print(f"\n  Relationships: {created} created, {skipped} already existed (skipped)")
        if missing:
            print(f"\n  WARNING: {len(missing)} stakeholder name(s) referenced in the seed list")
            print("  were not found in StakeholderRegistry (run seed_v6_registries.py first):")
            for name in sorted(missing):
                print(f"    - {name}")
        total = db.query(StakeholderRelationship).count()
        print(f"\n  Registry total: {total} relationships")
    finally:
        db.close()
    print("\n" + "=" * 60)
    print("  Seed complete")
    print("=" * 60)


if __name__ == "__main__":
    main()
