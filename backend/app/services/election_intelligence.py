"""
NDIP Election Intelligence Service v5.2
Transforms election metrics into full analyst-grade intelligence.
Covers: Assessment, Implications, Risks, Opportunities, Outlook, Monitoring Priorities, Confidence.
"""
from datetime import datetime, timezone, timedelta
from sqlalchemy.orm import Session
from app.analytics.strategic_narratives import get_narrative_analysis

ELECTION_DATE = datetime(2027, 2, 1, tzinfo=timezone.utc)

# ─── Election phase logic ─────────────────────────────────────────────────────
def get_election_phase(days_to_election: int) -> dict:
    if days_to_election > 365:
        return {"phase": "Pre-Campaign", "phase_description": "Early pre-election period. Party positioning and policy discourse beginning to emerge. Electoral institutions preparing administrative frameworks.", "expected_discourse_level": 3, "urgency": "Low"}
    elif days_to_election > 180:
        return {"phase": "Early Campaign", "phase_description": "Campaign environment forming. Candidate positioning, party primaries, and civic mobilisation beginning.", "expected_discourse_level": 8, "urgency": "Medium"}
    elif days_to_election > 90:
        return {"phase": "Active Campaign", "phase_description": "Campaign in full activity. Candidate debates, policy announcements, and public mobilisation intensifying.", "expected_discourse_level": 20, "urgency": "High"}
    elif days_to_election > 30:
        return {"phase": "Final Stretch", "phase_description": "Election imminent. Final campaign activities, security preparations, and public attention at peak.", "expected_discourse_level": 35, "urgency": "Critical"}
    else:
        return {"phase": "Election Imminent", "phase_description": "Election days away. Maximum public attention, security and logistics focus.", "expected_discourse_level": 50, "urgency": "Critical"}


# ─── Assessment ──────────────────────────────────────────────────────────────
def generate_election_assessment(elections: dict, phase: dict, days: int, days_to_election: int) -> dict:
    sov = elections["share_of_voice"] if elections else 0
    count = elections["count"] if elections else 0
    sentiment = elections["sentiment_label"] if elections else "neutral"
    momentum = elections["momentum"] if elections else 0
    direction = elections["momentum_direction"] if elections else "stable"
    expected = phase["expected_discourse_level"]

    # What happened
    if sov >= 15:
        what_happened = (
            f"Electoral discourse reached {sov:.0f}% share of voice this period — {count:,} mentions "
            f"across monitored sources. This represents elevated electoral attention for a period "
            f"{days_to_election} days ahead of the 2027 Nigerian General Election."
        )
    elif sov >= 5:
        what_happened = (
            f"Electoral discourse registered at {sov:.0f}% share of voice — {count:,} mentions across "
            f"monitored sources. Electoral discussion is present and building, consistent with the "
            f"{phase['phase']} phase of the election cycle."
        )
    else:
        what_happened = (
            f"Electoral discourse remains at {sov:.0f}% share of voice — {count:,} mentions across "
            f"monitored sources. This is below the expected threshold of {expected}% for this phase "
            f"of the 2027 election cycle, suggesting electoral discourse has not yet entered mainstream "
            f"public conversation."
        )

    # Discourse level context
    if sov < expected * 0.5:
        discourse_context = f"Current electoral discourse ({sov:.0f}%) is significantly below the expected level ({expected}%) for the {phase['phase']} phase. This may reflect public attention focused on other national priorities, or limited media coverage of electoral preparations."
    elif sov < expected:
        discourse_context = f"Current electoral discourse ({sov:.0f}%) is below the expected level ({expected}%) for the {phase['phase']} phase but within a normal range. Electoral attention is building gradually."
    else:
        discourse_context = f"Current electoral discourse ({sov:.0f}%) meets or exceeds expected levels ({expected}%) for the {phase['phase']} phase. Public attention to the election is developing on schedule."

    # Momentum assessment
    if direction == "rising" and momentum > 100:
        momentum_text = f"Electoral discourse is accelerating rapidly — up {momentum:.0f}% compared to the previous period. This surge warrants immediate attention and may indicate a specific triggering event."
    elif direction == "rising" and momentum > 30:
        momentum_text = f"Electoral discourse is growing — up {momentum:.0f}% compared to the previous period. The election cycle is beginning to attract increased public attention."
    elif direction == "falling":
        momentum_text = f"Electoral discourse declined by {abs(momentum):.0f}% compared to the previous period. This may reflect temporary news cycle displacement rather than reduced underlying interest."
    else:
        momentum_text = f"Electoral discourse remained broadly stable compared to the previous period — no significant momentum shift detected."

    return {
        "what_happened": what_happened,
        "discourse_context": discourse_context,
        "momentum_assessment": momentum_text,
        "current_sov": sov,
        "current_count": count,
        "sentiment": sentiment,
        "momentum": momentum,
        "direction": direction,
        "phase": phase["phase"],
        "days_to_election": days_to_election,
        "expected_discourse_level": expected,
    }


