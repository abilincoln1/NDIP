"""
NDIP V6.1.1 -- Backfill stakeholder_type on the 45 pre-existing
institutional StakeholderRegistry rows (created before this field
existed). Mapping built directly from the live precheck's real
category/sector/name data, not assumed.

Mapping rule, applied by name (explicit, auditable, not regex-guessed):
  - Federal ministries ("Federal Ministry of ...") -> FEDERAL_MINISTRY
  - Federal agencies/commissions/regulators/offices/corporations -> FEDERAL_AGENCY
  - State-level generic roles (Governor, Deputy Governor, "State ... (Generic)") -> STATE_GOVERNMENT
  - Office of the President / Vice President -> POLITICAL_ACTOR (most senior
    executive office-holders, distinct from a ministry/agency)
  - International development finance institutions (World Bank, AfDB, IFC,
    Islamic Development Bank, UNDP, UNIDO) -> DEVELOPMENT_FINANCE
  - Domestic/Africa-focused investment vehicles (NSIA, Africa Finance
    Corporation, Africa50) -> INVESTOR
  - Diaspora-sector ORGANISATIONS (RTIFN, Nigerians in Diaspora Commission,
    diaspora chambers/associations) -> DIASPORA_LEADER. NOTE: these remain
    institutional entries (organisations), not named individuals -- using
    DIASPORA_LEADER as the closest-fit existing enum value for the
    organisation's sector, consistent with the established public/private
    governance boundary (RTIFN itself, as an organisation, is already in
    the registry from V6.0 and is not a private individual).

Run: docker exec agora-backend-1 python scripts/v611_backfill_stakeholder_type.py
"""
import sys
sys.path.insert(0, '/app')

from app.db.database import SessionLocal
from app.models.models import StakeholderRegistry, StakeholderType

BACKFILL_MAP = {
    # Federal ministries
    "Federal Ministry of Agriculture": StakeholderType.FEDERAL_MINISTRY,
    "Federal Ministry of Budget & Economic Planning": StakeholderType.FEDERAL_MINISTRY,
    "Federal Ministry of Environment": StakeholderType.FEDERAL_MINISTRY,
    "Federal Ministry of Finance": StakeholderType.FEDERAL_MINISTRY,
    "Federal Ministry of Industry, Trade & Investment": StakeholderType.FEDERAL_MINISTRY,
    "Federal Ministry of Innovation, Science & Technology": StakeholderType.FEDERAL_MINISTRY,
    "Federal Ministry of Power": StakeholderType.FEDERAL_MINISTRY,
    "Federal Ministry of Steel Development": StakeholderType.FEDERAL_MINISTRY,
    "Federal Ministry of Water Resources": StakeholderType.FEDERAL_MINISTRY,
    "Federal Ministry of Works": StakeholderType.FEDERAL_MINISTRY,

    # Federal agencies / commissions / regulators / corporations
    "Bureau of Public Enterprises": StakeholderType.FEDERAL_AGENCY,
    "Bureau of Public Procurement": StakeholderType.FEDERAL_AGENCY,
    "Ecological Fund Office": StakeholderType.FEDERAL_AGENCY,
    "Energy Commission of Nigeria": StakeholderType.FEDERAL_AGENCY,
    "Green Bond Programme": StakeholderType.FEDERAL_AGENCY,
    "Infrastructure Concession Regulatory Commission": StakeholderType.FEDERAL_AGENCY,
    "Infrastructure Corporation of Nigeria": StakeholderType.FEDERAL_AGENCY,
    "National Council on Climate Change": StakeholderType.FEDERAL_AGENCY,
    "National Environmental Standards and Regulations Enforcement Agency": StakeholderType.FEDERAL_AGENCY,
    "Nigerian Electricity Regulatory Commission": StakeholderType.FEDERAL_AGENCY,
    "Nigerian National Petroleum Company Limited": StakeholderType.FEDERAL_AGENCY,
    "Rural Electrification Agency": StakeholderType.FEDERAL_AGENCY,
    "Transmission Company of Nigeria": StakeholderType.FEDERAL_AGENCY,

    # State government (generic roles, applies across states)
    "Deputy Governor (State-Level)": StakeholderType.STATE_GOVERNMENT,
    "Governor (State-Level)": StakeholderType.STATE_GOVERNMENT,
    "State Investment Promotion Agency (Generic)": StakeholderType.STATE_GOVERNMENT,
    "State Ministry of Energy (Generic)": StakeholderType.STATE_GOVERNMENT,
    "State Ministry of Environment (Generic)": StakeholderType.STATE_GOVERNMENT,
    "State Ministry of Finance (Generic)": StakeholderType.STATE_GOVERNMENT,
    "State PPP Office (Generic)": StakeholderType.STATE_GOVERNMENT,

    # Most senior federal executive offices
    "Office of the President": StakeholderType.POLITICAL_ACTOR,
    "Office of the Vice President": StakeholderType.POLITICAL_ACTOR,

    # International development finance
    "African Development Bank": StakeholderType.DEVELOPMENT_FINANCE,
    "International Finance Corporation": StakeholderType.DEVELOPMENT_FINANCE,
    "Islamic Development Bank": StakeholderType.DEVELOPMENT_FINANCE,
    "United Nations Development Programme": StakeholderType.DEVELOPMENT_FINANCE,
    "United Nations Industrial Development Organization": StakeholderType.DEVELOPMENT_FINANCE,
    "World Bank": StakeholderType.DEVELOPMENT_FINANCE,

    # Investment vehicles
    "Africa Finance Corporation": StakeholderType.INVESTOR,
    "Africa50": StakeholderType.INVESTOR,
    "Nigerian Sovereign Investment Authority": StakeholderType.INVESTOR,

    # Diaspora-sector organisations (institutional, not individual)
    "Nigerian Chambers of Commerce Abroad": StakeholderType.DIASPORA_LEADER,
    "Nigerian Professional Diaspora Associations": StakeholderType.DIASPORA_LEADER,
    "Nigerians in Diaspora Commission": StakeholderType.DIASPORA_LEADER,
    "RTIFN": StakeholderType.DIASPORA_LEADER,
}


def main():
    print("=" * 70)
    print("  NDIP V6.1.1 -- Backfill stakeholder_type on institutional rows")
    print("=" * 70)
    db = SessionLocal()
    try:
        updated = 0
        not_found = []
        for name, stype in BACKFILL_MAP.items():
            row = db.query(StakeholderRegistry).filter(StakeholderRegistry.name == name).first()
            if not row:
                not_found.append(name)
                continue
            row.stakeholder_type = stype
            updated += 1
        db.commit()

        print(f"\n  Updated: {updated} rows")
        if not_found:
            print(f"  NOT FOUND (name mismatch -- review): {not_found}")

        remaining = db.query(StakeholderRegistry).filter(StakeholderRegistry.stakeholder_type.is_(None)).all()
        print(f"\n  Rows STILL lacking stakeholder_type after this backfill: {len(remaining)}")
        for r in remaining:
            print(f"    id={r.id} name={r.name} (category={r.category})")
    finally:
        db.close()
    print("\n" + "=" * 70)
    print("  Backfill complete")
    print("=" * 70)


if __name__ == "__main__":
    main()
