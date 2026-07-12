"""
NDIP Leadership Watchlist Engine v5.3
Aggregates intelligence from all modules into a unified priority list.
Every item answers: What, Why, Priority, Reason, Monitor, Action Level.
"""
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from app.analytics.strategic_narratives import get_narrative_analysis, STRATEGIC_NARRATIVES


# ─── Priority levels ──────────────────────────────────────────────────────────
PRIORITY_LEVELS = {
    "Critical": {"order": 1, "color": "red", "action": "Immediate"},
    "High": {"order": 2, "color": "orange", "action": "Within 48 hours"},
    "Medium": {"order": 3, "color": "amber", "action": "This week"},
    "Low": {"order": 4, "color": "blue", "action": "Routine monitoring"},
}

# ─── Executive action classifications ────────────────────────────────────────
ACTION_FRAMEWORK = {
    "Escalate": "Requires immediate leadership escalation and response",
    "Act": "Requires a decision or action this period",
    "Prepare": "No action yet but preparation is recommended",
    "Monitor": "Continue routine monitoring — no action required",
}


def _make_item(title, why, priority, reason, monitor_period, action_level, source, executive_action, evidence=None):
    return {
        "title": title,
        "why_it_matters": why,
        "priority": priority,
        "priority_order": PRIORITY_LEVELS[priority]["order"],
        "reason_for_inclusion": reason,
        "recommended_monitoring_period": monitor_period,
        "leadership_attention_level": PRIORITY_LEVELS[priority]["action"],
        "executive_action": executive_action,
        "action_description": ACTION_FRAMEWORK[executive_action],
        "source_module": source,
        "evidence": evidence or {},
    }


