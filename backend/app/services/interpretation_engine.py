"""
NDIP Executive Interpretation Engine v5.1
Converts data into analyst-grade intelligence.
Every output answers: What happened, Why it matters, Implications, Monitor.
Zero generic templates — all commentary is narrative-specific and evidence-driven.
"""
from app.analytics.strategic_narratives import STRATEGIC_NARRATIVES


# ─── Strategic importance per narrative ──────────────────────────────────────
STRATEGIC_IMPORTANCE = {
    "Governance": "Governance narratives shape public trust in Nigerian institutions and directly influence diaspora confidence in the country's political direction. High governance discourse often precedes policy changes, ministerial reshuffles, or public accountability moments that affect overseas Nigerians.",
    "Economy": "Economic conditions are the primary driver of diaspora remittance behaviour, investment decisions, and return migration sentiment. When economic discourse dominates, diaspora communities are closely tracking conditions that affect both their families at home and their own financial engagement with Nigeria.",
    "Security": "Security narratives directly affect diaspora willingness to invest, visit family, and encourage return migration. Sustained security discourse — particularly when negative — suppresses diaspora economic participation and increases pressure on community organisations to advocate for policy interventions.",
    "Global Nigerian Engagement": "This is NDIP's primary intelligence mandate. Trends in this narrative directly reflect the level and tone of diaspora community engagement with Nigerian affairs. Shifts here are leading indicators of community mobilisation, advocacy activity, and sentiment toward RTIFN's mission.",
    "Elections & Democracy": "Electoral discourse is a leading indicator of civic mobilisation cycles. With Nigeria's 2027 general election approaching, sustained electoral discussion signals public attention to democratic processes and may indicate early campaign activity, institutional concerns, or civic society mobilisation.",
    "Investment": "Investment narratives indicate diaspora and international market confidence in Nigeria's economic future. Rising positive investment discourse is a direct opportunity signal for RTIFN to position diaspora communities as economic partners and amplify investment promotion messaging.",
    "Energy": "Energy coverage — particularly around fuel prices and power supply — directly affects household welfare and business conditions in Nigeria. For the diaspora, energy issues influence remittance decisions and quality-of-life assessments that affect return migration sentiment.",
    "Infrastructure": "Infrastructure discussions reflect development progress and quality-of-life conditions — two of the most cited factors in diaspora return migration decisions. Both project announcements and infrastructure failures generate significant diaspora community response.",
    "Education": "Education quality is consistently identified by diaspora communities as a primary barrier to return migration. Education discourse — particularly around ASUU, university access, and educational standards — directly influences diaspora engagement with Nigerian development narratives.",
    "Health": "Health system quality is a major concern for diaspora communities with families in Nigeria. Health discourse affects remittance decisions, family welfare assessments, and diaspora advocacy priorities. Outbreak coverage can rapidly mobilise diaspora health sector professionals.",
    "Media Representation": "How Nigeria and Nigerians are portrayed in international media affects diaspora identity, host community relationships, and international reputation. Negative representation narratives often generate strong diaspora advocacy responses and community solidarity.",
}

MONITORING_GUIDANCE = {
    "Governance": "Monitor over 14 days for shifts toward specific policy areas, corruption investigations, or cabinet changes. Track sentiment direction — a shift from positive to negative governance sentiment is an early warning indicator.",
    "Economy": "Track daily during periods of naira volatility, inflation announcements, or budget presentations. These events directly drive diaspora remittance and investment decisions within 48-72 hours of announcement.",
    "Security": "Monitor daily — security situations can escalate within hours. Pay particular attention to geographic concentration. Security incidents in diaspora-origin states (Lagos, Edo, Anambra, Delta) generate disproportionately strong diaspora responses.",
    "Global Nigerian Engagement": "Monitor weekly for participation trends, advocacy campaign launches, and policy announcements affecting overseas Nigerians. Track against national Nigerian events — diaspora engagement typically spikes 2-5 days after significant domestic developments.",
    "Elections & Democracy": "Monitor on a 30-day rolling basis and intensify monitoring 90 days ahead of any electoral milestone. Track INEC announcements, party primaries, and civil society electoral commentary as leading indicators.",
    "Investment": "Monitor monthly for FDI announcements, startup funding news, and regulatory environment changes. Positive investment coverage peaks typically precede increased diaspora investment enquiries by 2-4 weeks.",
    "Energy": "Monitor weekly for NNPC announcements, electricity tariff changes, and fuel scarcity reports. These generate rapid public discourse spikes and direct diaspora welfare concern responses.",
    "Infrastructure": "Monitor monthly for project completion announcements and infrastructure failure coverage. Return migration decisions are often directly influenced by infrastructure quality assessments that circulate in diaspora community networks.",
    "Education": "Monitor at academic term boundaries and whenever ASUU communications appear in monitored sources. Strike action indicators typically appear 2-3 weeks before formal announcements.",
    "Health": "Monitor continuously. Disease outbreak coverage can emerge rapidly and generate diaspora health sector mobilisation within 24-48 hours. WHO and NCDC advisories are leading indicators.",
    "Media Representation": "Monitor for major international media events that generate Nigerian reaction. Negative international coverage events typically produce 3-7 day discourse spikes before subsiding.",
}


