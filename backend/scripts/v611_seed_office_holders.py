"""
NDIP V6.1.1 Phase A -- Public Office Holder Population

Seeds named public office-holders as NEW StakeholderRegistry rows,
distinct from the existing institutional rows (e.g. "Federal Ministry of
Power" stays exactly as-is; "Minister of Power" is added as a separate,
linked row). This follows the spec's explicit Phase B rule: never
overwrite institutional records with personal names.

Scope, per the agreed and explicit governance decision: PUBLIC office-
holders and publicly identifiable institutional actors ONLY. No private
citizens, no RTIFN members, no diaspora individuals. Every name below is
a public office-holder acting in an official, publicly reported
capacity.

stakeholder_type values used here are deliberately ROLE-based, not
person-based (e.g. "Minister of Power", not a specific minister's
personal name) -- this is a second, more conservative design choice on
top of the public/private line already agreed: even within public
office-holders, tracking the OFFICE (which survives political turnover)
rather than hard-coding today's office-holder's name avoids the
spec's own stated risk ("institutional continuity must survive
political transitions"). Where a specific named individual is later
confirmed and wanted, that should update the existing row's `notes` or a
future `current_office_holder_name` field -- NOT replace the role-based
`name` field itself.

Run: docker exec agora-backend-1 python scripts/v611_seed_office_holders.py
"""
import sys
sys.path.insert(0, '/app')
import json

from app.db.database import SessionLocal
from app.models.models import StakeholderRegistry, StakeholderCategory, StakeholderType


# (name, category, stakeholder_type, sector, role_description, aliases)
OFFICE_HOLDER_SEED = [
    # --- Federal Executive ---
    ("Minister of Power", StakeholderCategory.POLITICAL, StakeholderType.FEDERAL_MINISTRY,
     "Energy", "Cabinet minister responsible for the federal power sector portfolio.",
     ["minister of power", "power minister"]),
    ("Minister of Environment", StakeholderCategory.POLITICAL, StakeholderType.FEDERAL_MINISTRY,
     "Climate", "Cabinet minister responsible for the federal environment portfolio.",
     ["minister of environment", "environment minister"]),
    ("Minister of Works", StakeholderCategory.POLITICAL, StakeholderType.FEDERAL_MINISTRY,
     "Infrastructure", "Cabinet minister responsible for the federal works/infrastructure portfolio.",
     ["minister of works", "works minister"]),
    ("Minister of Finance", StakeholderCategory.POLITICAL, StakeholderType.FEDERAL_MINISTRY,
     "Finance", "Cabinet minister responsible for the federal finance portfolio.",
     ["minister of finance", "finance minister"]),
    ("Minister of Budget and Economic Planning", StakeholderCategory.POLITICAL, StakeholderType.FEDERAL_MINISTRY,
     "Finance", "Cabinet minister responsible for federal budget and economic planning.",
     ["minister of budget", "minister of economic planning"]),
    ("Permanent Secretary, Federal Ministry of Power", StakeholderCategory.PUBLIC_INSTITUTION, StakeholderType.FEDERAL_MINISTRY,
     "Energy", "Most senior civil servant in the Federal Ministry of Power.",
     ["permanent secretary power", "perm sec power"]),
    ("Permanent Secretary, Federal Ministry of Environment", StakeholderCategory.PUBLIC_INSTITUTION, StakeholderType.FEDERAL_MINISTRY,
     "Climate", "Most senior civil servant in the Federal Ministry of Environment.",
     ["permanent secretary environment", "perm sec environment"]),

    # --- Federal Agencies (CEOs/DGs) ---
    ("Managing Director, Rural Electrification Agency", StakeholderCategory.PUBLIC_INSTITUTION, StakeholderType.FEDERAL_AGENCY,
     "Energy", "Chief executive of the Rural Electrification Agency (REA).",
     ["rea managing director", "rea md", "rea ceo"]),
    ("Chairman, Nigerian Electricity Regulatory Commission", StakeholderCategory.PUBLIC_INSTITUTION, StakeholderType.FEDERAL_AGENCY,
     "Energy", "Chief executive/chairman of NERC, the electricity sector regulator.",
     ["nerc chairman", "nerc chief executive"]),
    ("Managing Director, Transmission Company of Nigeria", StakeholderCategory.PUBLIC_INSTITUTION, StakeholderType.FEDERAL_AGENCY,
     "Energy", "Chief executive of the Transmission Company of Nigeria (TCN).",
     ["tcn managing director", "tcn md"]),
    ("Director-General, National Council on Climate Change", StakeholderCategory.PUBLIC_INSTITUTION, StakeholderType.FEDERAL_AGENCY,
     "Climate", "Director-General of the National Council on Climate Change (NCCC).",
     ["nccc director-general", "nccc dg"]),
    ("Director-General, National Environmental Standards and Regulations Enforcement Agency", StakeholderCategory.PUBLIC_INSTITUTION, StakeholderType.FEDERAL_AGENCY,
     "Climate", "Director-General of NESREA, the federal environmental enforcement agency.",
     ["nesrea director-general", "nesrea dg"]),
    ("Director-General, Infrastructure Concession Regulatory Commission", StakeholderCategory.PUBLIC_INSTITUTION, StakeholderType.FEDERAL_AGENCY,
     "Infrastructure", "Director-General of the Infrastructure Concession Regulatory Commission (ICRC).",
     ["icrc director-general", "icrc dg"]),
    ("Director-General, Bureau of Public Procurement", StakeholderCategory.PUBLIC_INSTITUTION, StakeholderType.FEDERAL_AGENCY,
     "Infrastructure", "Director-General of the Bureau of Public Procurement (BPP).",
     ["bpp director-general", "bpp dg"]),
    ("Managing Director, Nigeria Sovereign Investment Authority", StakeholderCategory.INVESTMENT, StakeholderType.FEDERAL_AGENCY,
     "Investment", "Chief executive of the Nigeria Sovereign Investment Authority (NSIA).",
     ["nsia managing director", "nsia md", "nsia ceo"]),

    # --- National Assembly ---
    ("Senate President", StakeholderCategory.POLITICAL, StakeholderType.LEGISLATOR,
     "Legislature", "Presiding officer of the Nigerian Senate.",
     ["senate president"]),
    ("Speaker of the House of Representatives", StakeholderCategory.POLITICAL, StakeholderType.LEGISLATOR,
     "Legislature", "Presiding officer of the House of Representatives.",
     ["speaker of the house", "house speaker"]),
    ("Senate Committee Chair on Power", StakeholderCategory.POLITICAL, StakeholderType.LEGISLATOR,
     "Energy", "Chair of the Senate Committee responsible for power sector oversight and legislation.",
     ["senate power committee chair"]),
    ("Senate Committee Chair on Environment and Climate Change", StakeholderCategory.POLITICAL, StakeholderType.LEGISLATOR,
     "Climate", "Chair of the Senate Committee responsible for environment and climate oversight.",
     ["senate environment committee chair", "senate climate committee chair"]),

    # --- State Government (role-level, generic -- per existing platform pattern) ---
    ("State Commissioner for Energy", StakeholderCategory.POLITICAL, StakeholderType.STATE_GOVERNMENT,
     "Energy", "State-level cabinet commissioner responsible for energy policy (generic role, applies across states).",
     ["state energy commissioner", "commissioner for energy"]),
    ("State Commissioner for Environment", StakeholderCategory.POLITICAL, StakeholderType.STATE_GOVERNMENT,
     "Climate", "State-level cabinet commissioner responsible for environment policy (generic role, applies across states).",
     ["state environment commissioner", "commissioner for environment"]),

    # --- Development Finance (Nigeria-resident leadership) ---
    ("World Bank Nigeria Country Director", StakeholderCategory.INTERNATIONAL, StakeholderType.DEVELOPMENT_FINANCE,
     "Development Finance", "Senior World Bank official responsible for the Nigeria country programme.",
     ["world bank country director nigeria", "world bank nigeria director"]),
    ("African Development Bank Nigeria Country Director", StakeholderCategory.INTERNATIONAL, StakeholderType.DEVELOPMENT_FINANCE,
     "Development Finance", "Senior AfDB official responsible for the Nigeria country programme.",
     ["afdb country director nigeria", "afdb nigeria director"]),
    ("UNDP Nigeria Resident Representative", StakeholderCategory.INTERNATIONAL, StakeholderType.INTERNATIONAL_DONOR,
     "Development Finance", "Senior UNDP official responsible for the Nigeria country programme.",
     ["undp resident representative nigeria", "undp nigeria representative"]),
]


