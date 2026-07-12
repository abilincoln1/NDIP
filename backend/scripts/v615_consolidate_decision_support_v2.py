"""
NDIP V6.1.5 -- Complete EDE consolidation, fixed version with correct
blank-line anchor (confirmed via live diagnostic).

Run: docker exec agora-backend-1 python scripts/v615_consolidate_decision_support_v2.py
"""
PATH = "/app/app/services/decision_support.py"

with open(PATH, "r") as f:
    content = f.read()

old = '''    NARRATIVE_SECTOR_MAP = {
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

new = '''    # V6.1.5 -- consolidated: stakeholder resolution now delegates to the
    # Executive Decision Engine's shared resolve_responsible_stakeholders(),
    # the single authoritative implementation (previously duplicated here
    # as an exact copy under V6.1.3). Decision Support retains ONLY its
    # orchestration responsibilities: applying time_horizon per bucket,
    # the adaptive confidence lookup (V5.8 learning-loop integration,
    # genuinely specific to Decision Support), and persistence via
    # record_recommendation().
    from app.services.executive_decision_engine import resolve_responsible_stakeholders

    for bucket, horizon in horizon_map.items():
        for action in result.get(bucket, []):
            action["time_horizon"] = horizon
            action["responsible_stakeholders"] = resolve_responsible_stakeholders(db, action.get("issue", ""))
            action.setdefault("generated_by", "Executive Decision Engine")

            # V5.8 Phase K'''

count = content.count(old)
print(f"Anchor found {count} time(s).")

if count != 1:
    print(f"Expected exactly 1 occurrence, found {count} -- aborting without changes.")
else:
    content = content.replace(old, new, 1)
    with open(PATH, "w") as f:
        f.write(content)
    print("Patched successfully: Decision Support now delegates stakeholder resolution to the Executive Decision Engine.")
