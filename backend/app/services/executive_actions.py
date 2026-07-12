"""
NDIP Executive Actions Engine v5.4
Converts intelligence findings into specific recommended leadership actions.
Every action includes: Issue, Reasoning, Recommended Action, Expected Outcome, Priority.
"""
from datetime import datetime, timezone
from sqlalchemy.orm import Session


ACTION_PRIORITIES = {
    "Escalate": 1,
    "Act": 2,
    "Prepare": 3,
    "Monitor": 4,
}


def generate_executive_actions(db: Session, days: int) -> dict:
    from app.analytics.strategic_narratives import get_narrative_analysis
    from app.services.risk_opportunity import detect_all_risks, detect_all_opportunities
    from app.analytics.engine import compute_all_metrics

    narratives = get_narrative_analysis(db, days)
    risks = detect_all_risks(db, days)
    opportunities = detect_all_opportunities(db, days)
    metrics = compute_all_metrics(db, max(days, 30))

    actions = []

    # ── From Critical/Warning Risks ───────────────────────────────────────────
    for r in risks:
        level = r.get("level", "")
        if level == "Critical":
            actions.append({
                "category": "Escalate",
                "priority_order": 1,
                "title": f"Escalate: {r['title']}",
                "issue": r["title"],
                "reasoning": r["detail"],
                "recommended_action": r.get("action", "Convene emergency leadership review immediately."),
                "expected_outcome": "Immediate leadership awareness and coordinated response to critical risk.",
                "confidence": r.get("confidence_label", "High"),
                "source": "Risk Engine",
                "evidence_count": r.get("evidence_count", 0),
            })
        elif level == "Warning":
            actions.append({
                "category": "Act",
                "priority_order": 2,
                "title": f"Act on: {r['title']}",
                "issue": r["title"],
                "reasoning": r["detail"],
                "recommended_action": r.get("action", "Initiate response protocol within 48 hours."),
                "expected_outcome": "Proactive risk mitigation before escalation occurs.",
                "confidence": r.get("confidence_label", "High"),
                "source": "Risk Engine",
                "evidence_count": r.get("evidence_count", 0),
            })

    # ── From Narrative Intelligence ───────────────────────────────────────────
    gov = next((n for n in narratives if n["narrative"] == "Governance"), None)
    diaspora = next((n for n in narratives if n["narrative"] == "Global Nigerian Engagement"), None)
    sec = next((n for n in narratives if n["narrative"] == "Security"), None)
    elections = next((n for n in narratives if n["narrative"] == "Elections & Democracy"), None)

    if diaspora and diaspora["sentiment_label"] == "positive" and diaspora["share_of_voice"] > 25:
        actions.append({
            "category": "Act",
            "priority_order": 2,
            "title": "Launch Diaspora Engagement Campaign",
            "issue": f"Global Nigerian Engagement at {diaspora['share_of_voice']:.0f}% share of voice — peak positive engagement window detected",
            "reasoning": (
                f"Diaspora engagement discourse is at {diaspora['share_of_voice']:.0f}% with positive sentiment "
                f"and {diaspora['momentum']:.0f}% momentum growth. This combination creates a 7-14 day window "
                f"of elevated community receptivity before narrative attention naturally shifts."
            ),
            "recommended_action": (
                "Issue a community-facing communications piece within the next 48-72 hours. "
                "Consider a membership drive, community survey, or thought leadership publication. "
                "Coordinate with chapter leads to amplify through local networks."
            ),
            "expected_outcome": "Maximised reach and engagement during peak diaspora attention window. Expected 20-40% higher engagement response than baseline periods.",
            "confidence": "High",
            "source": "Narrative Intelligence",
            "evidence_count": diaspora.get("count", 0),
        })

    if gov and gov["sentiment_label"] == "positive" and gov["share_of_voice"] > 15:
        actions.append({
            "category": "Act",
            "priority_order": 2,
            "title": "Position on Governance Narrative",
            "issue": f"Governance dominant at {gov['share_of_voice']:.0f}% — positive sentiment opportunity",
            "reasoning": (
                f"Governance attracts {gov['share_of_voice']:.0f}% of public discourse with positive sentiment. "
                f"This is a window to position RTIFN's voice on governance issues before the 2027 election "
                f"discourse intensifies and narrative space becomes more contested."
            ),
            "recommended_action": (
                "Publish a RTIFN statement on Nigerian governance standards and diaspora community expectations. "
                "Frame the diaspora community as a constructive stakeholder in national governance. "
                "Avoid partisan framing — focus on institutional quality and democratic accountability."
            ),
            "expected_outcome": "Established RTIFN positioning on governance ahead of election cycle. Strengthened credibility as civic voice.",
            "confidence": "High",
            "source": "Narrative Intelligence",
            "evidence_count": gov.get("count", 0),
        })

    if elections and elections["momentum"] > 200:
        actions.append({
            "category": "Prepare",
            "priority_order": 3,
            "title": "Activate Electoral Engagement Framework",
            "issue": f"Electoral discourse surged {elections['momentum']:.0f}% — accelerating ahead of 2027 election",
            "reasoning": (
                f"Elections & Democracy discourse grew {elections['momentum']:.0f}% this period. "
                f"With 230+ days to the election, this early acceleration indicates the civic space is forming. "
                f"Organisations that establish electoral credibility early have disproportionate influence on the discourse environment."
            ),
            "recommended_action": (
                "Commission an RTIFN Electoral Engagement strategy. "
                "Establish observation and monitoring framework for the 2027 election cycle. "
                "Begin producing regular election intelligence briefings for community leadership. "
                "Do not take partisan positions — frame as civic observation and diaspora engagement."
            ),
            "expected_outcome": "RTIFN established as the primary diaspora voice on electoral matters before campaign discourse intensifies.",
            "confidence": "Medium",
            "source": "Election Intelligence",
            "evidence_count": elections.get("count", 0),
        })

    if sec and sec["sentiment_label"] == "negative" and sec["share_of_voice"] > 12:
        actions.append({
            "category": "Prepare",
            "priority_order": 3,
            "title": "Prepare Security Community Brief",
            "issue": f"Security discourse at {sec['share_of_voice']:.0f}% with negative sentiment",
            "reasoning": (
                f"Negative security coverage ({sec['share_of_voice']:.0f}% share of voice) increases diaspora "
                f"anxiety about family welfare in Nigeria. Organisations that provide trusted security context "
                f"build community trust during periods of elevated concern."
            ),
            "recommended_action": (
                "Prepare a community security situation brief for diaspora audiences. "
                "Focus on geographic specificity — identify which states/regions are affected. "
                "Provide practical guidance for community members with family in affected areas. "
                "Avoid amplifying alarmist narratives."
            ),
            "expected_outcome": "Reduced community anxiety through authoritative information. Strengthened RTIFN role as trusted community information source.",
            "confidence": "Medium",
            "source": "Narrative Intelligence",
            "evidence_count": sec.get("count", 0),
        })

    # ── From High Opportunities ───────────────────────────────────────────────
    for opp in [o for o in opportunities if o.get("rank") == "High"][:2]:
        actions.append({
            "category": "Act",
            "priority_order": 2,
            "title": opp["title"],
            "issue": opp["detail"],
            "reasoning": opp.get("rationale", "High-priority opportunity identified by intelligence engine."),
            "recommended_action": opp.get("action", "Develop and execute engagement strategy this period."),
            "expected_outcome": "Capitalised strategic opportunity within optimal timing window.",
            "confidence": opp.get("confidence_label", "High"),
            "source": "Opportunity Engine",
            "evidence_count": opp.get("evidence_count", 0),
        })

    # Default monitor action
    if not [a for a in actions if a["category"] in ("Escalate", "Act")]:
        actions.append({
            "category": "Monitor",
            "priority_order": 4,
            "title": "Maintain Standard Intelligence Monitoring",
            "issue": "No urgent conditions detected",
            "reasoning": "Current discourse environment is stable with no immediate action triggers.",
            "recommended_action": "Continue daily ingest monitoring. Review Leadership Pack weekly. Pre-warm cache after 6am ingest.",
            "expected_outcome": "Sustained intelligence quality and early warning capability.",
            "confidence": "High",
            "source": "Platform",
            "evidence_count": 0,
        })

    # Sort and limit
    actions.sort(key=lambda x: x["priority_order"])
    actions = actions[:8]

    escalate = [a for a in actions if a["category"] == "Escalate"]
    act = [a for a in actions if a["category"] == "Act"]
    prepare = [a for a in actions if a["category"] == "Prepare"]
    monitor = [a for a in actions if a["category"] == "Monitor"]

    summary = ""
    if escalate:
        summary = f"{len(escalate)} item(s) require immediate escalation. Leadership must be briefed today."
    elif act:
        summary = f"{len(act)} action(s) recommended for this period. No critical escalation required."
    elif prepare:
        summary = f"No immediate actions required. {len(prepare)} item(s) warrant preparation this week."
    else:
        summary = "No urgent actions required. Platform in routine monitoring mode."

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "period_days": days,
        "summary": summary,
        "total_actions": len(actions),
        "escalate_count": len(escalate),
        "act_count": len(act),
        "prepare_count": len(prepare),
        "monitor_count": len(monitor),
        "actions": actions,
    }
