"""
NDIP Decision Support Engine v5.5
Sits AFTER intelligence interpretation.
Converts intelligence findings into structured, time-horizoned leadership actions.

SAFEGUARDS:
- Non-partisan: no party endorsement, no candidate promotion
- Evidence-based: every recommendation tied to intelligence finding
- Observational: focused on awareness, preparedness, monitoring
- Strategic: RTIFN mission-aligned only

Action categories: ACT / PREPARE / MONITOR / ESCALATE / INVESTIGATE / ENGAGE
Time horizons: Immediate (7d) / Near-Term (30d) / Strategic (90d) / Monitoring
"""
from datetime import datetime, timezone
from sqlalchemy.orm import Session

# ─── Safeguard classification ─────────────────────────────────────────────────
SAFEGUARD_NOTE = (
    "All recommendations are non-partisan, evidence-based, and focused on community "
    "awareness, institutional preparedness, and monitoring. NDIP does not support "
    "political parties, influence voting behaviour, target individuals, or promote candidates."
)

ACTION_CATEGORIES = {
    "ACT": "Take action within the recommended timeframe",
    "PREPARE": "Develop materials, frameworks, or plans",
    "MONITOR": "Observe and track — no action required yet",
    "ESCALATE": "Increase attention level or monitoring frequency",
    "INVESTIGATE": "Gather more information before acting",
    "ENGAGE": "Community or stakeholder engagement recommended",
}

# ─── Decision Support Engine ──────────────────────────────────────────────────

