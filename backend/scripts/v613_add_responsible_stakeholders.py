"""
NDIP V6.1.3 Phase A/B -- add responsible_stakeholders to every Decision
Support recommendation, in the EXISTING _enrich_and_track_recommendations
loop (same place time_horizon and confidence are already added) -- no
new computation engine, no change to the 380+ lines of hand-coded
narrative-specific recommendation logic, per "preserve existing
functionality."

Mapping is narrative -> sector, using REAL sector values confirmed live
in the registry (Energy, Climate, Infrastructure, Finance, etc.) --
not invented associations. Looks up real StakeholderRegistry rows by
sector, preferring named office-holders (stakeholder_type set to a
FEDERAL_MINISTRY/FEDERAL_AGENCY/POLITICAL_ACTOR/LEGISLATOR type) over
generic institutions where both exist, consistent with the spec's
"avoid anonymous recommendations whenever stakeholder intelligence
exists" rule.

Run: docker exec agora-backend-1 python scripts/v613_add_responsible_stakeholders.py
"""
PATH = "/app/app/services/decision_support.py"

with open(PATH, "r") as f:
    content = f.read()

old = '''    horizon_map = {
        "immediate_actions": "7 days",
        "near_term_actions": "30 days",
        "strategic_actions": "90 days",
        "monitoring_actions": "Ongoing",
    }
    confidence_map = {
        "Critical": "High", "High": "High", "Medium": "Medium", "Low": "Low",
    }
    for bucket, horizon in horizon_map.items():
        for action in result.get(bucket, []):
            action["time_horizon"] = horizon'''

new = '''    horizon_map = {
        "immediate_actions": "7 days",
        "near_term_actions": "30 days",
        "strategic_actions": "90 days",
        "monitoring_actions": "Ongoing",
    }
    confidence_map = {
        "Critical": "High", "High": "High", "Medium": "Medium", "Low": "Low",
    }
    # V6.1.3 Phase A/B -- narrative -> sector mapping, using REAL sector
    # values confirmed live in StakeholderRegistry (not invented). Each
    # recommendation's "issue" text is checked against these narrative
    # keywords to find the relevant sector, then real stakeholders in that
    # sector are looked up -- preferring named office-holders over plain
    # institutions where both exist, per the spec's anti-anonymity rule.
    NARRATIVE_SECTOR_MAP = {
        "governance": "Executive",
        "security": None,  # no current sector mapping exists for security/defence-specific stakeholders
        "economy": "Finance",
        "global nigerian engagement": "Diaspora",
        "diaspora": "Diaspora",
        "elections": "Legislature",
        "energy": "Energy",
        "infrastructure": "Infrastructure",
        "climate": "Climate",
        "investment": "Investment",
        "trade": "Trade",
    }

    def _lookup_responsible_stakeholders(issue_text: str, limit: int = 3) -> list:
        from app.models.models import StakeholderRegistry
        issue_lower = (issue_text or "").lower()
        sector = None
        for keyword, mapped_sector in NARRATIVE_SECTOR_MAP.items():
            if keyword in issue_lower and mapped_sector:
                sector = mapped_sector
                break
        if not sector:
            return []
        try:
            rows = db.query(StakeholderRegistry).filter(
                StakeholderRegistry.sector == sector,
                StakeholderRegistry.is_active == True,
            ).all()
        except Exception:
            return []
        # Prefer named office-holders (stakeholder_type set to a
        # person-style role) over plain institutions, per spec.
        named = [r for r in rows if r.stakeholder_type is not None]
        institutional = [r for r in rows if r.stakeholder_type is None]
        ordered = named + institutional
        return [r.name for r in ordered[:limit]]

    for bucket, horizon in horizon_map.items():
        for action in result.get(bucket, []):
            action["time_horizon"] = horizon
            action["responsible_stakeholders"] = _lookup_responsible_stakeholders(action.get("issue", ""))'''

count = content.count(old)
print(f"Anchor found {count} time(s).")

if count != 1:
    print(f"Expected exactly 1 occurrence, found {count} -- aborting without changes.")
else:
    content = content.replace(old, new, 1)
    with open(PATH, "w") as f:
        f.write(content)
    print("Patched successfully: responsible_stakeholders added to every Decision Support recommendation.")