# ─── Why It Matters ──────────────────────────────────────────────────────────
def generate_election_why_it_matters(elections: dict, phase: dict, days_to_election: int, narratives: list) -> dict:
    sov = elections["share_of_voice"] if elections else 0
    sentiment = elections["sentiment_label"] if elections else "neutral"

    # Core importance
    core_importance = (
        "Nigeria's 2027 General Election will be one of Africa's most significant democratic events. "
        "Electoral discourse trends are leading indicators of civic mobilisation, institutional trust, "
        "and political stability — all of which directly affect diaspora engagement, investment confidence, "
        "and Nigeria's international reputation."
    )

    # Diaspora relevance
    diaspora_relevance = (
        "For RTIFN and the Nigerian diaspora, the election cycle is a period of heightened civic engagement. "
        "Diaspora communities historically increase advocacy activity, financial contributions to campaigns, "
        "and public commentary during election periods. Monitoring electoral discourse enables RTIFN to "
        "anticipate and respond to diaspora mobilisation trends."
    )

    # Current significance
    if sov < 5:
        current_significance = (
            f"Current low electoral discourse ({sov:.0f}%) indicates the public is not yet focused on the "
            f"election. This is the window for civic education, voter registration awareness, and institutional "
            f"trust-building — before partisan debate dominates the discourse space."
        )
    elif sentiment == "negative":
        current_significance = (
            f"Negative electoral sentiment ({sov:.0f}% share of voice) warrants attention. Negative discourse "
            f"at this stage of the cycle may indicate declining trust in electoral institutions, concerns "
            f"about process integrity, or early partisan polarisation. If sustained, this could suppress "
            f"civic participation and depress diaspora electoral engagement."
        )
    else:
        current_significance = (
            f"The current electoral discourse environment ({sov:.0f}% share of voice, {sentiment} sentiment) "
            f"is broadly constructive. This is the optimal period to establish positive civic narratives "
            f"before the discourse environment becomes more contested as the election approaches."
        )

    # Cross-narrative significance
    gov = next((n for n in narratives if n["narrative"] == "Governance"), None)
    cross_narrative = ""
    if gov and gov["share_of_voice"] > sov * 3:
        cross_narrative = (
            f"Notably, Governance discourse ({gov['share_of_voice']:.0f}% share of voice) is currently "
            f"commanding significantly more attention than electoral discourse ({sov:.0f}%). This suggests "
            f"public concern about institutional performance may be channelled through governance narratives "
            f"rather than electoral ones — a pattern that sometimes precedes a shift toward electoral discourse "
            f"as the election approaches."
        )

    return {
        "core_importance": core_importance,
        "diaspora_relevance": diaspora_relevance,
        "current_significance": current_significance,
        "cross_narrative_significance": cross_narrative,
    }


# ─── Strategic Implications ──────────────────────────────────────────────────
def generate_election_implications(elections: dict, phase: dict, days_to_election: int) -> dict:
    sov = elections["share_of_voice"] if elections else 0
    sentiment = elections["sentiment_label"] if elections else "neutral"
    momentum = elections["momentum"] if elections else 0
    direction = elections["momentum_direction"] if elections else "stable"

    implications = {}

    # Democratic governance
    if sentiment == "negative" and sov > 5:
        implications["democratic_governance"] = "Negative electoral discourse signals potential erosion of confidence in democratic institutions. INEC, the judiciary, and security agencies should be monitored for discourse shifts that may indicate institutional credibility concerns."
    else:
        implications["democratic_governance"] = "Current electoral discourse is not generating significant concern about democratic governance quality. The institutional environment appears broadly stable from a public discourse perspective."

    # Public trust
    if direction == "rising" and sentiment == "negative":
        implications["public_trust"] = "Rising negative electoral discourse is an early warning indicator for declining public trust. Trust erosion at this stage of the cycle is more damaging than closer to the election, as it shapes the baseline from which civic mobilisation must build."
    elif sentiment == "positive":
        implications["public_trust"] = "Positive electoral sentiment indicates public trust in democratic processes remains intact. This is a constructive foundation for civic engagement campaigns and voter participation initiatives."
    else:
        implications["public_trust"] = "Neutral electoral sentiment suggests public trust is neither building nor eroding significantly. The discourse environment is open to positive framing — a missed opportunity if left unaddressed."

    # Civic participation
    if sov < 3:
        implications["civic_participation"] = f"Very low electoral discourse ({sov:.0f}%) suggests civic mobilisation has not yet begun in earnest. With {days_to_election} days to the election, there is a significant window for civic education and voter engagement initiatives before partisan discourse crowds out constructive participation narratives."
    elif direction == "rising":
        implications["civic_participation"] = f"Growing electoral discourse ({sov:.0f}%, up {momentum:.0f}%) indicates early civic mobilisation. This is the optimal moment to channel emerging public attention toward constructive participation narratives rather than allowing partisan or negative framing to dominate."
    else:
        implications["civic_participation"] = f"Electoral discourse at {sov:.0f}% share of voice represents a modest civic engagement level. Targeted civic participation campaigns could increase this share and improve democratic participation quality."

    # Diaspora engagement
    implications["diaspora_engagement"] = (
        "The Nigerian diaspora has historically played a significant role in election cycles — "
        "through remittances funding campaigns, advocacy on electoral integrity, media commentary, "
        "and mobilisation of home communities. Current electoral discourse levels suggest diaspora "
        "engagement is in early formation. RTIFN should establish its electoral observation and "
        "civic engagement positioning before discourse intensifies."
    )

    # Political stability
    if sentiment == "negative" and direction == "rising":
        implications["political_stability"] = "Rising negative electoral discourse is a leading indicator for political instability risk. If this trajectory continues, it may suppress investment, increase security concerns, and negatively affect Nigeria's international reputation approaching the election."
    else:
        implications["political_stability"] = "Current electoral discourse does not indicate elevated political instability risk. The discourse environment is consistent with a pre-election period in a functioning democracy."

    return implications