def seed_office_holders(db):
    created = 0
    skipped = 0
    for name, category, stakeholder_type, sector, role_description, aliases in OFFICE_HOLDER_SEED:
        existing = db.query(StakeholderRegistry).filter(StakeholderRegistry.name == name).first()
        if existing:
            skipped += 1
            continue
        db.add(StakeholderRegistry(
            name=name, category=category, stakeholder_type=stakeholder_type,
            sector=sector, role_description=role_description,
            aliases_json=json.dumps(aliases),
        ))
        created += 1
    db.commit()
    return created, skipped


def main():
    print("=" * 70)
    print("  NDIP V6.1.1 Phase A -- Public Office Holder Seed")
    print("=" * 70)
    db = SessionLocal()
    try:
        created, skipped = seed_office_holders(db)
        print(f"\n  Office-holder roles: {created} created, {skipped} already existed (skipped)")

        # Coverage report -- counts by stakeholder_type, confirming the new field is genuinely populated
        print("\n  COVERAGE REPORT (stakeholder_type, post-seed):")
        from sqlalchemy import func
        type_counts = db.query(StakeholderRegistry.stakeholder_type, func.count(StakeholderRegistry.id)).filter(
            StakeholderRegistry.stakeholder_type.isnot(None)
        ).group_by(StakeholderRegistry.stakeholder_type).all()
        for t, count in type_counts:
            print(f"    {t:30s} {count}")

        total_active = db.query(StakeholderRegistry).filter(StakeholderRegistry.is_active == True).count()
        print(f"\n  Total active StakeholderRegistry rows (institutions + roles combined): {total_active}")
    finally:
        db.close()
    print("\n" + "=" * 70)
    print("  Seed complete")
    print("=" * 70)


if __name__ == "__main__":
    main()
