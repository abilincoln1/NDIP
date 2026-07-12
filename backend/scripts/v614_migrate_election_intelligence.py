"""
NDIP V6.1.4 Phase B -- migrate Election Intelligence's leadership_actions
(3 hand-built dicts) to call the Executive Decision Engine. Threads `db`
through generate_election_implications_engine()'s signature and its one
call site (confirmed live: exactly one caller).

diaspora_actions (a static list, not narrative-triggered) and
escalation_alerts (a different, alert-specific shape) are intentionally
left as-is -- they are not the recommendation pattern this consolidation
targets (no category/priority/action/reasoning quadruple), consistent
with the audit's finding that only genuinely recommendation-shaped logic
should migrate.

Run: docker exec agora-backend-1 python scripts/v614_migrate_election_intelligence.py
"""
PATH = "/app/app/services/election_intelligence.py"

with open(PATH, "r") as f:
    content = f.read()

patches_applied = []
patches_skipped = []


def apply_patch(name, old, new):
    global content
    if old not in content:
        patches_skipped.append(name)
        return
    content = content.replace(old, new, 1)
    patches_applied.append(name)


# Thread db through the function signature
apply_patch(
    "Function signature -- add db parameter",
    '''def generate_election_implications_engine(elections: dict, phase: dict, days_to_election: int,
                                           narratives: list, risks: list, opportunities: list) -> dict:''',
    '''def generate_election_implications_engine(elections: dict, phase: dict, days_to_election: int,
                                           narratives: list, risks: list, opportunities: list, db: Session = None) -> dict:''',
)

# Migrate the 3 leadership_actions appends
apply_patch(
    "Commission Electoral Engagement Strategy action",
    '''    leadership_actions = []
    if days_to_election > 180:
        leadership_actions.append({
            "action": "Commission Electoral Engagement Strategy",
            "priority": "Prepare",
            "timing": "This month",
            "detail": "Develop RTIFN's electoral observation and civic engagement framework before campaign discourse begins.",
        })''',
    '''    leadership_actions = []
    if days_to_election > 180:
        if db is not None:
            from app.services.executive_decision_engine import build_recommendation
            leadership_actions.append(build_recommendation(
                db,
                category="PREPARE", priority="Medium",
                issue="Electoral discourse remains below expected pre-campaign levels",
                action="Develop RTIFN's electoral observation and civic engagement framework before campaign discourse begins.",
                reasoning="Early-stage preparation, well ahead of the election, allows positioning before discourse becomes contested.",
                expected_outcome="RTIFN establishes credibility before the electoral discourse space becomes competitive.",
                evidence=f"{days_to_election} days to election",
                time_horizon="This month",
            ))
        else:
            leadership_actions.append({
                "action": "Commission Electoral Engagement Strategy",
                "priority": "Prepare",
                "timing": "This month",
                "detail": "Develop RTIFN's electoral observation and civic engagement framework before campaign discourse begins.",
            })''',
)

apply_patch(
    "Monitor Electoral Acceleration action",
    '''    if direction == "rising" and momentum > 100:
        leadership_actions.append({
            "action": "Monitor Electoral Acceleration",
            "priority": "Act",
            "timing": "Daily for next 7 days",
            "detail": f"Electoral discourse surged {momentum:.0f}%. Identify the triggering event and assess implications for RTIFN positioning.",
        })''',
    '''    if direction == "rising" and momentum > 100:
        if db is not None:
            from app.services.executive_decision_engine import build_recommendation
            leadership_actions.append(build_recommendation(
                db,
                category="ESCALATE", priority="High",
                issue=f"Electoral discourse surged {momentum:.0f}%",
                action="Identify the triggering event and assess implications for RTIFN positioning.",
                reasoning=f"Electoral discourse accelerated {momentum:.0f}% -- an exceptional surge that may indicate a significant electoral development.",
                expected_outcome="Identified trigger enables targeted, informed RTIFN response.",
                evidence=f"{momentum:.0f}% momentum increase in electoral discourse",
                time_horizon="7 days",
            ))
        else:
            leadership_actions.append({
                "action": "Monitor Electoral Acceleration",
                "priority": "Act",
                "timing": "Daily for next 7 days",
                "detail": f"Electoral discourse surged {momentum:.0f}%. Identify the triggering event and assess implications for RTIFN positioning.",
            })''',
)

apply_patch(
    "Establish Election Intelligence Baseline action",
    '''    leadership_actions.append({
        "action": "Establish Election Intelligence Baseline",
        "priority": "Monitor",
        "timing": "Ongoing",
        "detail": "Continue daily monitoring of electoral discourse. Establish monthly benchmarks for trajectory tracking.",
    })''',
    '''    if db is not None:
        from app.services.executive_decision_engine import build_recommendation
        leadership_actions.append(build_recommendation(
            db,
            category="MONITOR", priority="Medium",
            issue="Elections & Democracy discourse baseline tracking",
            action="Continue daily monitoring of electoral discourse. Establish monthly benchmarks for trajectory tracking.",
            reasoning="Sustained monitoring establishes the baseline needed to detect future acceleration or deceleration.",
            expected_outcome="Reliable trajectory tracking ahead of the 2027 election cycle.",
            evidence=f"Current share of voice: {sov:.0f}%",
            time_horizon="Ongoing",
        ))
    else:
        leadership_actions.append({
            "action": "Establish Election Intelligence Baseline",
            "priority": "Monitor",
            "timing": "Ongoing",
            "detail": "Continue daily monitoring of electoral discourse. Establish monthly benchmarks for trajectory tracking.",
        })''',
)

# Update the one call site to pass db through
apply_patch(
    "Call site -- pass db through",
    '''    election_implications = generate_election_implications_engine(
        elections, phase, days_to_election, narratives, risks, opportunities
    )''',
    '''    election_implications = generate_election_implications_engine(
        elections, phase, days_to_election, narratives, risks, opportunities, db=db
    )''',
)

with open(PATH, "w") as f:
    f.write(content)

print(f"Applied: {len(patches_applied)}")
for p in patches_applied:
    print(f"  [OK] {p}")
print(f"Skipped: {len(patches_skipped)}")
for p in patches_skipped:
    print(f"  [SKIPPED] {p}")
