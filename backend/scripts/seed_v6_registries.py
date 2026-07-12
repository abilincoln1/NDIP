"""
NDIP V6.0 — Registry Seed Script
Populates StakeholderRegistry and OpportunityRegistry with the baseline list
specified by the platform owner. This is DATA, not business logic — running
this script again is safe (it skips rows that already exist by name), and
new entries can be added later via direct insert or a future admin UI without
touching any classification/scoring code.

Run: docker exec agora-backend-1 python scripts/seed_v6_registries.py
"""
import sys
sys.path.insert(0, '/app')
import json

from app.db.database import SessionLocal
from app.models.models import StakeholderRegistry, OpportunityRegistry, StakeholderCategory, OpportunityCategory


# ─── Stakeholder baseline ──────────────────────────────────────────────────────
# (name, short_name, category, sector, aliases)
STAKEHOLDER_SEED = [
    # Federal Government
    ("Office of the President", "Presidency", StakeholderCategory.POLITICAL, "Executive",
     ["president", "presidency", "aso rock", "office of the president"]),
    ("Office of the Vice President", "OVP", StakeholderCategory.POLITICAL, "Executive",
     ["vice president", "ovp", "office of the vice president"]),
    ("Federal Ministry of Finance", "Finance Ministry", StakeholderCategory.PUBLIC_INSTITUTION, "Finance",
     ["ministry of finance", "minister of finance", "federal ministry of finance"]),
    ("Federal Ministry of Budget & Economic Planning", "Budget & Planning", StakeholderCategory.PUBLIC_INSTITUTION, "Finance",
     ["ministry of budget", "economic planning", "budget and national planning"]),
    ("Federal Ministry of Power", "Power Ministry", StakeholderCategory.PUBLIC_INSTITUTION, "Energy",
     ["ministry of power", "minister of power", "federal ministry of power"]),
    ("Federal Ministry of Environment", "Environment Ministry", StakeholderCategory.PUBLIC_INSTITUTION, "Climate",
     ["ministry of environment", "minister of environment", "federal ministry of environment"]),
    ("Federal Ministry of Works", "Works Ministry", StakeholderCategory.PUBLIC_INSTITUTION, "Infrastructure",
     ["ministry of works", "minister of works", "federal ministry of works"]),
    ("Federal Ministry of Industry, Trade & Investment", "FMITI", StakeholderCategory.PUBLIC_INSTITUTION, "Trade",
     ["ministry of industry trade and investment", "fmiti", "trade and investment ministry"]),
    ("Federal Ministry of Steel Development", "Steel Ministry", StakeholderCategory.PUBLIC_INSTITUTION, "Industrial",
     ["ministry of steel development", "steel development ministry"]),
    ("Federal Ministry of Innovation, Science & Technology", "FMIST", StakeholderCategory.PUBLIC_INSTITUTION, "Innovation",
     ["ministry of innovation science and technology", "fmist"]),
    ("Federal Ministry of Agriculture", "Agriculture Ministry", StakeholderCategory.PUBLIC_INSTITUTION, "Agriculture",
     ["ministry of agriculture", "minister of agriculture"]),
    ("Federal Ministry of Water Resources", "Water Resources Ministry", StakeholderCategory.PUBLIC_INSTITUTION, "Infrastructure",
     ["ministry of water resources", "minister of water resources"]),

    # Infrastructure & PPP Institutions
    ("Infrastructure Concession Regulatory Commission", "ICRC", StakeholderCategory.PUBLIC_INSTITUTION, "Infrastructure",
     ["icrc", "infrastructure concession regulatory commission"]),
    ("Infrastructure Corporation of Nigeria", "InfraCorp", StakeholderCategory.PUBLIC_INSTITUTION, "Infrastructure",
     ["infracorp", "infrastructure corporation of nigeria"]),
    ("Nigerian Sovereign Investment Authority", "NSIA", StakeholderCategory.INVESTMENT, "Investment",
     ["nsia", "nigerian sovereign investment authority", "sovereign wealth fund nigeria"]),
    ("Bureau of Public Enterprises", "BPE", StakeholderCategory.PUBLIC_INSTITUTION, "Infrastructure",
     ["bpe", "bureau of public enterprises"]),
    ("Bureau of Public Procurement", "BPP", StakeholderCategory.PUBLIC_INSTITUTION, "Infrastructure",
     ["bpp", "bureau of public procurement"]),

    # Energy
    ("Rural Electrification Agency", "REA", StakeholderCategory.PUBLIC_INSTITUTION, "Energy",
     ["rea", "rural electrification agency"]),
    ("Nigerian Electricity Regulatory Commission", "NERC", StakeholderCategory.PUBLIC_INSTITUTION, "Energy",
     ["nerc", "nigerian electricity regulatory commission"]),
    ("Transmission Company of Nigeria", "TCN", StakeholderCategory.PUBLIC_INSTITUTION, "Energy",
     ["tcn", "transmission company of nigeria"]),
    ("Nigerian National Petroleum Company Limited", "NNPC", StakeholderCategory.PUBLIC_INSTITUTION, "Energy",
     ["nnpc", "nigerian national petroleum company"]),
    ("Energy Commission of Nigeria", "ECN", StakeholderCategory.PUBLIC_INSTITUTION, "Energy",
     ["ecn", "energy commission of nigeria"]),

    # Climate & Environment
    ("National Council on Climate Change", "NCCC", StakeholderCategory.PUBLIC_INSTITUTION, "Climate",
     ["nccc", "national council on climate change"]),
    ("National Environmental Standards and Regulations Enforcement Agency", "NESREA", StakeholderCategory.PUBLIC_INSTITUTION, "Climate",
     ["nesrea", "national environmental standards"]),
    ("Ecological Fund Office", "Ecological Fund", StakeholderCategory.PUBLIC_INSTITUTION, "Climate",
     ["ecological fund office", "ecological fund"]),
    ("Green Bond Programme", "Green Bonds", StakeholderCategory.PUBLIC_INSTITUTION, "Climate Finance",
     ["green bond", "sovereign green bond nigeria"]),

    # Development Finance Institutions
    ("World Bank", "World Bank", StakeholderCategory.INTERNATIONAL, "Development Finance",
     ["world bank", "ibrd", "world bank group"]),
    ("African Development Bank", "AfDB", StakeholderCategory.INTERNATIONAL, "Development Finance",
     ["afdb", "african development bank"]),
    ("Islamic Development Bank", "IsDB", StakeholderCategory.INTERNATIONAL, "Development Finance",
     ["isdb", "islamic development bank"]),
    ("International Finance Corporation", "IFC", StakeholderCategory.INTERNATIONAL, "Development Finance",
     ["ifc", "international finance corporation"]),
    ("United Nations Development Programme", "UNDP", StakeholderCategory.INTERNATIONAL, "Development Finance",
     ["undp", "united nations development programme"]),
    ("United Nations Industrial Development Organization", "UNIDO", StakeholderCategory.INTERNATIONAL, "Development Finance",
     ["unido", "united nations industrial development organization"]),
    ("Africa Finance Corporation", "AFC", StakeholderCategory.INVESTMENT, "Development Finance",
     ["afc", "africa finance corporation"]),
    ("Africa50", "Africa50", StakeholderCategory.INVESTMENT, "Infrastructure Finance",
     ["africa50", "africa 50"]),

    # Diaspora
    ("Nigerians in Diaspora Commission", "NiDCOM", StakeholderCategory.DIASPORA, "Diaspora",
     ["nidcom", "nigerians in diaspora commission"]),
    ("RTIFN", "RTIFN", StakeholderCategory.DIASPORA, "Diaspora",
     ["rtifn"]),
    ("Nigerian Professional Diaspora Associations", "Diaspora Professional Networks", StakeholderCategory.DIASPORA, "Diaspora",
     ["diaspora association", "professional diaspora network", "nigerian professionals abroad"]),
    ("Nigerian Chambers of Commerce Abroad", "Diaspora Chambers", StakeholderCategory.DIASPORA, "Diaspora",
     ["nigerian chamber of commerce", "chamber of commerce abroad"]),

    # State-level (generic roles, not named to a specific state — per platform owner instruction)
    ("Governor (State-Level)", "Governor", StakeholderCategory.POLITICAL, "State Government",
     ["governor", "state governor"]),
    ("Deputy Governor (State-Level)", "Deputy Governor", StakeholderCategory.POLITICAL, "State Government",
     ["deputy governor"]),
    ("State Ministry of Finance (Generic)", "State Finance Ministry", StakeholderCategory.PUBLIC_INSTITUTION, "State Government",
     ["state ministry of finance", "commissioner for finance"]),
    ("State Ministry of Environment (Generic)", "State Environment Ministry", StakeholderCategory.PUBLIC_INSTITUTION, "State Government",
     ["state ministry of environment", "commissioner for environment"]),
    ("State Ministry of Energy (Generic)", "State Energy Ministry", StakeholderCategory.PUBLIC_INSTITUTION, "State Government",
     ["state ministry of energy", "commissioner for energy", "commissioner for power"]),
    ("State Investment Promotion Agency (Generic)", "State Investment Agency", StakeholderCategory.PUBLIC_INSTITUTION, "State Government",
     ["state investment promotion agency", "sipa"]),
    ("State PPP Office (Generic)", "State PPP Office", StakeholderCategory.PUBLIC_INSTITUTION, "State Government",
     ["state ppp office", "public private partnership office"]),
]