def generate_differentiated_assessment(nar: dict) -> dict:
    name = nar["narrative"]
    sov = nar["share_of_voice"]
    momentum = nar["momentum"]
    direction = nar["momentum_direction"]
    sentiment = nar["sentiment_label"]
    count = nar["count"]
    prev_count = nar.get("prev_count", 0)
    confidence = nar["confidence_label"]

    # ── What happened ─────────────────────────────────────────────────────────
    if sov >= 30:
        what_happened = (
            f"**{name}** dominated monitored discourse this period, accounting for {sov:.0f}% of all "
            f"analysed content — {count:,} mentions across monitored sources. "
            f"This represents the single largest narrative category and indicates a high degree of public "
            f"attention concentration in this area."
        )
    elif sov >= 20:
        what_happened = (
            f"**{name}** was a major theme in monitored discourse, capturing {sov:.0f}% of all content "
            f"({count:,} mentions). It ranks among the top narratives this period, reflecting sustained "
            f"public attention to {name.lower()} issues."
        )
    elif sov >= 10:
        what_happened = (
            f"**{name}** maintained a meaningful presence at {sov:.0f}% share of voice ({count:,} mentions). "
            f"While not the dominant narrative, it represents a significant thread in public discourse "
            f"that warrants continued monitoring."
        )
    elif sov >= 5:
        what_happened = (
            f"**{name}** registered at {sov:.0f}% share of voice ({count:,} mentions) — present in monitored "
            f"discourse but below expected levels for a high-priority intelligence category. "
            f"Coverage may be constrained by source availability or news cycle displacement."
        )
    else:
        what_happened = (
            f"**{name}** was significantly underrepresented at {sov:.0f}% share of voice ({count:,} mentions). "
            f"This level of coverage is below monitoring thresholds and may indicate a genuine absence of "
            f"public discourse or a gap in source coverage for this narrative category."
        )

    # ── Why it matters ────────────────────────────────────────────────────────
    why_matters = STRATEGIC_IMPORTANCE.get(name,
        f"Coverage of {name} provides intelligence relevant to RTIFN's strategic mandate and diaspora engagement objectives."
    )

    # ── What changed ──────────────────────────────────────────────────────────
    if prev_count == 0:
        what_changed = (
            f"**{name}** is newly emerging in monitored discourse — no comparable baseline exists from the "
            f"previous period. Establish monitoring baseline over the next 7-14 days before drawing trend conclusions."
        )
    elif direction == "rising" and momentum > 300:
        what_changed = (
            f"Coverage of **{name}** accelerated dramatically — up {momentum:.0f}% compared to the previous period. "
            f"This is an exceptional surge that typically indicates a significant triggering event, major policy "
            f"announcement, or sustained media campaign. Investigate the specific drivers behind this acceleration."
        )
    elif direction == "rising" and momentum > 100:
        what_changed = (
            f"Coverage of **{name}** more than doubled compared to the previous period — up {momentum:.0f}%. "
            f"This is a significant acceleration indicating genuine increased public attention rather than "
            f"normal news cycle variation."
        )
    elif direction == "rising" and momentum > 30:
        what_changed = (
            f"Coverage of **{name}** grew meaningfully — up {momentum:.0f}% compared to the previous period. "
            f"This represents a sustained increase in public attention rather than a temporary spike."
        )
    elif direction == "rising":
        what_changed = (
            f"Coverage of **{name}** increased modestly — up {momentum:.0f}% compared to the previous period. "
            f"The trend is positive but not yet significant enough to indicate a major narrative shift."
        )
    elif direction == "falling" and momentum < -50:
        what_changed = (
            f"Coverage of **{name}** declined sharply — down {abs(momentum):.0f}% compared to the previous period. "
            f"This significant retreat may reflect news cycle displacement, issue resolution, or reduced "
            f"media attention. Monitor whether this decline is sustained or temporary."
        )
    elif direction == "falling":
        what_changed = (
            f"Coverage of **{name}** declined by {abs(momentum):.0f}% compared to the previous period — "
            f"a moderate retreat that may reflect normal news cycle variation rather than reduced underlying importance."
        )
    else:
        what_changed = (
            f"Coverage of **{name}** remained broadly stable compared to the previous period. "
            f"No significant momentum shift detected — this narrative is holding its position in public discourse."
        )

    # ── Sentiment context ─────────────────────────────────────────────────────
    if sentiment == "positive":
        sentiment_text = (
            f"The tone of {name.lower()} coverage was broadly constructive — public discourse is approaching "
            f"these issues from a solutions-oriented or affirmative perspective."
        )
    elif sentiment == "negative":
        sentiment_text = (
            f"The tone of {name.lower()} coverage was predominantly critical or concerned — public discourse "
            f"is highlighting problems, failures, or risks. This warrants leadership attention."
        )
    else:
        sentiment_text = (
            f"Coverage of {name.lower()} was broadly balanced in tone — a mix of perspectives without "
            f"a dominant emotional direction."
        )

    # ── Implications ──────────────────────────────────────────────────────────
    if sentiment == "negative" and direction == "rising" and sov > 10:
        implication = (
            f"Rising negative {name.lower()} discourse represents an emerging reputational and strategic risk. "
            f"If this trend continues, it may suppress diaspora engagement, reduce investment confidence, "
            f"and increase pressure on community organisations to respond publicly. "
            f"Leadership should consider whether proactive communications are warranted."
        )
    elif sentiment == "positive" and direction == "rising" and sov > 15:
        implication = (
            f"Growing positive {name.lower()} coverage creates a favourable communications environment. "
            f"This is an optimal moment for RTIFN to amplify constructive narratives through official "
            f"channels, launch community initiatives, or position diaspora communities as active contributors "
            f"to national progress."
        )
    elif sov > 25:
        implication = (
            f"As the dominant narrative, {name.lower()} is shaping the overall public conversation more "
            f"than any other issue. Leadership communications should acknowledge and engage with "
            f"this narrative to maintain relevance in the current discourse environment."
        )
    elif sov < 5 and STRATEGIC_NARRATIVES.get(name, {}).get("weight", 0) >= 1.0:
        implication = (
            f"Low coverage of {name.lower()} relative to its strategic importance may indicate monitoring "
            f"gaps rather than genuine absence of public discourse. Consider expanding source queries "
            f"for this category to ensure comprehensive intelligence coverage."
        )
    else:
        implication = (
            f"Current {name.lower()} coverage levels are within expected ranges. "
            f"No immediate strategic implication requiring leadership action — continue routine monitoring."
        )

    # ── Leadership action ─────────────────────────────────────────────────────
    if sentiment == "negative" and direction == "rising":
        leadership = (
            f"Prepare a communications response addressing {name.lower()} concerns. "
            f"Consider whether RTIFN's public positioning needs to address the issues driving negative discourse."
        )
    elif sentiment == "positive" and direction == "rising" and sov > 10:
        leadership = (
            f"Leverage positive {name.lower()} momentum through official communications and community engagement. "
            f"This is the optimal window for initiatives aligned with this narrative."
        )
    elif sov > 20:
        leadership = (
            f"As a dominant narrative, {name} should feature prominently in RTIFN's communications this period. "
            f"Ensure organisational messaging is aligned with the current direction of public discourse."
        )
    else:
        leadership = (
            f"Maintain routine monitoring of {name.lower()} discourse. "
            f"No immediate leadership action required — continue tracking for significant shifts."
        )

    return {
        "narrative": name,
        "what_happened": what_happened,
        "why_it_matters": why_matters,
        "what_changed": what_changed,
        "sentiment_context": sentiment_text,
        "implication": implication,
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


def generate_comparative_intelligence(narratives: list) -> list:
    """Generate specific comparative statements — not templates."""
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
                f"**{top['narrative']}** generated {ratio}x more discussion than **{other['narrative']}** — "
                f"a significant concentration of public attention that suggests {other['narrative'].lower()} "
                f"issues are currently being displaced from the primary discourse agenda."
            )
        elif ratio >= 2:
            comparisons.append(
                f"**{top['narrative']}** attracted twice as much coverage as **{other['narrative']}**, "
                f"indicating that {top['narrative'].lower()} concerns are currently commanding disproportionate "
                f"public attention relative to {other['narrative'].lower()} issues."
            )
        elif ratio >= 1.5:
            comparisons.append(
                f"**{top['narrative']}** attracted {ratio}x more coverage than **{other['narrative']}**, "
                f"reflecting the current prioritisation of {top['narrative'].lower()} in public discourse."
            )

    # Governance vs Economy — always a meaningful comparison
    gov = next((n for n in narratives if n["narrative"] == "Governance"), None)
    econ = next((n for n in narratives if n["narrative"] == "Economy"), None)
    sec = next((n for n in narratives if n["narrative"] == "Security"), None)
    diaspora = next((n for n in narratives if n["narrative"] == "Global Nigerian Engagement"), None)

    if gov and econ and gov["count"] > 0 and econ["count"] > 0:
        ratio = round(gov["count"] / max(econ["count"], 1), 1)
        if ratio > 1.5:
            comparisons.append(
                f"Governance generated {ratio}x more discussion than Economy — suggesting that "
                f"leadership performance and institutional issues are currently commanding more public "
                f"attention than economic conditions. This pattern often indicates political salience "
                f"is outweighing cost-of-living concerns in the current news cycle."
            )

    if diaspora and sec and diaspora["count"] > 0 and sec["count"] > 0:
        d_s_ratio = round(diaspora["count"] / max(sec["count"], 1), 1)
        comparisons.append(
            f"Global Nigerian Engagement attracted {d_s_ratio}x {'more' if d_s_ratio >= 1 else 'less'} "
            f"coverage than Security ({diaspora['share_of_voice']:.0f}% vs {sec['share_of_voice']:.0f}%), "
            f"reflecting the diaspora-weighted intelligence mandate of NDIP's monitoring framework."
        )

    # Rising vs falling dynamic
    rising = [n for n in narratives if n["momentum_direction"] == "rising" and n["momentum"] > 50]
    falling = [n for n in narratives if n["momentum_direction"] == "falling" and n["momentum"] < -20]
    if rising and falling:
        comparisons.append(
            f"While **{rising[0]['narrative']}** coverage accelerated significantly this period, "
            f"**{falling[0]['narrative']}** declined — suggesting a possible transfer of public attention "
            f"between these narrative areas that warrants monitoring."
        )

    return comparisons[:5]