# ─── Election Risks ──────────────────────────────────────────────────────────
def generate_election_risks(elections: dict, narratives: list, days_to_election: int) -> list:
    risks = []
    sov = elections["share_of_voice"] if elections else 0
    sentiment = elections["sentiment_label"] if elections else "neutral"
    security = next((n for n in narratives if n["narrative"] == "Security"), None)
    gov = next((n for n in narratives if n["narrative"] == "Governance"), None)

    # Low civic engagement risk
    if sov < 5:
        risks.append({
            "risk": "Low Electoral Civic Engagement",
            "level": "Medium",
            "level_order": 2,
            "detail": f"Electoral discourse at {sov:.0f}% is below expected levels for {days_to_election} days ahead of the election. Sustained low engagement may result in poor voter turnout, weak civic mobilisation, and reduced public scrutiny of electoral processes.",
            "reasoning": "Low pre-election discourse historically correlates with reduced voter registration and civic participation. Early engagement campaigns are most effective when initiated during low-activity periods.",
            "action": "Commission civic awareness monitoring to track engagement trajectory. Consider diaspora-facing voter education content.",
            "confidence_label": "Medium",
        })

    # Security-election intersection
    if security and security["share_of_voice"] > 15:
        risks.append({
            "risk": "Security-Election Discourse Intersection",
            "level": "Watch",
            "level_order": 3,
            "detail": f"Security discourse ({security['share_of_voice']:.0f}% share of voice) significantly exceeds electoral discourse ({sov:.0f}%). High security discourse ahead of an election cycle may indicate concerns about election-period security that are being discussed through general security narratives rather than explicitly electoral ones.",
            "reasoning": "In previous Nigerian election cycles, security concerns have been a significant factor in voter participation and diaspora engagement. Monitor for explicit references to election security within security narratives.",
            "action": "Monitor security narrative content for election-related keywords. Track geographic concentration of security discourse.",
            "confidence_label": "Medium",
        })

    # Governance-trust risk
    if gov and gov["sentiment_label"] == "negative" and gov["share_of_voice"] > 15:
        risks.append({
            "risk": "Governance Trust Deficit Pre-Election",
            "level": "Warning",
            "level_order": 2,
            "detail": f"Negative governance discourse ({gov['share_of_voice']:.0f}% share of voice) in the pre-election period may indicate declining institutional trust. Trust deficits formed before the campaign period are difficult to reverse and can suppress civic participation.",
            "reasoning": "Negative governance sentiment in pre-election periods historically correlates with reduced confidence in electoral institutions, as voters conflate government performance with election administration quality.",
            "action": "Monitor for shifts from general governance criticism toward INEC-specific or electoral institution criticism. This transition signals escalating risk.",
            "confidence_label": "High",
        })

    # Negative electoral sentiment
    if sentiment == "negative" and sov > 3:
        risks.append({
            "risk": "Negative Electoral Sentiment",
            "level": "Warning",
            "level_order": 2,
            "detail": f"Electoral discourse carries negative sentiment at {sov:.0f}% share of voice. Negative framing of electoral processes at this stage may indicate concerns about election integrity, institutional capacity, or political fairness.",
            "reasoning": "Negative electoral sentiment is a leading indicator for reduced civic participation and increased potential for post-election disputes.",
            "action": "Investigate specific drivers of negative sentiment. Identify whether criticism targets INEC, political parties, or broader democratic processes.",
            "confidence_label": "High",
        })

    # Timeline risk
    if days_to_election < 300 and sov < 3:
        risks.append({
            "risk": "Electoral Discourse Lag",
            "level": "Information",
            "level_order": 4,
            "detail": f"With {days_to_election} days to the election and only {sov:.0f}% electoral discourse, there is a risk that civic preparation and public awareness activities are not gaining traction. Electoral discourse typically needs to build gradually — a sustained lag may compress the available window for civic engagement.",
            "reasoning": "Electoral discourse patterns in 2023 Nigerian election showed gradual build from 18 months ahead. Current levels are consistent with that pattern but warrant monitoring.",
            "action": "Establish monthly electoral discourse benchmarks. Flag if discourse remains below 5% by 180 days ahead.",
            "confidence_label": "Medium",
        })

    return sorted(risks, key=lambda x: x["level_order"])