def generate_decision_support(db: Session, days: int) -> dict:
    """
    Generate structured decision support from intelligence findings.
    Returns time-horizoned actions across Immediate, Near-Term, Strategic, Monitoring.
    """
    from app.analytics.strategic_narratives import get_narrative_analysis
    from app.services.risk_opportunity import detect_all_risks, detect_all_opportunities
    from app.services.source_quality import get_source_quality_report
    from app.services.election_intelligence import ELECTION_DATE

    narratives = get_narrative_analysis(db, days)
    risks = detect_all_risks(db, days)
    opportunities = detect_all_opportunities(db, days)
    source_quality = get_source_quality_report(db, days)

    now = datetime.now(timezone.utc)
    days_to_election = (ELECTION_DATE - now).days

    immediate = []   # 7 days
    near_term = []   # 30 days
    strategic = []   # 90 days
    monitoring = []  # ongoing

    gov = next((n for n in narratives if n["narrative"] == "Governance"), None)
    sec = next((n for n in narratives if n["narrative"] == "Security"), None)
    econ = next((n for n in narratives if n["narrative"] == "Economy"), None)
    diaspora = next((n for n in narratives if n["narrative"] == "Global Nigerian Engagement"), None)
    elections = next((n for n in narratives if n["narrative"] == "Elections & Democracy"), None)
    media = next((n for n in narratives if n["narrative"] == "Media Representation"), None)
    investment = next((n for n in narratives if n["narrative"] == "Investment"), None)

    # ── CRITICAL RISKS → ESCALATE ─────────────────────────────────────────────
    for r in [r for r in risks if r.get("level") == "Critical"]:
        immediate.append({
            "category": "ESCALATE",
            "priority": "Critical",
            "issue": r["title"],
            "reasoning": r["detail"],
            "action": f"Escalate to senior leadership immediately. {r.get('action', 'Commission emergency review.')}",
            "expected_outcome": "Immediate leadership awareness and coordinated response.",
            "evidence": f"{r.get('evidence_count', 0)} records",
        })

    # ── GOVERNANCE ────────────────────────────────────────────────────────────
    if gov:
        sov = gov["share_of_voice"]
        momentum = gov["momentum"]
        direction = gov["momentum_direction"]
        sentiment = gov["sentiment_label"]

        if direction == "rising" and momentum > 200:
            immediate.append({
                "category": "INVESTIGATE",
                "priority": "High",
                "issue": f"Governance discourse surged {momentum:.0f}%",
                "reasoning": (
                    f"Governance coverage accelerated {momentum:.0f}% — an exceptional surge "
                    f"indicating a specific triggering event. Without understanding the driver, "
                    f"RTIFN risks responding to the wrong issue."
                ),
                "action": (
                    "Review the top 10 governance articles from the past 48 hours to identify "
                    "the specific development driving this surge. Determine whether it relates "
                    "to a ministerial action, policy announcement, or accountability event."
                ),
                "expected_outcome": "Identified trigger enables targeted, informed community response.",
                "evidence": f"{gov['count']} governance records",
            })

        if sentiment == "positive" and sov > 15:
            immediate.append({
                "category": "ENGAGE",
                "priority": "High",
                "issue": f"Governance at {sov:.0f}% share of voice with positive sentiment",
                "reasoning": (
                    "Positive governance discourse creates a favourable window for diaspora-government "
                    "engagement. This type of window typically lasts 7-14 days before news cycle shifts."
                ),
                "action": (
                    "Prepare and publish a RTIFN statement positioning the diaspora community as "
                    "a constructive stakeholder in Nigerian governance. Focus on institutional "
                    "quality and accountability — not partisan positions."
                ),
                "expected_outcome": "Established RTIFN voice in governance discourse during a peak positive window.",
                "evidence": f"{gov['count']} governance records",
            })
        elif sentiment == "negative" and sov > 15:
            near_term.append({
                "category": "PREPARE",
                "priority": "High",
                "issue": f"Negative governance sentiment at {sov:.0f}% share of voice",
                "reasoning": (
                    "Negative governance discourse may indicate declining institutional trust. "
                    "Diaspora communities need trusted interpretation of governance developments "
                    "to maintain informed engagement."
                ),
                "action": (
                    "Develop a governance situation brief for diaspora community leaders. "
                    "Summarise the key governance issues driving discourse and provide "
                    "context on institutional processes. Maintain non-partisan framing."
                ),
                "expected_outcome": "Informed diaspora community with reduced uncertainty about governance developments.",
                "evidence": f"{gov['count']} governance records",
            })

        monitoring.append({
            "category": "MONITOR",
            "priority": "Medium",
            "issue": "Governance narrative direction",
            "reasoning": "Governance is the dominant narrative. Sentiment direction is the most important leading indicator of public confidence.",
            "action": "Track governance sentiment weekly. Flag if sentiment shifts from positive to negative — this is an early warning indicator.",
            "expected_outcome": "Early detection of governance trust erosion.",
            "evidence": f"{gov['count']} records, {gov['source_count']} sources",
        })

    # ── SECURITY ──────────────────────────────────────────────────────────────
    if sec:
        sov = sec["share_of_voice"]
        direction = sec["momentum_direction"]
        momentum = sec["momentum"]
        sentiment = sec["sentiment_label"]

        if direction == "rising" and momentum > 100:
            immediate.append({
                "category": "ESCALATE",
                "priority": "High",
                "issue": f"Security discourse accelerating — up {momentum:.0f}%",
                "reasoning": (
                    "Rapid security discourse growth may indicate an emerging security situation. "
                    "Diaspora communities with family in affected areas need timely, accurate information."
                ),
                "action": (
                    f"Increase monitoring frequency for security-related narratives from weekly to "
                    f"daily over the next 30 days, due to a {momentum:.0f}% acceleration in security "
                    f"discourse. Identify geographic concentration — which states are driving the "
                    f"increase. Prepare a diaspora community security advisory within 7 days if "
                    f"incidents are concentrated in high-diaspora-origin states (Lagos, Edo, Anambra, Delta)."
                ),
                "expected_outcome": "Diaspora community informed and reassured through timely, accurate security context.",
                "evidence": f"{sec['count']} security records",
            })

        if sentiment == "negative" and sov > 12:
            near_term.append({
                "category": "PREPARE",
                "priority": "High",
                "issue": f"Negative security discourse at {sov:.0f}%",
                "reasoning": (
                    "Negative security coverage suppresses diaspora willingness to visit, invest, "
                    "and encourage return migration. Proactive community briefing prevents "
                    "disproportionate anxiety from media coverage."
                ),
                "action": (
                    "Prepare a security situation community brief for diaspora audiences. "
                    "Focus on geographic specificity — distinguish affected regions from "
                    "unaffected areas. Avoid amplifying alarmist narratives. "
                    "Provide practical guidance for community members with family in affected areas."
                ),
                "expected_outcome": "Reduced diaspora anxiety, maintained engagement levels, and RTIFN positioned as trusted information source.",
                "evidence": f"{sec['count']} security records",
            })

        monitoring.append({
            "category": "MONITOR",
            "priority": "High",
            "issue": "Security narrative — geographic concentration",
            "reasoning": "Security situations can escalate within hours. Geographic concentration in diaspora-origin states triggers disproportionate community response.",
            "action": "Monitor security discourse daily. Track geographic keywords (state names, regions). Flag if security-election narrative overlap emerges.",
            "expected_outcome": "Early warning of security developments affecting diaspora communities.",
            "evidence": f"{sec['count']} records",
        })

    # ── ECONOMY ───────────────────────────────────────────────────────────────
    if econ:
        sov = econ["share_of_voice"]
        sentiment = econ["sentiment_label"]
        direction = econ["momentum_direction"]

        if sentiment == "negative" and direction == "rising":
            near_term.append({
                "category": "ENGAGE",
                "priority": "Medium",
                "issue": f"Negative economic discourse growing ({sov:.0f}% share of voice)",
                "reasoning": (
                    "Negative economic discourse directly affects diaspora remittance behaviour "
                    "and investment decisions. Rising negative economic sentiment signals "
                    "increased household welfare concerns among community members' families."
                ),
                "action": (
                    "Assess whether diaspora community support resources are adequate for "
                    "increased economic hardship queries. Consider commissioning a diaspora "
                    "economic welfare briefing for community leaders."
                ),
                "expected_outcome": "Community preparedness for increased welfare support requests.",
                "evidence": f"{econ['count']} economy records",
            })

        monitoring.append({
            "category": "MONITOR",
            "priority": "Medium",
            "issue": "Economy — remittance and investment triggers",
            "reasoning": "Naira volatility, inflation announcements, and budget presentations drive diaspora financial decisions within 48-72 hours.",
            "action": "Monitor economy discourse daily during periods of financial announcements. Flag sentiment shifts.",
            "expected_outcome": "Timely community information during economic events.",
            "evidence": f"{econ['count']} records",
        })

    # ── DIASPORA ──────────────────────────────────────────────────────────────
    if diaspora:
        sov = diaspora["share_of_voice"]
        sentiment = diaspora["sentiment_label"]
        direction = diaspora["momentum_direction"]
        momentum = diaspora["momentum"]

        if sentiment == "positive" and sov > 25:
            immediate.append({
                "category": "ENGAGE",
                "priority": "High",
                "issue": f"Peak diaspora engagement window — {sov:.0f}% share of voice, positive sentiment",
                "reasoning": (
                    f"Global Nigerian Engagement is at {sov:.0f}% with positive sentiment "
                    f"and {momentum:.0f}% momentum growth. This peak engagement window typically "
                    f"lasts 7-14 days before narrative attention naturally shifts. "
                    f"This is the optimal period for community outreach and initiatives."
                ),
                "action": (
                    f"Launch a diaspora voter and civic awareness briefing targeting RTIFN chapters "
                    f"in the UK, Canada, and United States within the next 7 days, while Global Nigerian "
                    f"Engagement remains at {sov:.0f}% share of voice. Options include: membership drive, "
                    f"community survey, thought leadership publication, or event announcement. "
                    f"Coordinate directly with chapter leads to amplify through local networks before "
                    f"the typical 7-14 day attention window closes."
                ),
                "expected_outcome": "Maximised community reach during peak engagement window. Expected 20-40% higher response than baseline periods.",
                "evidence": f"{diaspora['count']} records, {diaspora['source_count']} sources",
            })

    # ── ELECTIONS ─────────────────────────────────────────────────────────────
    if elections:
        sov = elections["share_of_voice"]
        direction = elections["momentum_direction"]
        momentum = elections["momentum"]
        sentiment = elections["sentiment_label"]

        if direction == "rising" and momentum > 200:
            immediate.append({
                "category": "INVESTIGATE",
                "priority": "High",
                "issue": f"Electoral discourse surged {momentum:.0f}%",
                "reasoning": (
                    f"Electoral discourse accelerated {momentum:.0f}% — significantly above "
                    f"expected levels for {days_to_election} days ahead of the election. "
                    f"This likely indicates a specific electoral development requiring identification."
                ),
                "action": (
                    "Review top electoral articles from the past 72 hours. "
                    "Identify the specific INEC announcement, party development, or civic event "
                    "driving this acceleration. Assess RTIFN positioning implications."
                ),
                "expected_outcome": "Identified trigger enables informed community communications on electoral matters.",
                "evidence": f"{elections['count']} electoral records",
            })

        near_term.append({
            "category": "PREPARE",
            "priority": "High" if days_to_election < 300 else "Medium",
            "issue": f"Nigeria 2027 General Election — {days_to_election} days remaining",
            "reasoning": (
                f"With {days_to_election} days to the election, RTIFN needs an established "
                f"electoral engagement framework before campaign discourse intensifies. "
                f"Organisations that build electoral credibility early have greater influence "
                f"on community behaviour as the election approaches."
            ),
            "action": (
                "Develop an RTIFN Electoral Engagement Strategy covering: diaspora voter education, "
                "election observation framework, civic participation resources, and community "
                "briefing schedule. Maintain strictly non-partisan positioning throughout. "
                "Focus on process integrity and democratic participation — not candidate preference."
            ),
            "expected_outcome": "RTIFN established as trusted diaspora electoral information source before campaign discourse intensifies.",
            "evidence": f"{days_to_election} days to election",
        })

        monitoring.append({
            "category": "MONITOR",
            "priority": "High",
            "issue": "Electoral discourse trajectory — INEC and civic participation signals",
            "reasoning": "Electoral discourse will intensify as 2027 approaches. Early tracking enables proactive positioning.",
            "action": f"Monitor electoral discourse weekly. Escalate to daily at 180 days ahead. Track INEC announcements, party primary activity, and civil society commentary.",
            "expected_outcome": "Continuous situational awareness of electoral environment.",
            "evidence": f"{elections['count']} electoral records",
        })

    # ── MEDIA REPRESENTATION ──────────────────────────────────────────────────
    if media and media["sentiment_label"] == "negative" and media["momentum_direction"] == "rising":
        near_term.append({
            "category": "ENGAGE",
            "priority": "Medium",
            "issue": "Negative media representation discourse growing",
            "reasoning": (
                "Negative portrayal of Nigeria and Nigerians in international media affects "
                "diaspora identity, host community relationships, and Nigeria's international reputation. "
                "Rising negative representation narratives generate strong diaspora advocacy responses."
            ),
            "action": (
                "Monitor the specific international media events driving negative representation discourse. "
                "Prepare a community messaging guide that provides constructive counter-narratives. "
                "Engage with diaspora community networks to coordinate representation advocacy."
            ),
            "expected_outcome": "Coordinated community response to negative international media coverage.",
            "evidence": f"{media['count']} records",
        })

    # ── NLP QUALITY ALERT ─────────────────────────────────────────────────────
    nlp_rate = source_quality.get("processing_rate", 100)
    if nlp_rate < 80:
        monitoring.append({
            "category": "INVESTIGATE",
            "priority": "Medium",
            "issue": f"NLP processing rate at {nlp_rate}% (below 80% threshold)",
            "reasoning": "Intelligence quality depends on NLP completion. Low rates reduce confidence in all platform outputs.",
            "action": "Check backend logs. If rate does not return to 90%+ within 24 hours, restart the NLP processing pipeline.",
            "expected_outcome": "Restored intelligence quality and confidence scores.",
            "evidence": f"{nlp_rate}% NLP rate",
        })

    # ── DEFAULT MONITOR IF NOTHING URGENT ────────────────────────────────────
    if not immediate:
        monitoring.append({
            "category": "MONITOR",
            "priority": "Low",
            "issue": "Routine monitoring — no urgent conditions",
            "reasoning": "No critical or high-priority conditions detected this period.",
            "action": "Continue daily ingest monitoring. Review Leadership Pack weekly. Maintain standard intelligence cadence.",
            "expected_outcome": "Sustained intelligence quality and early warning capability.",
            "evidence": "Platform assessment",
        })

    # ── LEADERSHIP DECISION SUPPORT SUMMARY (Phase D) ─────────────────────────
    summary_bullets = _generate_decision_summary(
        immediate, near_term, strategic, monitoring,
        diaspora, gov, sec, elections, days_to_election
    )

    # Counts
    escalate_count = sum(1 for a in immediate + near_term if a["category"] == "ESCALATE")
    act_count = sum(1 for a in immediate if a["category"] in ("ACT", "ENGAGE"))

    if escalate_count > 0:
        overall_posture = "Escalated"
        posture_summary = f"{escalate_count} item(s) require immediate escalation."
    elif act_count > 0:
        overall_posture = "Active"
        posture_summary = f"{act_count} action(s) recommended this period."
    elif near_term:
        overall_posture = "Preparatory"
        posture_summary = "No immediate actions required. Preparation recommended."
    else:
        overall_posture = "Monitoring"
        posture_summary = "No urgent conditions. Routine monitoring mode."

    result = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "period_days": days,
        "overall_posture": overall_posture,
        "posture_summary": posture_summary,
        "decision_support_summary": summary_bullets,
        "immediate_actions": immediate,
        "near_term_actions": near_term,
        "strategic_actions": strategic,
        "monitoring_actions": monitoring,
        "total_actions": len(immediate) + len(near_term) + len(strategic) + len(monitoring),
        "immediate_count": len(immediate),
        "near_term_count": len(near_term),
        "safeguard_note": SAFEGUARD_NOTE,
        "action_categories": ACTION_CATEGORIES,
    }

    # V5.6: enrich every action with explicit time_horizon + confidence fields,
    # then persist to the Recommendation Effectiveness Tracker for later evaluation.
    _enrich_and_track_recommendations(db, result, days)

    return result


