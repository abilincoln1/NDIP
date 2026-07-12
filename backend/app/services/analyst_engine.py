"""
Strategic Analyst Interpretation Engine
Behaves like a professional intelligence analyst.
Every finding answers: What happened? Why does it matter? What changed? What to monitor?
"""
from datetime import datetime, timezone, timedelta
from sqlalchemy.orm import Session
from app.analytics.strategic_narratives import get_narrative_analysis, STRATEGIC_NARRATIVES


# ─── Analyst narrative assessments ───────────────────────────────────────────

NARRATIVE_STRATEGIC_IMPORTANCE = {
    "Governance": "Governance narratives shape public trust in institutions and directly influence diaspora confidence in Nigeria's political direction. High governance discourse often precedes policy changes affecting overseas Nigerians.",
    "Economy": "Economic conditions are the primary driver of diaspora remittance behaviour and return migration decisions. Rising economic concern discourse may signal reduced confidence in Nigeria's business environment.",
    "Security": "Security narratives directly affect diaspora willingness to invest, visit, and engage with Nigeria. Sustained negative security discourse can suppress diaspora economic participation.",
    "Elections & Democracy": "Electoral discourse shapes diaspora engagement cycles. Heightened electoral discussion typically indicates upcoming votes or disputes and correlates with increased diaspora advocacy activity.",
    "Global Nigerian Engagement": "This is RTIFN's core mission area. Trends in this narrative directly reflect the community's engagement with the organisation's goals and programmes.",
    "Investment": "Investment narratives indicate diaspora and international confidence in Nigeria's economic future. Rising investment discourse is a positive leading indicator for diaspora economic engagement.",
    "Infrastructure": "Infrastructure discussions reflect quality-of-life concerns that influence return migration decisions and diaspora investment in property and business.",
    "Education": "Education narratives resonate strongly with diaspora communities who frequently cite educational quality as a factor in return migration decisions.",
    "Health": "Health discourse affects diaspora decisions about family visits and return migration. Outbreaks or health system failures generate significant diaspora concern.",
    "Energy": "Energy coverage — particularly fuel prices and power supply — affects business operations and household welfare, influencing diaspora economic remittance decisions.",
    "Media Representation": "How Nigeria and its diaspora are portrayed in media affects international reputation, diaspora identity, and the receptiveness of host communities to Nigerian-origin residents.",
}

MONITORING_GUIDANCE = {
    "Governance": "Monitor over 14 days for shifts toward electoral discourse, corruption allegations, or policy announcements affecting diaspora rights.",
    "Economy": "Track daily for naira movement, inflation data releases, and unemployment figures which drive diaspora remittance decisions.",
    "Security": "Monitor daily — security situations can escalate rapidly. Watch for geographic concentration of incidents.",
    "Elections & Democracy": "Track 30 days ahead of any electoral calendar dates. Monitor tribunal proceedings and political party activity.",
    "Global Nigerian Engagement": "Monitor weekly for participation trends, advocacy campaigns, and diaspora policy developments.",
    "Investment": "Monitor monthly for FDI announcements, startup funding rounds, and business environment changes.",
    "Infrastructure": "Monitor monthly for major project announcements, contractor disputes, and completion milestones.",
    "Education": "Monitor at start of academic terms and when ASUU activity is reported.",
    "Health": "Monitor continuously for outbreak reports, WHO advisories, and hospital capacity issues.",
    "Energy": "Monitor weekly for NNPC announcements, grid stability reports, and fuel scarcity indicators.",
    "Media Representation": "Monitor for major international coverage events that may affect Nigeria's global image.",
}


