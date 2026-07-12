"""
Advanced Risk & Opportunity Intelligence Engine
Classifies: Information / Watch / Warning / Critical
Ranks opportunities: High / Medium / Low
Every item includes rationale, evidence count, confidence.
"""
from datetime import datetime, timedelta, timezone
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.analytics.strategic_narratives import get_narrative_analysis, STRATEGIC_NARRATIVES
from app.analytics.engine import compute_all_metrics
from app.analytics.intelligence import get_sentiment_trends, get_source_comparison


# ─── Risk Intelligence Engine ─────────────────────────────────────────────────

def detect_all_risks(db: Session, days: int = 7) -> list[dict]:
    """
    Comprehensive risk detection across 6 categories:
    - Sentiment deterioration
    - Engagement decline
    - Monitoring blind spots
    - Narrative concentration
    - Source concentration
    - Data quality issues
    """
    risks = []
    metrics = compute_all_metrics(db, max(days, 30))
    narrative_results = get_narrative_analysis(db, days)
    sentiment_trends = get_sentiment_trends(db, days)
    sources = get_source_comparison(db, days)

    # ── Sentiment deterioration ──
    if sentiment_trends and len(sentiment_trends) >= 4:
        recent = [t["avg_score"] for t in sentiment_trends[-3:]]
        older = [t["avg_score"] for t in sentiment_trends[:3]]
        shift = (sum(recent)/len(recent)) - (sum(older)/len(older)) if recent and older else 0
        if shift < -0.3:
            risks.append(_risk("Critical", "Severe Sentiment Deterioration",
                f"Public sentiment declined by {abs(shift)*100:.0f}% over the monitoring period. This is a significant reputational signal.",
                "Commission urgent review of public communications and identify key sources of negativity.",
                confidence="High", evidence=sum(t["total"] for t in sentiment_trends)))
        elif shift < -0.15:
            risks.append(_risk("Warning", "Sentiment Declining",
                f"Public sentiment declined by {abs(shift)*100:.0f}% compared to the start of the monitoring period.",
                "Monitor sentiment daily and prepare a proactive communications response.",
                confidence="Medium", evidence=sum(t["total"] for t in sentiment_trends)))

    # ── Engagement decline ──
    if metrics["growth_rate"] < -0.1 and abs(metrics["growth_rate"]) < 0.7:
        risks.append(_risk("Warning", "Participation Declining",
            f"Registered participation dropped by {abs(metrics['growth_rate'])*100:.1f}%. Sustained decline will reduce community reach.",
            "Review outreach channels. Consider targeted re-engagement campaign.",
            confidence="High", evidence=metrics["total_participants"]))
    elif metrics["engagement_index"] < 0.5:
        risks.append(_risk("Watch", "Low Engagement Index",
            f"Engagement index is {metrics['engagement_index']:.2f} — below the 0.5 threshold. Most registered participants are not actively engaging.",
            "Review programme relevance and communication frequency.",
            confidence="Medium", evidence=metrics["total_engagements"]))

    # ── Narrative concentration ──
    if narrative_results:
        top_share = narrative_results[0]["share_of_voice"]
        if top_share > 60:
            risks.append(_risk("Watch", "Narrative Concentration Risk",
                f"**{narrative_results[0]['narrative']}** accounts for {top_share:.0f}% of all discourse — over-concentration in one narrative reduces intelligence breadth.",
                "Expand monitoring queries to improve coverage across multiple narrative categories.",
                confidence="High", evidence=narrative_results[0]["count"]))

    # ── Source concentration ──
    if sources:
        total_volume = sum(s["total"] for s in sources)
        if total_volume > 0:
            top_source_share = max(s["total"] for s in sources) / total_volume * 100
            if top_source_share > 70:
                top_source = max(sources, key=lambda x: x["total"])
                risks.append(_risk("Watch", "Source Concentration Risk",
                    f"**{top_source['platform'].replace('_',' ').title()}** accounts for {top_source_share:.0f}% of all monitored content. Intelligence may be biased toward one source's perspective.",
                    "Add additional API connectors to diversify source coverage.",
                    confidence="Medium", evidence=total_volume))

    # ── Monitoring blind spots ──
    present_narratives = {n["narrative"] for n in narrative_results}
    for narrative, config in STRATEGIC_NARRATIVES.items():
        if config["weight"] >= 1.2 and narrative not in present_narratives:
            risks.append(_risk("Information", f"Monitoring Gap: {narrative}",
                f"No coverage detected for **{narrative}** — a high-priority monitoring category. Intelligence may be incomplete.",
                f"Add search queries targeting {narrative.lower()} topics to the daily ingest.",
                confidence="Low", evidence=0))

    # ── Data quality ──
    from app.models.models import NormalisedPost
    total_posts = db.query(func.count(NormalisedPost.id)).scalar() or 0
    processed = db.query(func.count(NormalisedPost.id)).filter(
        NormalisedPost.nlp_processed == True
    ).scalar() or 0

    if total_posts > 0 and processed / total_posts < 0.8:
        # Distinguish "haven't run it in a while" (low severity, the
        # existing check) from "ran and is actively failing" (high
        # severity, new check) — a stuck backlog percentage looks
        # identical either way unless we actually test the pipeline.
        from app.analytics.intelligence import check_nlp_pipeline_health
        health = check_nlp_pipeline_health(db, sample_size=10)
        if health["sample_size"] > 0 and health["error_rate"] >= 0.5:
            risks.append(_risk("Warning", "NLP Pipeline Failing",
                f"The NLP processing pipeline is actively failing — {health['errors']} of "
                f"{health['sample_size']} sampled posts errored on a live test "
                f"({health['error_rate']*100:.0f}% failure rate). Running the pipeline will "
                f"NOT resolve this; it requires a code fix. Sample error: {health['sample_error']}",
                "Escalate to engineering immediately — this is a code defect, not a backlog. "
                "Check recent changes to entity/topic/sentiment extraction logic.",
                confidence="High", evidence=health["sample_size"]))
        else:
            risks.append(_risk("Information", "NLP Processing Backlog",
                f"Only {processed/total_posts*100:.0f}% of ingested records have been NLP-processed. Intelligence quality may be affected.",
                "Run the NLP processing pipeline via the Data Health page.",
                confidence="High", evidence=total_posts))

    return risks