# ─── Election Opportunities ──────────────────────────────────────────────────
def generate_election_opportunities(elections: dict, narratives: list, days_to_election: int) -> list:
    opportunities = []
    sov = elections["share_of_voice"] if elections else 0
    sentiment = elections["sentiment_label"] if elections else "neutral"
    direction = elections["momentum_direction"] if elections else "stable"

    # Civic education window
    if sov < 10:
        opportunities.append({
            "opportunity": "Civic Education Window",
            "rank": "High",
            "detail": f"Low current electoral discourse ({sov:.0f}%) and {days_to_election} days to the election creates an optimal window for civic education and voter awareness initiatives. Early civic engagement shapes the discourse environment before partisan narratives dominate.",
            "strategic_context": "RTIFN is well-positioned to lead diaspora civic education initiatives during this low-competition window. Content addressing voter registration, electoral processes, and democratic participation will face minimal counter-narrative competition at this stage.",
            "action": "Develop and distribute a civic education content series targeting diaspora communities. Position RTIFN as a trusted electoral information source before campaign discourse intensifies.",
            "confidence_label": "High",
        })

    # Positive sentiment leverage
    if sentiment in ("positive", "neutral") and sov > 2:
        opportunities.append({
            "opportunity": "Positive Electoral Discourse Amplification",
            "rank": "High",
            "detail": f"Current electoral discourse is {sentiment} in tone. This constructive environment provides a platform for amplifying democratic participation narratives before negative or partisan framing takes hold.",
            "strategic_context": "Positive pre-election discourse is rare and valuable. Communities and organisations that establish positive electoral narratives early have disproportionate influence on the discourse environment as the election approaches.",
            "action": "Issue RTIFN electoral engagement position statement. Amplify positive civic participation narratives through community channels.",
            "confidence_label": "High",
        })

    # Diaspora engagement
    opportunities.append({
        "opportunity": "Diaspora Electoral Engagement Leadership",
        "rank": "High",
        "detail": f"With {days_to_election} days to the election, RTIFN has a unique window to establish itself as the primary diaspora voice on electoral observation, civic participation, and democratic governance.",
        "strategic_context": "Diaspora organisations that establish electoral credibility early in the cycle have significantly more influence on community behaviour closer to the election. The current low-activity period is the least competitive time to build this positioning.",
        "action": "Establish an RTIFN Electoral Observation and Civic Engagement programme. Begin regular election intelligence briefings for community leadership.",
        "confidence_label": "High",
    })

    # Early monitoring establishment
    if direction == "rising":
        opportunities.append({
            "opportunity": "Emerging Electoral Discourse — Early Position",
            "rank": "Medium",
            "detail": f"Electoral discourse is growing ({direction}, up {elections.get('momentum', 0):.0f}%). This early acceleration provides a window to engage with emerging narratives before they crystallise.",
            "strategic_context": "Narratives established during the early acceleration phase tend to persist. Community organisations that participate early in defining electoral discourse have lasting influence on how the election is framed.",
            "action": "Monitor emerging electoral topics weekly. Prepare RTIFN commentary on the most significant emerging narratives.",
            "confidence_label": "Medium",
        })

    return opportunities


# ─── Election Outlook ─────────────────────────────────────────────────────────
def generate_election_outlook(elections: dict, phase: dict, days_to_election: int, risks: list, opportunities: list) -> dict:
    sov = elections["share_of_voice"] if elections else 0
    direction = elections["momentum_direction"] if elections else "stable"
    momentum = elections["momentum"] if elections else 0
    high_risks = [r for r in risks if r["level"] in ("Critical", "Warning")]

    def _7day():
        if direction == "rising" and momentum > 100:
            return {
                "outlook": f"Electoral discourse is accelerating rapidly (up {momentum:.0f}%). Over the next 7 days this momentum is likely to continue. Monitor for the specific triggering event driving this surge.",
                "drivers": "Recent electoral developments or policy announcements are likely driving this acceleration.",
                "uncertainties": "Whether acceleration represents a sustained trend or a temporary news cycle spike.",
                "monitoring": "Daily monitoring of electoral discourse share of voice. Identify specific articles and sources driving the increase.",
            }
        elif direction == "rising":
            return {
                "outlook": f"Electoral discourse is building gradually. Over the next 7 days, moderate continued growth is expected as the {phase['phase']} phase develops.",
                "drivers": "Normal electoral cycle progression and growing public awareness of the approaching election.",
                "uncertainties": "Whether growth will sustain or plateau pending specific campaign developments.",
                "monitoring": "Weekly tracking of electoral discourse share. Monitor for INEC announcements or party convention activity.",
            }
        else:
            return {
                "outlook": f"Electoral discourse is expected to remain broadly stable over the next 7 days at approximately {sov:.0f}% share of voice. No significant electoral events are anticipated based on current discourse signals.",
                "drivers": "Stable pre-election environment with no major electoral triggers detected.",
                "uncertainties": "Unexpected electoral administration announcements or security incidents could rapidly shift discourse.",
                "monitoring": "Continue routine monitoring. Flag any sudden discourse spikes exceeding 5% share of voice.",
            }

    def _14day():
        return {
            "outlook": f"Over the next 14 days, electoral discourse is expected to {'continue building' if direction == 'rising' else 'remain stable'} as Nigeria progresses through the {phase['phase']} phase. With {days_to_election} days to the election, electoral attention will gradually increase.",
            "drivers": "Electoral calendar milestones, INEC administrative activities, and party positioning will drive discourse shifts.",
            "uncertainties": "Security conditions, economic developments, and governance events may displace or amplify electoral discourse.",
            "monitoring": "Monitor INEC official communications, party primary activities, and civil society electoral commentary. Track sentiment direction — a shift to negative warrants immediate escalation.",
        }

    def _30day():
        days_marker = days_to_election - 30
        return {
            "outlook": f"The 30-day electoral outlook is {'cautiously positive' if not high_risks else 'attentive'}. By this time, Nigeria will be {days_marker} days from the election. Electoral discourse is expected to be establishing its trajectory — the narrative environment formed in this period will shape the campaign discourse.",
            "drivers": "Campaign launch activities, voter registration progress, electoral institution announcements, and international observer engagement will be primary discourse drivers.",
            "uncertainties": "Security conditions, economic shocks, and governance crises represent the primary uncertainties that could disrupt the electoral discourse trajectory.",
            "monitoring": "Establish a 30-day electoral discourse benchmark. Track whether discourse is building toward expected pre-campaign levels. Monitor trust indicators for INEC and electoral institutions specifically.",
        }

    return {
        "7_day": _7day(),
        "14_day": _14day(),
        "30_day": _30day(),
        "outlook_basis": f"Based on current electoral discourse at {sov:.0f}% share of voice, {phase['phase']} phase assessment, and {days_to_election} days to the 2027 General Election.",
    }