# ─── Opportunity programme baseline ────────────────────────────────────────────
# (name, category, description, aliases)
OPPORTUNITY_SEED = [
    ("PPP Projects", OpportunityCategory.PPP,
     "Public-private partnership concessions and projects",
     ["ppp", "public private partnership", "concession agreement"]),
    ("InfraCorp Initiatives", OpportunityCategory.INFRASTRUCTURE,
     "Projects led or co-financed by Infrastructure Corporation of Nigeria",
     ["infracorp project", "infracorp initiative"]),
    ("State Infrastructure Concessions", OpportunityCategory.INFRASTRUCTURE,
     "State-level infrastructure concession opportunities",
     ["state concession", "state infrastructure project"]),
    ("Industrial Parks", OpportunityCategory.INDUSTRIAL_DEVELOPMENT,
     "Industrial park development and special economic zones",
     ["industrial park", "special economic zone", "free trade zone"]),
    ("Transport Projects", OpportunityCategory.INFRASTRUCTURE,
     "Road, rail, ports, and transport infrastructure projects",
     ["transport project", "rail project", "road project", "port concession"]),

    ("Mini-Grid Programmes", OpportunityCategory.ENERGY,
     "Decentralised mini-grid electrification programmes",
     ["mini-grid", "minigrid", "mini grid programme"]),
    ("Rural Electrification Projects", OpportunityCategory.ENERGY,
     "Rural and underserved-area electrification initiatives",
     ["rural electrification", "off-grid electrification"]),
    ("Renewable Energy Projects", OpportunityCategory.ENERGY,
     "Solar, wind, hydro and other renewable generation projects",
     ["solar project", "renewable energy project", "wind power", "hydro power"]),
    ("Grid Expansion Programmes", OpportunityCategory.ENERGY,
     "Transmission and distribution grid expansion initiatives",
     ["grid expansion", "transmission expansion", "distribution upgrade"]),
    ("Gas-to-Power Projects", OpportunityCategory.ENERGY,
     "Gas-fired power generation and gas infrastructure projects",
     ["gas-to-power", "gas to power", "gas fired power plant"]),

    ("Municipal Waste Programmes", OpportunityCategory.WASTE_TO_ENERGY,
     "Municipal solid waste management programmes",
     ["municipal waste", "solid waste management", "waste collection programme"]),
    ("Waste Management Concessions", OpportunityCategory.WASTE_TO_ENERGY,
     "Concessioned waste management and processing contracts",
     ["waste management concession", "waste concession"]),
    ("Circular Economy Initiatives", OpportunityCategory.WASTE_TO_ENERGY,
     "Circular economy and waste-to-value initiatives",
     ["circular economy", "waste to value", "waste recycling initiative"]),
    ("Carbon-Credit Linked Projects", OpportunityCategory.CARBON_MARKETS,
     "Projects generating or linked to tradable carbon credits",
     ["carbon credit project", "carbon offset project"]),

    ("Green Climate Fund Programmes", OpportunityCategory.CLIMATE_FINANCE,
     "Green Climate Fund-financed programmes in Nigeria",
     ["green climate fund", "gcf"]),
    ("Adaptation Fund Programmes", OpportunityCategory.CLIMATE_FINANCE,
     "Adaptation Fund-financed climate resilience programmes",
     ["adaptation fund"]),
    ("Climate Investment Funds Programmes", OpportunityCategory.CLIMATE_FINANCE,
     "Climate Investment Funds-financed programmes",
     ["climate investment funds", "cif programme"]),
    ("Carbon Market Programmes", OpportunityCategory.CARBON_MARKETS,
     "National or voluntary carbon market programmes",
     ["carbon market", "carbon trading scheme"]),

    ("Diaspora Bonds", OpportunityCategory.DIASPORA_INVESTMENT,
     "Diaspora bond issuances and related investment instruments",
     ["diaspora bond"]),
    ("Diaspora Investment Funds", OpportunityCategory.DIASPORA_INVESTMENT,
     "Investment funds targeting diaspora capital",
     ["diaspora investment fund", "diaspora fund"]),
    ("Diaspora Business Missions", OpportunityCategory.DIASPORA_INVESTMENT,
     "Trade and investment missions engaging diaspora business communities",
     ["diaspora business mission", "diaspora trade mission"]),
    ("Trade Facilitation Programmes", OpportunityCategory.TRADE_INVESTMENT,
     "Programmes facilitating trade and cross-border investment",
     ["trade facilitation", "trade facilitation programme"]),
]


