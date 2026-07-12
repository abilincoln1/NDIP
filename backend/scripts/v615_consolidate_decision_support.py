"""
NDIP V6.1.5 -- Complete EDE consolidation: remove Decision Support's
duplicated NARRATIVE_SECTOR_MAP and _lookup_responsible_stakeholders
(an exact, line-for-line copy of what now lives in
executive_decision_engine.resolve_responsible_stakeholders), replacing
the call site with the shared function.

PRESERVED, deliberately, per the spec's explicit instruction that
Decision Support remains the orchestration layer:
  - The horizon_map / per-bucket loop structure (workflow logic)
  - The adaptive confidence lookup via get_recommended_confidence
    (Decision Support's V5.8 learning-loop integration -- the EDE has no
    knowledge of this and should not need to; this is domain-specific
    orchestration, not recommendation-construction duplication)
  - The full record_recommendation() persistence call (workflow logic)

This is therefore a TARGETED removal of the duplicated lookup function
and its backing data, not a full rewrite of the enrichment loop -- the
loop's job (apply time_horizon, decide confidence, persist) stays;
only WHERE the stakeholder list comes from changes.

Run: docker exec agora-backend-1 python scripts/v615_consolidate_decision_support.py
"""
PATH = "/app/app/services/decision_support.py"

with open(PATH, "r") as f:
    content = f.read()

old = '''    # V6.1.3 Phase A/B -- narrative -> sector mapping, using REAL sector
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
            action["responsible_stakeholders"] = _lookup_responsible_stakeholders(action.get("issue", ""))'''

new = '''    # V6.1.5 -- consolidated: stakeholder resolution now delegates to the
    # Executive Decision Engine's shared resolve_responsible_stakeholders(),
    # the single authoritative implementation (previously duplicated here
    # as an exact copy under V6.1.3). Decision Support retains ONLY its
    # orchestration responsibilities below: applying time_horizon per
    # bucket, the adaptive confidence lookup (V5.8 learning-loop
    # integration, genuinely specific to Decision Support), and
    # persistence via record_recommendation().
    from app.services.executive_decision_engine import resolve_responsible_stakeholders
    for bucket, horizon in horizon_map.items():
        for action in result.get(bucket, []):
            action["time_horizon"] = horizon
            action["responsible_stakeholders"] = resolve_responsible_stakeholders(db, action.get("issue", ""))
            action.setdefault("generated_by", "Executive Decision Engine")'''

count = content.count(old)
print(f"Anchor found {count} time(s).")

if count != 1:
    print(f"Expected exactly 1 occurrence, found {count} -- aborting without changes.")
else:
    content = content.replace(old, new, 1)
    with open(PATH, "w") as f:
        f.write(content)
    print("Patched successfully: Decision Support now delegates stakeholder resolution to the Executive Decision Engine.")