# ─── Monitoring Priorities ────────────────────────────────────────────────────
def generate_election_monitoring_priorities() -> list:
    return [
        {
            "priority": "INEC Election Administration",
            "what_to_monitor": "INEC official announcements, voter registration updates, electoral calendar milestones, and public communications about election preparation.",
            "why_it_matters": "INEC's administrative credibility is the foundation of public trust in the electoral process. Negative discourse about INEC capacity or impartiality is the strongest predictor of post-election disputes.",
            "confidence_label": "High",
            "monitoring_period": "Weekly throughout the election cycle. Daily from 90 days ahead.",
            "area": "Electoral Process",
        },
        {
            "priority": "Public Trust Indicators",
            "what_to_monitor": "Sentiment toward electoral institutions, confidence in the voting process, commentary on election integrity, and civil society electoral assessments.",
            "why_it_matters": "Trust deficits formed before the campaign period are difficult to reverse. Early negative trust signals require proactive narrative management.",
            "confidence_label": "High",
            "monitoring_period": "Monthly now. Weekly from 180 days ahead. Daily from 60 days ahead.",
            "area": "Public Trust",
        },
        {
            "priority": "Diaspora Electoral Engagement",
            "what_to_monitor": "Diaspora community discourse about the election, overseas Nigerian advocacy activity, remittance patterns relative to election cycle, and diaspora voter registration discussions.",
            "why_it_matters": "The Nigerian diaspora is a significant force in election cycles — financially, through advocacy, and through influence on home communities. Diaspora engagement trends are leading indicators of community mobilisation.",
            "confidence_label": "High",
            "monitoring_period": "Monthly now. Weekly from 180 days ahead.",
            "area": "Diaspora Election Engagement",
        },
        {
            "priority": "Civic Participation Trends",
            "what_to_monitor": "Voter registration discourse, civic education campaigns, youth engagement narratives, and community mobilisation activity.",
            "why_it_matters": "Civic participation levels directly affect election legitimacy and outcome representativeness. Early civic engagement monitoring enables targeted intervention when participation discourse is lagging.",
            "confidence_label": "Medium",
            "monitoring_period": "Monthly now. Weekly from 270 days ahead.",
            "area": "Civic Participation",
        },
        {
            "priority": "Electoral Reform Discourse",
            "what_to_monitor": "Constitutional reform discussions, electoral law amendments, voting technology debates, and civil society reform advocacy.",
            "why_it_matters": "Electoral reform discussions often signal underlying concerns about process integrity. Reform advocacy can either build or erode public confidence depending on its framing.",
            "confidence_label": "Medium",
            "monitoring_period": "Monthly monitoring. Escalate if discourse exceeds 2% share of voice.",
            "area": "Electoral Reform",
        },
        {
            "priority": "Election Security Environment",
            "what_to_monitor": "Security discourse intersecting with electoral geography, threat assessments for election-day security, military and police electoral deployment discussions.",
            "why_it_matters": "Election security conditions directly affect voter turnout, particularly in conflict-affected states. Security concerns in diaspora-origin states generate disproportionately strong diaspora community responses.",
            "confidence_label": "High",
            "monitoring_period": "Weekly now. Daily from 90 days ahead.",
            "area": "Election Security",
        },
        {
            "priority": "Political Polarisation Indicators",
            "what_to_monitor": "Sentiment variance across sources, partisan discourse intensity, inter-party conflict narratives, and social cohesion indicators.",
            "why_it_matters": "Pre-election polarisation is a leading indicator for election-period violence and post-election instability. Early detection enables preventive civic engagement.",
            "confidence_label": "Medium",
            "monitoring_period": "Monthly now. Weekly from 180 days ahead.",
            "area": "Democratic Accountability",
        },
    ]