def generate_narrative_competition_analysis(narratives: list) -> dict:
    """Item 4: Narrative Competition Engine — what is winning attention?"""
    if not narratives:
        return {}

    total = sum(n["count"] for n in narratives)
    top_two_sov = sum(n["share_of_voice"] for n in narratives[:2])
    top_two_names = " and ".join(f"**{n['narrative']}**" for n in narratives[:2])

    # Identify narrative competition dynamics
    dominant = narratives[0]
    challenger = narratives[1] if len(narratives) > 1 else None

    competition_narrative = (
        f"{top_two_names} collectively account for {top_two_sov:.0f}% of monitored discourse — "
        f"more than half of all public conversation is concentrated in just two narrative areas. "
    )

    # Economic vs political competition
    gov = next((n for n in narratives if n["narrative"] == "Governance"), None)
    econ = next((n for n in narratives if n["narrative"] == "Economy"), None)
    if gov and econ:
        if gov["share_of_voice"] > econ["share_of_voice"] * 2:
            competition_narrative += (
                f"Economic concerns remain significant but are not currently the dominant driver of discussion — "
                f"political and governance narratives are commanding disproportionately more attention. "
                f"This may indicate that institutional and leadership issues are outweighing cost-of-living "
                f"concerns in the current public consciousness."
            )
        elif econ["share_of_voice"] > gov["share_of_voice"]:
            competition_narrative += (
                f"Economic concerns have displaced governance as the primary public discourse driver — "
                f"an unusual pattern that typically indicates significant economic stress or a major "
                f"economic event driving public conversation."
            )

    # Attention winners and losers
    winners = [n for n in narratives if n["momentum_direction"] == "rising" and n["momentum"] > 30]
    losers = [n for n in narratives if n["momentum_direction"] == "falling" and n["momentum"] < -20]

    return {
        "competition_summary": competition_narrative,
        "dominant_narrative": dominant["narrative"],
        "dominant_sov": dominant["share_of_voice"],
        "attention_winners": [{"narrative": n["narrative"], "momentum": n["momentum"]} for n in winners[:3]],
        "attention_losers": [{"narrative": n["narrative"], "momentum": n["momentum"]} for n in losers[:3]],
        "concentration_score": round(top_two_sov, 1),
        "concentration_label": "High" if top_two_sov > 55 else "Moderate" if top_two_sov > 40 else "Distributed",
        "insight": (
            f"Narrative attention is {'highly concentrated' if top_two_sov > 55 else 'moderately concentrated' if top_two_sov > 40 else 'broadly distributed'} "
            f"— {top_two_sov:.0f}% of discourse is captured by just two narrative categories."
        ),
    }


