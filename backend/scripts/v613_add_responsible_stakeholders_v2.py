"""
NDIP V6.1.3 Phase A/B -- add responsible_stakeholders to every Decision
Support recommendation. Fixed version: anchor text corrected to match
the real file's blank lines (confirmed via live diagnostic), which the
first attempt's anchor was missing.

Run: docker exec agora-backend-1 python scripts/v613_add_responsible_stakeholders_v2.py
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
            action["time_horizon"] = horizon

            # V5.8 Phase K'''

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
    # values confirmed live in StakeholderRegistry (Energy, Climate,
    # Infrastructure, Finance, Diaspora, etc. -- not invented). Each
    # recommendation's "issue" text is checked against these narrative
    # keywords to find the relevant sector, then real stakeholders in that
    # sector are looked up -- preferring named office-holders over plain
    # institutions where both exist, per the spec's anti-anonymity rule.
    NARRATIVE_SECTOR_MAP = {
        "governance": "Executive",
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
            if keyword in issue_lower:
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
        named = [r for r in rows if r.stakeholder_type is not None]
        institutional = [r for r in rows if r.stakeholder_type is None]
        ordered = named + institutional
        return [r.name for r in ordered[:limit]]

    for bucket, horizon in horizon_map.items():
        for action in result.get(bucket, []):
            action["time_horizon"] = horizon
            action["responsible_stakeholders"] = _lookup_responsible_stakeholders(action.get("issue", ""))

            # V5.8 Phase K'''

count = content.count(old)
print(f"Anchor found {count} time(s).")

if count != 1:
    print(f"Expected exactly 1 occurrence, found {count} -- aborting without changes.")
else:
    content = content.replace(old, new, 1)
    with open(PATH, "w") as f:
        f.write(content)
    print("Patched successfully: responsible_stakeholders added to every Decision Support recommendation.")