# ─── Confidence Framework ─────────────────────────────────────────────────────
def generate_election_confidence(elections: dict, source_quality: dict) -> dict:
    sov = elections["share_of_voice"] if elections else 0
    count = elections["count"] if elections else 0
    sources = source_quality.get("source_count", 12)
    nlp_rate = source_quality.get("processing_rate", 100)

    # Source coverage assessment
    if sources >= 10:
        source_coverage = "High — intelligence draws from 10+ active sources including Nigerian national media, international news APIs, and global event databases."
    elif sources >= 6:
        source_coverage = "Moderate — intelligence draws from 6-9 active sources. Some regional or specialist electoral sources may be underrepresented."
    else:
        source_coverage = "Limited — fewer than 6 sources active. Electoral intelligence may not capture full discourse breadth."

    # Evidence strength
    if count >= 200:
        evidence_strength = f"High — {count:,} electoral mentions provide a robust evidence base for assessment."
    elif count >= 50:
        evidence_strength = f"Moderate — {count:,} electoral mentions provide adequate evidence. Assessments are directionally reliable but may lack granularity."
    else:
        evidence_strength = f"Limited — only {count:,} electoral mentions detected. Assessments should be treated as indicative rather than definitive at this evidence volume."

    # Overall confidence
    if count >= 100 and sources >= 8 and nlp_rate >= 90:
        overall = "High"
        overall_reasoning = "Strong evidence base, diverse source coverage, and high NLP processing rate support confident assessment."
    elif count >= 50 and sources >= 6:
        overall = "Medium"
        overall_reasoning = "Adequate evidence base for directional assessment. Confidence will improve as electoral discourse volume increases closer to the election."
    else:
        overall = "Low"
        overall_reasoning = "Limited electoral evidence volume constrains confidence. Assessments should be treated as early indicators only."

    limitations = [
        "Electoral discourse monitoring covers publicly available sources only — private political communications, internal party documents, and off-record discussions are not captured.",
        "Sentiment analysis reflects expressed public tone, not private voter intention.",
        f"Electoral discourse currently represents {sov:.0f}% of total monitored content — assessments will strengthen as electoral discourse volume increases.",
        "Geographic distribution of sources is weighted toward Lagos, Abuja, and international outlets. State-level electoral dynamics in less-covered regions may be underrepresented.",
    ]

    return {
        "overall": overall,
        "source_coverage": source_coverage,
        "evidence_strength": evidence_strength,
        "overall_reasoning": overall_reasoning,
        "limitations": limitations,
        "data_volume": f"{count:,} electoral mentions",
        "analytical_confidence": overall,
    }


# ─── Executive Election Briefing ──────────────────────────────────────────────
def generate_executive_election_briefing(
    assessment: dict, why_matters: dict, implications: dict,
    risks: list, opportunities: list, outlook: dict,
    monitoring: list, confidence: dict, days_to_election: int, phase: dict
) -> dict:
    high_risks = [r for r in risks if r["level"] in ("Critical", "Warning")]
    high_opps = [o for o in opportunities if o["rank"] == "High"]

    summary = (
        f"Nigeria's 2027 General Election is {days_to_election} days away. "
        f"The platform is currently in the {phase['phase']} phase. "
        f"{assessment['what_happened']} "
        f"{assessment['momentum_assessment']}"
    )

    key_changes = []
    if assessment["direction"] == "rising" and assessment["momentum"] > 50:
        key_changes.append(f"Electoral discourse accelerated significantly — up {assessment['momentum']:.0f}%")
    if assessment["current_sov"] < assessment["expected_discourse_level"] * 0.5:
        key_changes.append(f"Discourse remains below expected levels for this phase ({assessment['current_sov']:.0f}% vs expected {assessment['expected_discourse_level']}%)")
    if not key_changes:
        key_changes.append("No significant changes in electoral discourse detected this period")

    strategic_summary = (
        f"{why_matters['core_importance']} "
        f"{why_matters['current_significance']}"
    )

    return {
        "briefing_date": datetime.now(timezone.utc).isoformat(),
        "days_to_election": days_to_election,
        "election_phase": phase["phase"],
        "election_summary": summary,
        "key_changes": key_changes,
        "strategic_summary": strategic_summary,
        "top_risks": high_risks[:3],
        "top_opportunities": high_opps[:3],
        "immediate_outlook": outlook["7_day"]["outlook"],
        "top_monitoring_priorities": monitoring[:3],
        "confidence_statement": f"{confidence['overall']} confidence. {confidence['overall_reasoning']}",
        "limitations": confidence["limitations"][:2],
    }




# ─── Election Implications Engine ────────────────────────────────────────────