def generate_narrative_assessment(narrative: dict) -> dict:
    """Delegate to differentiated interpretation engine."""
    try:
        from app.services.interpretation_engine import generate_differentiated_assessment
        return generate_differentiated_assessment(narrative)
    except Exception:
        pass
    # Fallback to original logic
    name = narrative["narrative"]
    sov = narrative["share_of_voice"]
    momentum = narrative["momentum"]
    sentiment = narrative["sentiment_label"]
    direction = narrative["momentum_direction"]
    count = narrative["count"]
    confidence = narrative["confidence_label"]
    prev_count = narrative.get("prev_count", 0)

    # What happened
    if sov >= 25:
        what_happened = f"**{name}** dominated monitored discourse, accounting for {sov:.0f}% of all analysed content — the largest single narrative category this period."
    elif sov >= 15:
        what_happened = f"**{name}** was a major theme in monitored sources, representing {sov:.0f}% of public discourse."
    elif sov >= 8:
        what_happened = f"**{name}** maintained a consistent presence, accounting for {sov:.0f}% of monitored content."
    else:
        what_happened = f"**{name}** had limited coverage, accounting for {sov:.0f}% of monitored discourse."

    # Why it matters
    why_matters = NARRATIVE_STRATEGIC_IMPORTANCE.get(name,
        f"Coverage of {name} provides insight into public priorities and may influence diaspora decision-making.")

    # What changed
    if prev_count == 0:
        what_changed = f"**{name}** emerged as a new narrative this period with no comparable prior coverage."
    elif direction == "rising" and momentum > 50:
        what_changed = f"Coverage increased significantly — up by approximately {min(momentum, 500):.0f}% compared to the previous period."
    elif direction == "rising" and momentum > 10:
        what_changed = f"Coverage grew moderately, with a {momentum:.0f}% increase from the previous period."
    elif direction == "falling" and momentum < -20:
        what_changed = f"Coverage declined by {abs(momentum):.0f}% compared to the previous period — this narrative is losing public attention."
    else:
        what_changed = "Coverage remained broadly stable compared to the previous period."

    # Sentiment context
    if sentiment == "positive":
        sentiment_text = "The tone of coverage was broadly positive, suggesting constructive public discourse."
    elif sentiment == "negative":
        sentiment_text = "The tone of coverage was predominantly negative — critical or concerned discourse is dominant in this narrative."
    else:
        sentiment_text = "Coverage was largely neutral in tone, with balanced reporting across positive and negative angles."

    # Leadership considerations
    if sentiment == "negative" and direction == "rising":
        leadership = f"Rising negative coverage of **{name}** warrants leadership attention. Consider whether a public response or communications strategy is needed."
    elif direction == "rising" and sentiment == "positive":
        leadership = f"Growing positive discourse around **{name}** presents a communications opportunity. Leadership can amplify this narrative through official channels."
    elif sov > 20:
        leadership = f"As the dominant narrative, **{name}** should be a primary focus of leadership communications this period."
    else:
        leadership = f"Monitor **{name}** trends over the coming weeks to identify emerging opportunities or concerns."

    return {
        "narrative": name,
        "what_happened": what_happened,
        "why_it_matters": why_matters,
        "what_changed": what_changed,
        "sentiment_context": sentiment_text,
        "leadership_considerations": leadership,
        "monitoring_priority": MONITORING_GUIDANCE.get(name, f"Continue monitoring {name.lower()} trends."),
        "confidence_label": confidence,
        "share_of_voice": sov,
        "momentum": momentum,
        "momentum_direction": direction,
        "sentiment_label": sentiment,
        "count": count,
        "strategic_importance": "High" if STRATEGIC_NARRATIVES.get(name, {}).get("weight", 0) >= 1.2 else "Medium",
    }


def generate_comparative_intelligence(narratives: list[dict]) -> list[str]:
    """Delegate to differentiated interpretation engine."""
    try:
        from app.services.interpretation_engine import generate_comparative_intelligence as _gci
        return _gci(narratives)
    except Exception:
        pass
    # Fallback original:
    """Generate analyst-style comparative statements."""
    if len(narratives) < 2:
        return []

    comparisons = []
    top = narratives[0]

    for other in narratives[1:4]:
        if other["count"] == 0:
            continue
        ratio = round(top["count"] / max(other["count"], 1), 1)
        if ratio >= 3:
            comparisons.append(
                f"**{top['narrative']}** generated {ratio}x more discussion than **{other['narrative']}**, making it the overwhelmingly dominant narrative this period."
            )
        elif ratio >= 2:
            comparisons.append(
                f"**{top['narrative']}** generated twice as much discussion as **{other['narrative']}**."
            )
        elif ratio >= 1.5:
            comparisons.append(
                f"**{top['narrative']}** attracted {ratio}x more coverage than **{other['narrative']}**."
            )

    # Rising vs falling
    rising = [n for n in narratives if n["momentum_direction"] == "rising" and n["momentum"] > 20]
    falling = [n for n in narratives if n["momentum_direction"] == "falling" and n["momentum"] < -20]
    if rising:
        comparisons.append(
            f"The fastest growing narrative is **{rising[0]['narrative']}**, which saw coverage increase significantly compared to the previous period."
        )
    if falling:
        comparisons.append(
            f"**{falling[0]['narrative']}** saw the largest decline in coverage, potentially indicating reduced public salience."
        )

    return comparisons[:4]


