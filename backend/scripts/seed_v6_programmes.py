"""
NDIP V6.0A Phase A -- Opportunity Registry Coverage Completion

Seeds FEDERAL_PROGRAMMES and STATE_PROGRAMMES opportunity types, which
the live audit confirmed have zero coverage despite being required
categories. Same registry-driven principle as the original V6.0 seed:
this is DATA, not business logic -- running again is safe (skips
existing names), and new entries can be added later via the registry
management UI with no code change.

Run: docker exec agora-backend-1 python scripts/seed_v6_programmes.py
"""
import sys
sys.path.insert(0, '/app')

from app.db.database import SessionLocal
from app.models.models import OpportunityRegistry, OpportunityCategory


FEDERAL_PROGRAMME_SEED = [
    ("Rural Electrification Agency Programmes", OpportunityCategory.FEDERAL_PROGRAMMES,
     "REA-led federal rural electrification and mini-grid deployment programmes",
     ["rea programme", "rural electrification programme", "rea mini-grid", "rea solar programme"]),
    ("Federal Infrastructure Initiatives", OpportunityCategory.FEDERAL_PROGRAMMES,
     "Federally-sponsored infrastructure development initiatives (roads, rail, ports)",
     ["federal infrastructure initiative", "federal infrastructure programme", "national infrastructure plan"]),
    ("Energy Transition Programmes", OpportunityCategory.FEDERAL_PROGRAMMES,
     "Federal energy transition and decarbonisation programmes",
     ["energy transition programme", "energy transition plan", "national energy transition"]),
    ("Federal Climate Initiatives", OpportunityCategory.FEDERAL_PROGRAMMES,
     "Federally-sponsored climate adaptation and mitigation initiatives",
     ["federal climate initiative", "national climate programme", "climate change initiative nigeria"]),
    ("SME Development Programmes", OpportunityCategory.FEDERAL_PROGRAMMES,
     "Federal small and medium enterprise development and funding programmes",
     ["sme development programme", "sme fund", "small business development programme"]),
    ("National Social Investment Programmes", OpportunityCategory.FEDERAL_PROGRAMMES,
     "Federal social investment and poverty-alleviation programmes",
     ["social investment programme", "n-power", "conditional cash transfer"]),
    ("Federal Housing Programmes", OpportunityCategory.FEDERAL_PROGRAMMES,
     "Federally-sponsored affordable housing development programmes",
     ["federal housing programme", "national housing programme", "affordable housing scheme"]),

    ("State Infrastructure Initiatives", OpportunityCategory.STATE_PROGRAMMES,
     "State-level infrastructure development initiatives (generic, applies across states)",
     ["state infrastructure initiative", "state infrastructure programme", "state road project"]),
    ("State Energy Programmes", OpportunityCategory.STATE_PROGRAMMES,
     "State-level electrification and energy access programmes",
     ["state energy programme", "state electrification programme", "state power project"]),
    ("State PPP Opportunities", OpportunityCategory.STATE_PROGRAMMES,
     "State-level public-private partnership concession opportunities",
     ["state ppp opportunity", "state concession", "state ppp project"]),
    ("State Investment Programmes", OpportunityCategory.STATE_PROGRAMMES,
     "State-level investment promotion and incentive programmes",
     ["state investment programme", "state investment promotion", "state incentive scheme"]),
    ("State Climate and Environment Programmes", OpportunityCategory.STATE_PROGRAMMES,
     "State-level climate adaptation and environmental management programmes",
     ["state climate programme", "state environment programme", "state ecological programme"]),
]


def seed_programmes(db):
    created = 0
    skipped = 0
    for name, category, description, aliases in FEDERAL_PROGRAMME_SEED:
        existing = db.query(OpportunityRegistry).filter(OpportunityRegistry.name == name).first()
        if existing:
            skipped += 1
            continue
        db.add(OpportunityRegistry(
            name=name, category=category, description=description,
            aliases_json=__import__("json").dumps(aliases),
        ))
        created += 1
    db.commit()
    return created, skipped


def main():
    print("=" * 60)
    print("  NDIP V6.0A Phase A -- Federal/State Programme Seed")
    print("=" * 60)
    db = SessionLocal()
    try:
        created, skipped = seed_programmes(db)
        print(f"\n  Programme opportunity types: {created} created, {skipped} already existed (skipped)")

        # Coverage report -- counts by category, confirming the gap is closed
        print("\n  COVERAGE REPORT (all categories, post-seed):")
        for cat in OpportunityCategory:
            count = db.query(OpportunityRegistry).filter(
                OpportunityRegistry.category == cat, OpportunityRegistry.is_active == True
            ).count()
            print(f"    {cat.value:30s} {count}")
    finally:
        db.close()
    print("\n" + "=" * 60)
    print("  Seed complete")
    print("=" * 60)


if __name__ == "__main__":
    main()