def _risk(level, title, detail, action, confidence="Medium", evidence=0):
    level_order = {"Critical": 0, "Warning": 1, "Watch": 2, "Information": 3}
    return {
        "level": level,
        "level_order": level_order.get(level, 3),
        "title": title,
        "detail": detail,
        "action": action,
        "confidence_label": confidence,
        "evidence_count": evidence,
        "rationale": f"Based on {evidence} data points with {confidence.lower()} confidence.",
    }


# ─── Advanced Opportunity Detection ──────────────────────────────────────────

def detect_all_opportunities(db: Session, days: int = 7) -> list[dict]:
    """
    Ranked opportunity detection across 5 categories:
    - Rising positive engagement
    - Underutilised narratives
    - Rapidly growing topics
    - High-interest diaspora discussions
    - Emerging public concerns
    """
    opportunities = []
    narrative_results = get_narrative_analysis(db, days)
    metrics = compute_all_metrics(db, max(days, 30))
    sentiment_trends = get_sentiment_trends(db, days)

    # ── Rising positive narratives ──
    for nar in narrative_results:
        if nar["sentiment_label"] == "positive" and nar["momentum"] > 50 and nar["share_of_voice"] > 5:
            rank = "High" if nar["momentum"] > 200 else "Medium"
            opportunities.append(_opp(rank,
                f"Amplify Positive {nar['narrative']} Coverage",
                f"Positive discussion about **{nar['narrative']}** is growing strongly ({nar['share_of_voice']:.0f}% share of voice, positive sentiment). "
                f"This is an ideal moment to amplify constructive narratives through official channels.",
                f"Issue a public statement or content series engaging with {nar['narrative']} themes.",
                confidence=nar["confidence_label"], evidence=nar["count"], source_count=nar["source_count"]))

    # ── Diaspora engagement window ──
    diaspora = next((n for n in narrative_results if n["narrative"] == "Global Nigerian Engagement"), None)
    if diaspora and diaspora["share_of_voice"] > 20:
        opportunities.append(_opp("High",
            "High Diaspora Engagement Window",
            f"Global Nigerian Engagement content represents {diaspora['share_of_voice']:.0f}% of monitored discourse — the highest strategic priority for RTIFN. "
            "This is an exceptional window for community outreach and engagement campaigns.",
            "Launch a targeted community engagement initiative or membership drive.",
            confidence=diaspora["confidence_label"], evidence=diaspora["count"], source_count=diaspora["source_count"]))

    # ── Underutilised narratives ──
    for nar in narrative_results:
        if nar["share_of_voice"] < 5 and nar["sentiment_label"] == "positive" and STRATEGIC_NARRATIVES.get(nar["narrative"], {}).get("weight", 0) >= 1.0:
            opportunities.append(_opp("Low",
                f"Underutilised Positive Narrative: {nar['narrative']}",
                f"**{nar['narrative']}** has positive coverage but low share of voice ({nar['share_of_voice']:.0f}%). "
                "There is an opportunity to amplify this narrative before it fades.",
                f"Create content or commentary addressing {nar['narrative']} to increase share of voice.",
                confidence="Low", evidence=nar["count"], source_count=nar["source_count"]))

    # ── Engagement spike ──
    if metrics["engagement_index"] > 2.0:
        opportunities.append(_opp("High",
            "High Engagement Window — Act Now",
            f"Community engagement is very high (index: {metrics['engagement_index']:.2f}). "
            "This is the optimal time to launch new initiatives, surveys, or calls to action.",
            "Plan a major community event, survey, or fundraising initiative this week.",
            confidence="High", evidence=metrics["total_engagements"], source_count=1))

    # ── Positive sentiment momentum ──
    if sentiment_trends and len(sentiment_trends) >= 4:
        recent = [t["avg_score"] for t in sentiment_trends[-3:]]
        older = [t["avg_score"] for t in sentiment_trends[:3]]
        shift = (sum(recent)/len(recent)) - (sum(older)/len(older)) if recent and older else 0
        if shift > 0.1:
            opportunities.append(_opp("Medium",
                "Improving Sentiment — Communications Opportunity",
                f"Public sentiment improved by {shift*100:.0f}% during this period. "
                "Positive momentum in public discourse provides an ideal backdrop for outreach.",
                "Issue public communications highlighting community achievements and progress.",
                confidence="Medium", evidence=sum(t["total"] for t in sentiment_trends), source_count=3))

    # Sort by rank
    rank_order = {"High": 0, "Medium": 1, "Low": 2}
    opportunities.sort(key=lambda x: rank_order.get(x["rank"], 2))
    return opportunities[:6]


def _opp(rank, title, detail, action, confidence="Medium", evidence=0, source_count=1):
    return {
        "rank": rank,
        "title": title,
        "detail": detail,
        "action": action,
        "confidence_label": confidence,
        "evidence_count": evidence,
        "source_count": source_count,
        "rationale": f"Based on {evidence} data points across {source_count} source{'s' if source_count != 1 else ''}.",
    }