def generate_election_implications_engine(elections: dict, phase: dict, days_to_election: int,
                                           narratives: list, risks: list, opportunities: list, db: Session = None) -> dict:
    """
    Decision-support layer: If current trends continue, what happens next?
    Converts election metrics into forward-looking decision support.
    """
    sov = elections["share_of_voice"] if elections else 0
    direction = elections["momentum_direction"] if elections else "stable"
    momentum = elections["momentum"] if elections else 0
    sentiment = elections["sentiment_label"] if elections else "neutral"

    sec = next((n for n in narratives if n["narrative"] == "Security"), None)
    gov = next((n for n in narratives if n["narrative"] == "Governance"), None)

    # If current trends continue...
    trend_implications = []

    if direction == "rising" and momentum > 100:
        trend_implications.append(
            f"If the current {momentum:.0f}% acceleration in electoral discourse continues, "
            f"electoral narratives will likely emerge as a top-3 discourse category within 2-4 weeks. "
            f"This would signal entry into the early active campaign phase earlier than typical for this stage of the cycle."
        )
    elif sov < 5 and days_to_election > 180:
        trend_implications.append(
            f"If current low electoral discourse levels ({sov:.0f}%) persist, civic mobilisation will be "
            f"delayed relative to historical Nigerian election patterns. This creates a window for proactive "
            f"civic engagement organisations to establish narrative presence before campaign discourse dominates."
        )

    if sec and sec["share_of_voice"] > 15 and sec["sentiment_label"] == "negative":
        trend_implications.append(
            f"If elevated negative security discourse ({sec['share_of_voice']:.0f}%) continues approaching "
            f"the election, it will increasingly intersect with electoral confidence narratives. Historical "
            f"patterns suggest this intersection typically occurs 90-120 days before an election."
        )

    if gov and gov["sentiment_label"] == "negative":
        trend_implications.append(
            "If negative governance sentiment persists, it will likely erode confidence in electoral "
            "institutions as the campaign period approaches — a pattern seen in the 2023 election cycle."
        )

    if not trend_implications:
        trend_implications.append(
            f"If current trends continue, the electoral discourse environment will develop consistent with "
            f"a typical Nigerian pre-election pattern — gradual build from current {sov:.0f}% toward "
            f"20-30% share of voice by 90 days ahead of the election."
        )

    # Increasing risks
    escalating_risks = []
    if days_to_election < 300 and sov < 3:
        escalating_risks.append({
            "risk": "Civic Engagement Deficit",
            "trajectory": "Increasing",
            "detail": "Low pre-election civic discourse reduces voter registration momentum and community preparedness.",
        })
    if sec and sec["momentum_direction"] == "rising" and sec["sentiment_label"] == "negative":
        escalating_risks.append({
            "risk": "Security-Election Intersection",
            "trajectory": "Increasing",
            "detail": "Rising negative security discourse approaching an election cycle historically correlates with reduced voter confidence.",
        })
    if gov and gov["sentiment_label"] == "negative" and gov["share_of_voice"] > 15:
        escalating_risks.append({
            "risk": "Institutional Trust Erosion",
            "trajectory": "Watch",
            "detail": "Negative governance sentiment in the pre-election period may transfer to electoral institution distrust.",
        })

    # Emerging opportunities
    emerging_opps = []
    if sov < 8 and direction == "rising":
        emerging_opps.append({
            "opportunity": "Early Electoral Narrative Leadership",
            "window": "Now — 60 days",
            "detail": "Early-stage electoral discourse growth creates a low-competition window to establish RTIFN as a trusted electoral information source.",
        })
    if sentiment == "positive":
        emerging_opps.append({
            "opportunity": "Positive Electoral Framing",
            "window": "This period",
            "detail": "Current positive electoral sentiment provides an opportunity to establish constructive democratic participation narratives before campaign discourse intensifies.",
        })

    # Leadership actions
    leadership_actions = []
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
            })
    if direction == "rising" and momentum > 100:
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
            })
    if db is not None:
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
        })

    # Diaspora-specific actions
    diaspora_actions = [
        {
            "action": "Diaspora Voter Education Programme",
            "priority": "Prepare",
            "detail": "Develop voter information resources for diaspora communities covering electoral registration, process, and rights.",
        },
        {
            "action": "Election Observation Coordination",
            "priority": "Monitor",
            "detail": "Connect with established election observation organisations for diaspora community monitoring coordination.",
        },
    ]

    # Escalation alerts
    escalation_alerts = []
    for r in risks:
        if r.get("level") == "Critical":
            escalation_alerts.append({
                "alert": f"CRITICAL: {r['title']}",
                "action_required": "Immediate leadership briefing",
                "detail": r["detail"][:100],
            })

    return {
        "trend_implications": trend_implications,
        "escalating_risks": escalating_risks,
        "emerging_opportunities": emerging_opps,
        "leadership_actions": leadership_actions,
        "diaspora_leadership_actions": diaspora_actions,
        "escalation_alerts": escalation_alerts,
        "decision_support_summary": (
            f"With {days_to_election} days to the 2027 election and electoral discourse at {sov:.0f}% share of voice, "
            f"RTIFN is in the {'preparation' if days_to_election > 180 else 'active engagement'} phase of its electoral intelligence cycle. "
            f"{'Proactive positioning now will establish RTIFN credibility before the discourse space becomes contested.' if days_to_election > 180 else 'Active engagement is required to maintain RTIFN visibility in the increasingly competitive electoral discourse environment.'}"
        ),
    }