def seed_stakeholders(db):
    created = 0
    skipped = 0
    for name, short_name, category, sector, aliases in STAKEHOLDER_SEED:
        existing = db.query(StakeholderRegistry).filter(StakeholderRegistry.name == name).first()
        if existing:
            skipped += 1
            continue
        db.add(StakeholderRegistry(
            name=name, short_name=short_name, category=category, sector=sector,
            aliases_json=json.dumps(aliases),
        ))
        created += 1
    db.commit()
    return created, skipped


def seed_opportunities(db):
    created = 0
    skipped = 0
    for name, category, description, aliases in OPPORTUNITY_SEED:
        existing = db.query(OpportunityRegistry).filter(OpportunityRegistry.name == name).first()
        if existing:
            skipped += 1
            continue
        db.add(OpportunityRegistry(
            name=name, category=category, description=description,
            aliases_json=json.dumps(aliases),
        ))
        created += 1
    db.commit()
    return created, skipped


def main():
    print("=" * 60)
    print("  NDIP V6.0 — Registry Seed")
    print("=" * 60)
    db = SessionLocal()
    try:
        sc, ss = seed_stakeholders(db)
        print(f"\n  Stakeholders: {sc} created, {ss} already existed (skipped)")
        oc, os_ = seed_opportunities(db)
        print(f"  Opportunities: {oc} created, {os_} already existed (skipped)")

        total_stakeholders = db.query(StakeholderRegistry).count()
        total_opportunities = db.query(OpportunityRegistry).count()
        print(f"\n  Registry totals: {total_stakeholders} stakeholders, {total_opportunities} opportunity types")
    finally:
        db.close()
    print("\n" + "=" * 60)
    print("  Seed complete")
    print("=" * 60)


if __name__ == "__main__":
    main()