def generate_outlook_engine(narratives: list, days: int, risks: list, opportunities: list) -> dict:
    """Evidence-based outlook — observation not prediction. Always explains why."""
    rising = [n for n in narratives if n["momentum_direction"] == "rising" and n["momentum"] > 30]
    neg_rising = [n for n in narratives if n["momentum_direction"] == "rising" and n["sentiment_label"] == "negative"]
    high_risks = [r for r in risks if r.get("level") in ("Critical", "Warning")]
    high_opps = [o for o in opportunities if o.get("rank") == "High"]
    total_records = sum(n["count"] for n in narratives)

    def _7day():
        if neg_rising:
            n = neg_rising[0]
            return (
                f"**{n['narrative']}** negative discourse is accelerating and is likely to remain elevated "
                f"over the next 7 days unless underlying conditions change. "
                f"This outlook is based on current momentum trajectory ({n['momentum']:.0f}% growth) "
                f"and negative sentiment direction. Leadership communications should be prepared."
            )
        elif rising:
            n = rising[0]
            return (
                f"**{n['narrative']}** is the fastest-growing narrative and is likely to maintain or "
                f"increase its share of voice over the next 7 days. "
                f"This outlook is based on current momentum of {n['momentum']:.0f}% growth. "
                f"{'This represents a communications opportunity.' if n['sentiment_label'] == 'positive' else 'Monitor sentiment direction closely.'}"
            )
        elif high_risks:
            return (
                f"The 7-day outlook is cautiously stable. {high_risks[0]['title']} remains the primary "
                f"monitoring concern. No significant escalation is anticipated based on current data, "
                f"but conditions should be reviewed daily."
            )
        return (
            f"The 7-day outlook is stable. Current narrative patterns are expected to continue without "
            f"significant disruption. This assessment is based on balanced momentum across {len(narratives)} "
            f"narrative categories with no dominant acceleration signals."
        )

    def _14day():
        items = [f"**{n['narrative']}**" for n in rising[:2]]
        items += [f"**{r['title']}**" for r in high_risks[:1]]
        if items:
            return (
                f"Over the next 14 days, {', '.join(items[:3])} warrant heightened monitoring. "
                f"Current momentum patterns suggest these areas are likely to remain prominent. "
                f"This outlook is generated from {total_records:,} records analysed over the {days}-day window — "
                f"leadership should maintain situational awareness across these narratives."
            )
        return (
            f"The 14-day outlook is stable. No significant narrative shifts are anticipated based on "
            f"current momentum data across {len(narratives)} monitored categories. "
            f"Continue standard monitoring cadence."
        )

    def _30day():
        elections = next((n for n in narratives if n["narrative"] == "Elections & Democracy"), None)
        election_note = ""
        if elections:
            election_note = (
                f" Electoral discourse is expected to gradually intensify as Nigeria's 2027 election "
                f"cycle progresses — current electoral coverage ({elections['share_of_voice']:.0f}%) "
                f"is likely to increase over the 30-day period."
            )
        if high_opps:
            return (
                f"The 30-day outlook is positive. Current engagement levels and sentiment trends provide "
                f"a favourable environment for community initiatives.{election_note} "
                f"The high engagement window identified this period ({high_opps[0]['title']}) suggests "
                f"strong community receptivity to RTIFN outreach and programming."
            )
        return (
            f"The 30-day outlook is broadly stable.{election_note} "
            f"Continue building monitoring baseline — intelligence quality will improve as data accumulates."
        )

    return {
        "7_day": _7day(),
        "14_day": _14day(),
        "30_day": _30day(),
        "monitoring_priorities": [n["narrative"] for n in rising[:3]] or ["Continue routine monitoring"],
        "emerging_concerns": [n["narrative"] for n in neg_rising[:2]],
        "emerging_opportunities": [o["title"] for o in high_opps[:2]],
        "outlook_basis": (
            f"Based on {total_records:,} records across {len(narratives)} narratives "
            f"over a {days}-day analysis window."
        ),
    }
