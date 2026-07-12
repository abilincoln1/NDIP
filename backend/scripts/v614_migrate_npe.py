"""
NDIP V6.1.4 Phase B -- migrate National Pulse Executive's 5 hand-built
recommendation dicts to call the Executive Decision Engine's
build_recommendation(), preserving every module-specific trigger
condition and action/reasoning text exactly as-is (per "preserve
existing functionality") -- only the dict CONSTRUCTION is delegated.

Anchors confirmed live via sed extraction this session.

Run: docker exec agora-backend-1 python scripts/v614_migrate_npe.py
"""
PATH = "/app/app/services/national_pulse_executive.py"

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


apply_patch(
    "Diaspora engagement action",
    '''        actions.append({
            "action": "Launch Community Engagement Campaign",
            "priority": "Act",
            "issue": f"Global Nigerian Engagement at {diaspora['share_of_voice']:.0f}% with positive sentiment",
            "reasoning": "High positive diaspora engagement creates a 1-2 week communications window before narrative attention shifts.",
            "recommended_action": "Issue a public statement, content series, or membership drive capitalising on current peak diaspora engagement.",
            "expected_outcome": "Increased RTIFN visibility and community engagement during a peak attention period.",
        })''',
    '''        from app.services.executive_decision_engine import build_recommendation
        actions.append(build_recommendation(
            db,
            category="ENGAGE", priority="High",
            issue=f"Global Nigerian Engagement at {diaspora['share_of_voice']:.0f}% with positive sentiment",
            action="Issue a public statement, content series, or membership drive capitalising on current peak diaspora engagement.",
            reasoning="High positive diaspora engagement creates a 1-2 week communications window before narrative attention shifts.",
            expected_outcome="Increased RTIFN visibility and community engagement during a peak attention period.",
            evidence=f"{diaspora['count']} diaspora records" if diaspora.get("count") else "Diaspora engagement data",
            time_horizon="7 days",
        ))''',
)

apply_patch(
    "Governance positive action",
    '''        actions.append({
            "action": "Amplify Positive Governance Narrative",
            "priority": "Act",
            "issue": f"Governance at {gov['share_of_voice']:.0f}% with positive sentiment",
            "reasoning": "Positive governance discourse creates a favourable window for diaspora-government engagement.",
            "recommended_action": "Publish RTIFN commentary positioning diaspora community as constructive governance stakeholder.",
            "expected_outcome": "Strengthened RTIFN positioning ahead of 2027 election cycle.",
        })''',
    '''        from app.services.executive_decision_engine import build_recommendation
        actions.append(build_recommendation(
            db,
            category="ENGAGE", priority="High",
            issue=f"Governance at {gov['share_of_voice']:.0f}% with positive sentiment",
            action="Publish RTIFN commentary positioning diaspora community as constructive governance stakeholder.",
            reasoning="Positive governance discourse creates a favourable window for diaspora-government engagement.",
            expected_outcome="Strengthened RTIFN positioning ahead of 2027 election cycle.",
            evidence=f"{gov['count']} governance records" if gov.get("count") else "Governance discourse data",
            time_horizon="7 days",
        ))''',
)

apply_patch(
    "Security briefing action",
    '''        actions.append({
            "action": "Prepare Security Briefing",
            "priority": "Prepare",
            "issue": f"Security at {sec['share_of_voice']:.0f}% with negative sentiment",
            "reasoning": "Negative security discourse suppresses diaspora engagement and investment confidence.",
            "recommended_action": "Prepare community briefing note. Monitor geographic concentration. Avoid amplifying negative narratives.",
            "expected_outcome": "Reduced community anxiety and maintained engagement levels.",
        })''',
    '''        from app.services.executive_decision_engine import build_recommendation
        actions.append(build_recommendation(
            db,
            category="PREPARE", priority="High",
            issue=f"Security at {sec['share_of_voice']:.0f}% with negative sentiment",
            action="Prepare community briefing note. Monitor geographic concentration. Avoid amplifying negative narratives.",
            reasoning="Negative security discourse suppresses diaspora engagement and investment confidence.",
            expected_outcome="Reduced community anxiety and maintained engagement levels.",
            evidence=f"{sec['count']} security records" if sec.get("count") else "Security discourse data",
            time_horizon="30 days",
        ))''',
)

apply_patch(
    "Risk-based action",
    '''        actions.append({
            "action": f"Address Risk: {r['title']}",
            "priority": "Prepare",
            "issue": r["title"],
            "reasoning": r["detail"][:120],
            "recommended_action": r.get("action", "Monitor and prepare appropriate response."),
            "expected_outcome": "Reduced risk exposure and improved situational awareness.",
        })''',
    '''        from app.services.executive_decision_engine import build_recommendation
        actions.append(build_recommendation(
            db,
            category="PREPARE", priority="High",
            issue=r["title"],
            action=r.get("action", "Monitor and prepare appropriate response."),
            reasoning=r["detail"][:120],
            expected_outcome="Reduced risk exposure and improved situational awareness.",
            evidence=f"{r.get('evidence_count', 0)} records",
            time_horizon="30 days",
        ))''',
)

apply_patch(
    "Default monitoring action",
    '''        actions.append({
            "action": "Maintain Monitoring Cadence",
            "priority": "Monitor",
            "issue": "Stable environment — no immediate triggers",
            "reasoning": "No elevated concerns detected this period.",
            "recommended_action": "Continue daily monitoring. Review Leadership Pack weekly.",
            "expected_outcome": "Sustained intelligence quality and early warning capability.",
        })''',
    '''        from app.services.executive_decision_engine import build_recommendation
        actions.append(build_recommendation(
            db,
            category="MONITOR", priority="Medium",
            issue="Stable environment — no immediate triggers",
            action="Continue daily monitoring. Review Leadership Pack weekly.",
            reasoning="No elevated concerns detected this period.",
            expected_outcome="Sustained intelligence quality and early warning capability.",
            evidence="No elevated narrative triggers this period",
            time_horizon="Ongoing",
        ))''',
)

with open(PATH, "w") as f:
    f.write(content)

print(f"Applied: {len(patches_applied)}")
for p in patches_applied:
    print(f"  [OK] {p}")
print(f"Skipped: {len(patches_skipped)}")
for p in patches_skipped:
    print(f"  [SKIPPED] {p}")