def generate_watchlist(db: Session, days: int = 7) -> dict:
    """Generate unified Leadership Watchlist from all intelligence modules."""
    from app.services.risk_opportunity import detect_all_risks, detect_all_opportunities
    from app.services.election_intelligence import generate_full_election_intelligence, ELECTION_DATE
    from app.analytics.engine import compute_all_metrics
    from app.services.source_quality import get_source_quality_report

    narratives = get_narrative_analysis(db, days)
    risks = detect_all_risks(db, days)
    opportunities = detect_all_opportunities(db, days)
    metrics = compute_all_metrics(db, max(days, 30))
    source_quality = get_source_quality_report(db, days)
    now = datetime.now(timezone.utc)
    days_to_election = (ELECTION_DATE - now).days

    items = []

    # ── CRITICAL RISKS ────────────────────────────────────────────────────────
    for r in risks:
        if r.get("level") == "Critical":
            items.append(_make_item(
                title=r["title"],
                why=r["detail"],
                priority="Critical",
                reason=f"Critical risk detected — {r.get('rationale', 'Requires immediate attention')}",
                monitor_period="Daily",
                action_level="Immediate",
                source="Risk Engine",
                executive_action="Escalate",
                evidence={"count": r.get("evidence_count", 0)},
            ))

    # ── NARRATIVE ACCELERATION ────────────────────────────────────────────────
    for nar in narratives:
        name = nar["narrative"]
        momentum = nar["momentum"]
        direction = nar["momentum_direction"]
        sentiment = nar["sentiment_label"]
        sov = nar["share_of_voice"]
        weight = STRATEGIC_NARRATIVES.get(name, {}).get("weight", 1.0)

        # High-weight narrative surging negatively
        if direction == "rising" and momentum > 200 and sentiment == "negative" and weight >= 1.2:
            items.append(_make_item(
                title=f"{name} — Negative Surge",
                why=f"{name} discourse surged {momentum:.0f}% with negative sentiment. {sov:.0f}% share of voice.",
                priority="Critical" if momentum > 400 else "High",
                reason=f"High-weight narrative ({weight}) with large negative momentum spike requires immediate attention.",
                monitor_period="Daily",
                action_level="Immediate" if momentum > 400 else "Within 48 hours",
                source="Narrative Intelligence",
                executive_action="Escalate" if momentum > 400 else "Act",
                evidence={"count": nar["count"], "momentum": momentum},
            ))
        # Major narrative surge — any sentiment
        elif direction == "rising" and momentum > 300 and weight >= 1.2:
            items.append(_make_item(
                title=f"{name} — Significant Acceleration",
                why=f"{name} coverage accelerated {momentum:.0f}% — the largest single-period increase detected. This warrants investigation into the triggering event.",
                priority="High",
                reason=f"Major acceleration in a high-weight narrative ({weight}) is a leading indicator of significant public developments.",
                monitor_period="Daily",
                action_level="Within 48 hours",
                source="Narrative Intelligence",
                executive_action="Prepare",
                evidence={"count": nar["count"], "momentum": momentum},
            ))
        # Dominant narrative positive — communications opportunity
        elif sov > 30 and sentiment == "positive" and weight >= 1.3:
            items.append(_make_item(
                title=f"{name} — High Engagement Window",
                why=f"{name} dominates discourse at {sov:.0f}% with positive sentiment. This is an exceptional communications opportunity.",
                priority="High",
                reason=f"Dominant positive narrative in NDIP's highest-weight category creates a time-sensitive communications window.",
                monitor_period="Weekly",
                action_level="Within 48 hours",
                source="Narrative Intelligence",
                executive_action="Act",
                evidence={"count": nar["count"], "sov": sov},
            ))

    # ── WARNING RISKS ─────────────────────────────────────────────────────────
    for r in risks:
        if r.get("level") == "Warning":
            items.append(_make_item(
                title=r["title"],
                why=r["detail"],
                priority="High",
                reason=r.get("rationale", "Warning-level risk requires proactive monitoring"),
                monitor_period="Weekly",
                action_level="Within 48 hours",
                source="Risk Engine",
                executive_action="Prepare",
                evidence={"count": r.get("evidence_count", 0)},
            ))

    # ── ELECTION MILESTONE ────────────────────────────────────────────────────
    if days_to_election <= 365:
        election_nar = next((n for n in narratives if n["narrative"] == "Elections & Democracy"), None)
        if election_nar:
            eov = election_nar["share_of_voice"]
            e_momentum = election_nar["momentum"]
            priority = "High" if days_to_election < 180 else "Medium"
            items.append(_make_item(
                title=f"Election 2027 — {days_to_election} Days Remaining",
                why=f"Nigeria's 2027 General Election is {days_to_election} days away. Electoral discourse is at {eov:.0f}% share of voice{f', up {e_momentum:.0f}%' if e_momentum > 50 else ''}. RTIFN's electoral positioning window is active.",
                priority=priority,
                reason=f"With {days_to_election} days to the election, establishing RTIFN's electoral intelligence and civic engagement positioning is time-sensitive.",
                monitor_period="Weekly" if days_to_election > 180 else "Daily",
                action_level=PRIORITY_LEVELS[priority]["action"],
                source="Election Intelligence",
                executive_action="Prepare" if days_to_election > 180 else "Act",
                evidence={"days_to_election": days_to_election, "electoral_sov": eov},
            ))

    # ── HIGH OPPORTUNITIES ────────────────────────────────────────────────────
    for opp in opportunities:
        if opp.get("rank") == "High":
            items.append(_make_item(
                title=opp["title"],
                why=opp["detail"],
                priority="Medium",
                reason=opp.get("rationale", "High-priority opportunity identified"),
                monitor_period="Weekly",
                action_level="This week",
                source="Opportunity Engine",
                executive_action="Act",
                evidence={"count": opp.get("evidence_count", 0)},
            ))

    # ── DATA QUALITY ALERT ────────────────────────────────────────────────────
    nlp_rate = source_quality.get("processing_rate", 100)
    if nlp_rate < 80:
        items.append(_make_item(
            title="NLP Processing Rate Below Threshold",
            why=f"NLP processing rate is {nlp_rate}% — below the 80% quality threshold. Some intelligence assessments may be based on incomplete data.",
            priority="Medium",
            reason="Intelligence quality is dependent on NLP processing completion. Low rates reduce confidence in all platform outputs.",
            monitor_period="Daily until resolved",
            action_level="This week",
            source="Data Health",
            executive_action="Monitor",
            evidence={"nlp_rate": nlp_rate},
        ))

    # ── WATCH RISKS ───────────────────────────────────────────────────────────
    watch_count = 0
    for r in risks:
        if r.get("level") == "Watch" and watch_count < 2:
            items.append(_make_item(
                title=r["title"],
                why=r["detail"],
                priority="Low",
                reason="Watch-level condition detected — routine monitoring recommended",
                monitor_period="Weekly",
                action_level="Routine monitoring",
                source="Risk Engine",
                executive_action="Monitor",
                evidence={"count": r.get("evidence_count", 0)},
            ))
            watch_count += 1

    # Sort by priority
    items.sort(key=lambda x: x["priority_order"])

    # Limit to top 10
    items = items[:10]

    # Generate summary
    critical_count = sum(1 for i in items if i["priority"] == "Critical")
    high_count = sum(1 for i in items if i["priority"] == "High")
    act_items = [i for i in items if i["executive_action"] in ("Escalate", "Act")]

    if critical_count > 0:
        summary = f"{critical_count} critical item{'s' if critical_count > 1 else ''} requiring immediate attention. {high_count} high-priority items also identified."
    elif high_count > 0:
        summary = f"{high_count} high-priority item{'s' if high_count > 1 else ''} require leadership attention this period. No critical conditions detected."
    elif act_items:
        summary = f"{len(act_items)} item{'s' if len(act_items) > 1 else ''} identified for leadership action this period. No urgent conditions detected."
    else:
        summary = "No critical or high-priority conditions detected. Platform is in routine monitoring mode."

    return {
        "generated_at": now.isoformat(),
        "period_days": days,
        "summary": summary,
        "total_items": len(items),
        "critical_count": critical_count,
        "high_count": high_count,
        "items": items,
        "action_framework": ACTION_FRAMEWORK,
    }