def _enrich_and_track_recommendations(db: Session, result: dict, days: int) -> None:
    """
    V5.6 Phase A + B: add explicit time_horizon/confidence fields to every
    recommendation (specificity requirement) and persist each one to the
    RecommendationRecord table for automated effectiveness evaluation.
    """
    try:
        from app.services.recommendation_tracker import record_recommendation
    except Exception:
        return  # tracker not available — degrade gracefully, decision support still works

    horizon_map = {
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
    # V6.1.5 -- consolidated: stakeholder resolution now delegates to the
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

            # V5.8 Phase K — consult adaptive confidence weighting before falling
            # back to the static priority-based map. This is the actual closed
            # loop: past recommendation accuracy for this category now influences
            # the confidence assigned to NEW recommendations of the same category.
            if "confidence" not in action:
                adaptive_confidence = None
                try:
                    from app.services.intelligence_learning import get_recommended_confidence
                    adaptive_confidence = get_recommended_confidence(
                        db, action.get("category", "MONITOR"), action.get("narrative")
                    )
                except Exception:
                    adaptive_confidence = None
                action["confidence"] = adaptive_confidence or confidence_map.get(action.get("priority", "Medium"), "Medium")

            # Persist for tracking — best effort, never block the response
            try:
                narrative = action.get("narrative")
                evidence_str = action.get("evidence", "")
                trigger_value = None
                try:
                    # Extract leading numeric value from evidence strings like "300 governance records"
                    digits = "".join(c for c in evidence_str.split()[0] if c.isdigit())
                    trigger_value = float(digits) if digits else None
                except (IndexError, ValueError):
                    trigger_value = None

                record_recommendation(
                    db,
                    narrative=narrative,
                    recommendation_text=action.get("action", ""),
                    category=action.get("category", "MONITOR"),
                    priority=action.get("priority", "Medium"),
                    confidence=action.get("confidence", "Medium"),
                    time_horizon=horizon,
                    supporting_evidence=action.get("reasoning") or evidence_str,
                    expected_outcome=action.get("expected_outcome"),
                    trigger_metric_name="share_of_voice",
                    trigger_metric_value=trigger_value,
                    period_days=days,
                    module="decision_support",
                )
            except Exception:
                continue


def _generate_decision_summary(immediate, near_term, strategic, monitoring,
                                 diaspora, gov, sec, elections, days_to_election) -> list:
    """
    Generate a maximum 5-bullet Leadership Decision Support Summary.
    If a board member reads only this, they know exactly what to do.
    """
    bullets = []

    # Most urgent immediate action
    if immediate:
        top = immediate[0]
        bullets.append(f"{top['category']}: {top['action'].split('.')[0]}.")

    # Diaspora engagement opportunity
    if diaspora and diaspora["sentiment_label"] == "positive" and diaspora["share_of_voice"] > 25:
        bullets.append(
            f"Launch community engagement initiative within 7 days — peak diaspora attention window is active."
        )

    # Election preparation
    if elections and days_to_election < 365:
        bullets.append(
            f"Develop RTIFN Electoral Engagement Strategy within 30 days — {days_to_election} days to 2027 election."
        )

    # Security or governance alert
    if sec and sec["sentiment_label"] == "negative" and sec["share_of_voice"] > 12:
        bullets.append(
            f"Prepare security community brief — negative security discourse at {sec['share_of_voice']:.0f}% requires proactive diaspora communications."
        )
    elif gov and gov["momentum_direction"] == "rising" and gov["momentum"] > 200:
        bullets.append(
            f"Investigate governance discourse surge ({gov['momentum']:.0f}%) — identify triggering event before communicating to community."
        )

    # Monitoring priority
    if monitoring:
        top_monitor = monitoring[0]
        bullets.append(f"MONITOR: {top_monitor['issue']}.")

    return bullets[:5]