# ─── Main entry point ─────────────────────────────────────────────────────────
def generate_full_election_intelligence(db: Session, days: int = 30) -> dict:
    from app.services.source_quality import get_source_quality_report
    narratives = get_narrative_analysis(db, days)
    elections = next((n for n in narratives if n["narrative"] == "Elections & Democracy"), {
        "share_of_voice": 0, "count": 0, "sentiment_label": "neutral",
        "momentum": 0, "momentum_direction": "stable", "confidence_label": "Low"
    })
    source_quality = get_source_quality_report(db, days)
    now = datetime.now(timezone.utc)
    days_to_election = (ELECTION_DATE - now).days
    phase = get_election_phase(days_to_election)

    assessment = generate_election_assessment(elections, phase, days, days_to_election)
    why_matters = generate_election_why_it_matters(elections, phase, days_to_election, narratives)
    implications = generate_election_implications(elections, phase, days_to_election)
    risks = generate_election_risks(elections, narratives, days_to_election)
    opportunities = generate_election_opportunities(elections, narratives, days_to_election)
    outlook = generate_election_outlook(elections, phase, days_to_election, risks, opportunities)
    monitoring = generate_election_monitoring_priorities()
    confidence = generate_election_confidence(elections, source_quality)
    briefing = generate_executive_election_briefing(
        assessment, why_matters, implications, risks,
        opportunities, outlook, monitoring, confidence,
        days_to_election, phase
    )

    # Add Election Implications Engine
    election_implications = generate_election_implications_engine(
        elections, phase, days_to_election, narratives, risks, opportunities, db=db
    )

    # V5.7 — Election Narrative Granularity Engine
    try:
        from app.services.election_subcategory import get_election_subcategory_breakdown
        subcategory_breakdown = get_election_subcategory_breakdown(db, days)
    except Exception:
        subcategory_breakdown = None

    result = {
        "generated_at": now.isoformat(),
        "period_days": days,
        "days_to_election": days_to_election,
        "election_phase": phase,
        "assessment": assessment,
        "why_it_matters": why_matters,
        "strategic_implications": implications,
        "risks": risks,
        "opportunities": opportunities,
        "outlook": outlook,
        "monitoring_priorities": monitoring,
        "confidence": confidence,
        "executive_briefing": briefing,
        "election_narrative": elections,
        "election_implications": election_implications,
        "election_subcategories": subcategory_breakdown,
        "monitoring_note": "This framework monitors publicly available discourse only. It does not target individuals, influence voters, or engage in political communication. Intelligence is for strategic awareness purposes only.",
    }

    # V5.8 Phase F — Election Intelligence module self-evaluation.
    # Track the election outlook, top risk, and top opportunity as evaluable
    # recommendations contributing to outlook/risk/opportunity accuracy.
    try:
        from app.services.recommendation_tracker import record_recommendation
        seven_day = outlook.get("7_day", {}) if isinstance(outlook, dict) else {}
        outlook_text = seven_day.get("outlook", "") if isinstance(seven_day, dict) else str(seven_day)
        record_recommendation(
            db,
            narrative="Elections & Democracy",
            recommendation_text=outlook_text,
            category="MONITOR",
            priority="Medium",
            confidence=elections.get("confidence_label", "Medium"),
            time_horizon="7 days",
            supporting_evidence=f"{elections.get('count', 0)} electoral mentions, phase={phase.get('phase', 'Unknown') if isinstance(phase, dict) else phase}",
            expected_outcome="Electoral discourse trajectory consistent with 7-day outlook",
            trigger_metric_name="share_of_voice",
            trigger_metric_value=float(elections.get("share_of_voice", 0)),
            period_days=days,
            module="election_intelligence",
        )
        if risks:
            top_risk = risks[0]
            record_recommendation(
                db,
                narrative="Elections & Democracy",
                recommendation_text=top_risk.get("title", "") + " — " + top_risk.get("description", ""),
                category="ESCALATE" if str(top_risk.get("level", "")).lower() in ("high", "critical") else "MONITOR",
                priority=str(top_risk.get("level", "Medium")).title(),
                confidence="Medium",
                time_horizon="14 days",
                supporting_evidence="Election Risk Engine",
                expected_outcome="Risk materialises or resolves consistent with assessed level",
                trigger_metric_name="share_of_voice",
                trigger_metric_value=float(elections.get("share_of_voice", 0)),
                period_days=days,
                module="election_intelligence",
            )
        if opportunities:
            top_opp = opportunities[0]
            record_recommendation(
                db,
                narrative="Elections & Democracy",
                recommendation_text=top_opp.get("title", "") + " — " + top_opp.get("description", ""),
                category="ENGAGE",
                priority=str(top_opp.get("rank", "Medium")).title(),
                confidence="Medium",
                time_horizon="30 days",
                supporting_evidence="Election Opportunity Engine",
                expected_outcome="Opportunity window remains open consistent with assessed priority",
                trigger_metric_name="share_of_voice",
                trigger_metric_value=float(elections.get("share_of_voice", 0)),
                period_days=days,
                module="election_intelligence",
            )
    except Exception:
        try:
            db.rollback()
        except Exception:
            pass

    return result