def generate_national_context(narratives: list[dict], diaspora_name: str = "Global Nigerian Engagement") -> str:
    """
    Connect diaspora narratives to national developments.
    Instead of 'Diaspora engagement increased', explain WHY in national context.
    """
    diaspora = next((n for n in narratives if n["narrative"] == diaspora_name), None)
    governance = next((n for n in narratives if n["narrative"] == "Governance"), None)
    economy = next((n for n in narratives if n["narrative"] == "Economy"), None)
    security = next((n for n in narratives if n["narrative"] == "Security"), None)

    if not diaspora:
        return ""

    context_parts = []

    if diaspora["momentum_direction"] == "rising":
        context_parts.append(
            f"Global Nigerian Engagement discussions increased during this period"
        )
    else:
        context_parts.append(
            f"Global Nigerian Engagement discussions remained active during this period"
        )

    # Connect to national narratives
    drivers = []
    if governance and governance["share_of_voice"] > 15:
        drivers.append(f"heightened governance discourse ({governance['share_of_voice']:.0f}% share of voice)")
    if economy and economy["share_of_voice"] > 10:
        drivers.append(f"significant economic discussion ({economy['share_of_voice']:.0f}% share of voice)")
    if security and security["share_of_voice"] > 10:
        drivers.append(f"elevated security coverage ({security['share_of_voice']:.0f}% share of voice)")

    if drivers:
        context_parts.append(
            f", coinciding with {' and '.join(drivers)}. This suggests overseas Nigerian communities are actively tracking and responding to broader national developments."
        )
    else:
        context_parts.append(
            ". This reflects sustained community interest in diaspora affairs independent of specific national events."
        )

    return "".join(context_parts)


def generate_outlook(narratives: list[dict], days: int, risks: list, opportunities: list) -> dict:
    """Delegate to outlook engine."""
    try:
        from app.services.interpretation_engine import generate_outlook_engine
        return generate_outlook_engine(narratives, days, risks, opportunities)
    except Exception:
        pass
    # Fallback:
    """Generate 7/14/30 day outlook."""
    high_risks = [r for r in risks if r.get("level") in ("Critical", "Warning")]
    high_opps = [o for o in opportunities if o.get("rank") == "High"]

    rising_narratives = [n for n in narratives if n["momentum_direction"] == "rising"]
    negative_rising = [n for n in rising_narratives if n["sentiment_label"] == "negative"]

    def _outlook_text(horizon_days: int) -> str:
        if negative_rising:
            return (
                f"Over the next {horizon_days} days, monitor **{negative_rising[0]['narrative']}** closely — "
                f"negative discourse is rising and may intensify. "
                f"{'Immediate communications review recommended.' if horizon_days <= 7 else 'Prepare contingency communications strategy.'}"
            )
        elif high_risks:
            return (
                f"The {horizon_days}-day outlook is cautiously stable. "
                f"{high_risks[0]['title']} remains a priority concern requiring active monitoring."
            )
        elif high_opps:
            return (
                f"The {horizon_days}-day outlook is positive. "
                f"Current momentum in **{rising_narratives[0]['narrative'] if rising_narratives else 'key narratives'}** "
                f"presents communications and engagement opportunities. "
                f"{'Act this week.' if horizon_days <= 7 else 'Plan initiatives for this period.'}"
            )
        else:
            return (
                f"The {horizon_days}-day outlook is broadly stable. "
                f"Continue routine monitoring and maintain community engagement activities."
            )

    return {
        "7_day": _outlook_text(7),
        "14_day": _outlook_text(14),
        "30_day": _outlook_text(30),
        "monitoring_priorities": [n["narrative"] for n in rising_narratives[:3]] or ["Continue routine monitoring"],
        "emerging_concerns": [n["narrative"] for n in negative_rising[:2]],
        "emerging_opportunities": [o["title"] for o in high_opps[:2]],
    }


def get_full_analyst_brief(db: Session, days: int = 7) -> dict:
    """Master function — returns full analyst-grade intelligence package."""
    from app.services.narrative_intelligence import generate_situation_room, generate_brief
    from app.services.risk_opportunity import detect_all_risks, detect_all_opportunities

    narratives = get_narrative_analysis(db, days)
    risks = detect_all_risks(db, days)
    opportunities = detect_all_opportunities(db, days)

    # Full narrative assessments
    assessments = [generate_narrative_assessment(n) for n in narratives[:8]]

    # Comparative intelligence
    comparisons = generate_comparative_intelligence(narratives)

    # National context
    national_context = generate_national_context(narratives)

    # Diaspora narratives
    diaspora = next((n for n in narratives if n["narrative"] == "Global Nigerian Engagement"), None)
    national_narratives = [n for n in narratives if n["narrative"] in (
        "Economy", "Security", "Governance", "Elections & Democracy",
        "Infrastructure", "Energy", "Education", "Health"
    )]
    emerging_narratives = [n for n in narratives if n["momentum_direction"] == "rising" and n["momentum"] > 100 and n.get("prev_count", 0) > 3]

    # Outlook
    outlook = generate_outlook(narratives, days, risks, opportunities)

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "period_days": days,
        "narrative_assessments": assessments,
        "comparative_intelligence": comparisons,
        "national_context": national_context,
        "diaspora_narrative": diaspora,
        "national_narratives": national_narratives,
        "emerging_narratives": emerging_narratives,
        "risks": risks,
        "opportunities": opportunities,
        "outlook": outlook,
    }
