"""
Narrative Intelligence Service v2
Strategic Narrative Framework — executive-grade insights.
Every finding answers: Why does this matter? What changed? What should leadership monitor?
"""
from datetime import datetime, timezone, timedelta
from sqlalchemy.orm import Session

from app.analytics.engine import compute_all_metrics, get_engagement_by_type, get_geography
from app.analytics.intelligence import get_sentiment_trends, get_top_entities, get_emerging_topics
from app.analytics.strategic_narratives import (
    get_narrative_analysis, get_underrepresented_narratives,
    generate_strategic_insight, generate_opportunity_insights,
)


def interpret_sentiment(score):
    if score >= 0.4: return "Public conversation is strongly positive — community reputation appears strong."
    elif score >= 0.2: return "The overall tone of public discussion is encouraging and broadly positive."
    elif score >= 0.05: return "Sentiment is slightly positive — public discourse is generally constructive."
    elif score >= -0.05: return "Public discussion is neutral — no strong positive or negative lean detected."
    elif score >= -0.2: return "Some concerns are emerging in public conversation — worth monitoring."
    elif score >= -0.4: return "Public discussion has a notably critical tone — leadership attention recommended."
    else: return "Significant negativity detected in public discourse — requires immediate review."


def interpret_sentiment_shift(shift):
    if shift >= 0.15: return f"Sentiment improved significantly (+{shift*100:.0f}%) — a meaningful positive shift."
    elif shift >= 0.05: return f"Sentiment improved slightly (+{shift*100:.0f}%) this period."
    elif shift >= -0.05: return "Sentiment remained stable — no significant shift in public tone."
    elif shift >= -0.15: return f"Sentiment declined slightly ({shift*100:.0f}%) — worth monitoring."
    else: return f"Sentiment declined significantly ({shift*100:.0f}%) — warrants leadership attention."


def interpret_engagement(index):
    if index >= 2.0: return f"Community engagement is very high (index: {index:.2f}) — registered participants are interacting frequently across multiple channels."
    elif index >= 1.0: return f"Community engagement is strong (index: {index:.2f}) — good participation levels across key channels."
    elif index >= 0.5: return f"Community engagement is moderate (index: {index:.2f}) — reasonable participation with room to grow."
    elif index >= 0.2: return f"Community engagement is below target (index: {index:.2f}) — most participants are not yet actively engaged."
    else: return f"Community engagement is very low (index: {index:.2f}) — urgent attention needed."


def interpret_growth(rate):
    if rate >= 0.1: return f"Strong growth — participant numbers increased by {rate*100:.1f}% this period."
    elif rate >= 0.02: return f"Steady growth — a {rate*100:.1f}% increase in registered participants."
    elif rate >= -0.02: return "Participation numbers are stable — no significant change this period."
    elif rate >= -0.1: return f"Slight decline of {abs(rate)*100:.1f}% in participation — consider re-engagement."
    else:
        if abs(rate) > 0.9: return "Note: Growth rate comparison is limited by data history. Participation tracking is active and building baseline."
        return f"Significant decline of {abs(rate)*100:.1f}% — requires immediate leadership attention."


def identify_risks(metrics, sentiment_shift, narrative_results, underrepresented):
    risks = []
    if metrics["growth_rate"] < -0.05 and abs(metrics["growth_rate"]) < 0.5:
        risks.append({"level": "HIGH", "title": "Declining Community Participation",
            "detail": f"Registered participation dropped by {abs(metrics['growth_rate'])*100:.1f}%. Community reach and influence may weaken.",
            "action": "Review outreach channels and launch a re-engagement campaign.",
            "confidence_label": "High", "evidence_count": metrics["total_participants"]})
    elif metrics["growth_rate"] < -0.5:
        risks.append({"level": "WATCH", "title": "Participation Baseline Building",
            "detail": "Growth rate comparison is limited by early-stage data history. The platform is actively building its baseline for accurate trend tracking.",
            "action": "Continue data collection — comparative analytics will improve over the next 30 days.",
            "confidence_label": "Low", "evidence_count": metrics["total_participants"]})
    if metrics["sentiment_score"] < -0.2:
        risks.append({"level": "HIGH", "title": "Negative Public Sentiment",
            "detail": "The overall tone of monitored discourse is negative. This may affect reputation and recruitment.",
            "action": "Review communications strategy and address key public concerns.",
            "confidence_label": "High", "evidence_count": metrics["total_engagements"]})
    if sentiment_shift < -0.15:
        risks.append({"level": "MEDIUM", "title": "Worsening Sentiment Trend",
            "detail": f"Public sentiment declined {abs(sentiment_shift)*100:.0f}% vs previous period.",
            "action": "Identify the source of negative sentiment and prepare a response.",
            "confidence_label": "Medium", "evidence_count": 0})
    for nar in narrative_results:
        if nar["sentiment_label"] == "negative" and nar["momentum_direction"] == "rising" and nar["share_of_voice"] > 10:
            risks.append({"level": "MEDIUM", "title": f"Rising Negative Coverage: {nar['narrative']}",
                "detail": f"Negative discussion about {nar['narrative'].lower()} increased {nar['momentum']:.0f}%, representing {nar['share_of_voice']:.0f}% of discourse.",
                "action": f"Monitor {nar['narrative'].lower()} coverage and prepare a response.",
                "confidence_label": nar["confidence_label"], "evidence_count": nar["count"]})
    for alert in underrepresented[:2]:
        risks.append({"level": "WATCH", "title": f"Coverage Gap: {alert['narrative']}",
            "detail": alert["message"], "action": "Expand monitoring queries for this narrative.",
            "confidence_label": "Low", "evidence_count": 0})
    return risks


def generate_key_findings(metrics, sentiment_shift, narrative_results, entities, emerging):
    findings = []
    used_narratives = set()
    # Finding 1: Participation
    findings.append({"finding": f"The intelligence platform is tracking {metrics['total_participants']} registered participants. {interpret_growth(metrics['growth_rate'])}", "why_it_matters": "Participation levels are the foundation of community influence and reach.", "confidence_label": "High", "source_count": 1, "evidence_count": metrics["total_participants"]})
    # Finding 2: Top narrative
    if narrative_results:
        top = narrative_results[0]
        used_narratives.add(top["narrative"])
        findings.append({"finding": generate_strategic_insight(top, 0), "why_it_matters": top["description"], "confidence_label": top["confidence_label"], "source_count": top["source_count"], "evidence_count": top["count"]})
    # Finding 3: Sentiment
    findings.append({"finding": f"{interpret_sentiment(metrics['sentiment_score'])} {interpret_sentiment_shift(sentiment_shift)}", "why_it_matters": "Public sentiment shapes community reputation and influences new participant engagement.", "confidence_label": "High" if abs(sentiment_shift) > 0.1 else "Medium", "source_count": len([n for n in narrative_results if n["count"] > 0]), "evidence_count": sum(n["count"] for n in narrative_results)})
    # Finding 4: Second distinct narrative - never repeats finding 2
    second = next((n for n in narrative_results if n["narrative"] not in used_narratives and n["share_of_voice"] > 5), None)
    if second:
        used_narratives.add(second["narrative"])
        findings.append({"finding": generate_strategic_insight(second, 1), "why_it_matters": second["description"], "confidence_label": second["confidence_label"], "source_count": second["source_count"], "evidence_count": second["count"]})
    # Finding 5: Engagement
    findings.append({"finding": interpret_engagement(metrics["engagement_index"]), "why_it_matters": "Engagement levels show how actively the community interacts with RTIFN programmes.", "confidence_label": "High", "source_count": 1, "evidence_count": metrics["total_engagements"]})
    return findings[:5]


def _detect_changes(metrics, sentiment_shift, narrative_results):
    changes = []
    if abs(sentiment_shift) > 0.05:
        d = "improved" if sentiment_shift > 0 else "declined"
        changes.append(f"Public sentiment {d} by {abs(sentiment_shift)*100:.0f}% compared to the previous period.")
    if metrics["growth_rate"] > 0.02:
        changes.append(f"Community participation grew by {metrics['growth_rate']*100:.1f}%.")
    elif metrics["growth_rate"] < -0.5:
        changes.append("Participation baseline is being established — comparative tracking will improve as more historical data accumulates.")
    elif metrics["growth_rate"] < -0.02:
        changes.append(f"Community participation decreased by {abs(metrics['growth_rate'])*100:.1f}%.")
    for nar in narrative_results[:2]:
        if abs(nar["momentum"]) > 20:
            d = "increased" if nar["momentum"] > 0 else "decreased"
            changes.append(f"Coverage of {nar['narrative']} {d} by {abs(nar['momentum']):.0f}%.")
    if not changes:
        changes.append("No significant changes detected — situation is stable.")
    return changes


def _generate_outlook(metrics, sentiment_shift, risks, opportunities):
    high = [r for r in risks if r["level"] == "HIGH"]
    medium = [r for r in risks if r["level"] == "MEDIUM"]
    if high:
        return (f"The outlook requires immediate attention. {len(high)} high-priority issue(s) identified. "
                "Leadership should review engagement and communications strategy this week.")
    elif medium and not opportunities:
        return ("The outlook is cautiously stable. Areas of concern exist but no immediate crisis. "
                "Proactive steps over the next 2-4 weeks are recommended.")
    elif opportunities and sentiment_shift >= 0:
        return ("The outlook is positive. Sentiment is stable or improving with clear opportunities. "
                "This is a good period for new community initiatives.")
    else:
        return ("The outlook is broadly stable. Continue routine monitoring and maintain regular "
                "community engagement to sustain current participation levels.")


def generate_situation_room(db: Session, days: int = 7) -> dict:
    now = datetime.now(timezone.utc)
    metrics = compute_all_metrics(db, max(days, 30))  # use min 30 days for stable metrics
    sentiment_trends = get_sentiment_trends(db, days)
    narrative_results = get_narrative_analysis(db, days)
    entities = get_top_entities(db, days, limit=10)
    emerging = get_emerging_topics(db, days)
    underrepresented = get_underrepresented_narratives(narrative_results, days)

    recent = [t["avg_score"] for t in sentiment_trends[-3:]] if sentiment_trends else []
    older = [t["avg_score"] for t in sentiment_trends[:3]] if len(sentiment_trends) > 3 else []
    sentiment_shift = round((sum(recent)/len(recent) - sum(older)/len(older)) if recent and older else 0.0, 4)

    key_findings = generate_key_findings(metrics, sentiment_shift, narrative_results, entities, emerging)
    risks = identify_risks(metrics, sentiment_shift, narrative_results, underrepresented)
    opportunities = generate_opportunity_insights(narrative_results)
    changes = _detect_changes(metrics, sentiment_shift, narrative_results)
    outlook = _generate_outlook(metrics, sentiment_shift, risks, opportunities)

    narrative_sov = [{
        "narrative": n["narrative"], "share_of_voice": n["share_of_voice"],
        "momentum": n["momentum"], "momentum_direction": n["momentum_direction"],
        "sentiment_label": n["sentiment_label"], "confidence_label": n["confidence_label"],
        "source_count": n["source_count"], "count": n["count"],
        "strategic_insight": generate_strategic_insight(n, i),
    } for i, n in enumerate(narrative_results[:8])]

    emerging_enriched = [{
        "topic": t["topic"].title(), "category": t.get("category", "Other"),
        "velocity": t["velocity"],
        "plain_english": (f"Discussion of {t['topic'].title()} surged significantly — a rapidly emerging subject." if t["velocity"] >= 2
                          else f"{t['topic'].title()} is gaining momentum in public conversation."),
        "confidence_label": "High" if t["velocity"] >= 2 else "Medium",
    } for t in emerging[:5]]

    total_sources = len(set(s for n in narrative_results for s in n.get("sources", [])))
    exec_summary = (
        f"Over the past {days} days, the National & Diaspora Intelligence Platform (NDIP) monitored discourse across "
        f"{total_sources} active source{'s' if total_sources != 1 else ''}. "
        f"{interpret_engagement(metrics['engagement_index'])} "
        f"{interpret_sentiment(metrics['sentiment_score'])} "
        f"{interpret_sentiment_shift(sentiment_shift)} "
        f"{'There are ' + str(len([r for r in risks if r['level'] in ('HIGH','MEDIUM')])) + ' issue(s) requiring leadership attention.' if [r for r in risks if r['level'] in ('HIGH','MEDIUM')] else 'No critical issues detected this period.'}"
    )

    result = {
        "generated_at": now.isoformat(), "period_days": days,
        "executive_summary": exec_summary,
        "key_findings": key_findings,
        "narrative_share_of_voice": narrative_sov,
        "underrepresented_narratives": underrepresented,
        "risks": risks, "opportunities": opportunities,
        "significant_changes": changes,
        "emerging_topics": emerging_enriched,
        "outlook": outlook,
        "what_matters_most": key_findings[0]["finding"] if key_findings else "Insufficient data.",
        "recommended_monitoring": [r["title"] for r in risks if r["level"] in ("HIGH","MEDIUM")][:3] or ["Continue routine monitoring."],
        "metrics_summary": {
            "participants": metrics["total_participants"],
            "engagement_plain": interpret_engagement(metrics["engagement_index"]),
            "sentiment_plain": interpret_sentiment(metrics["sentiment_score"]),
            "growth_plain": interpret_growth(metrics["growth_rate"]),
            "sentiment_score": metrics["sentiment_score"],
            "engagement_index": metrics["engagement_index"],
            "growth_rate": metrics["growth_rate"],
        },
    }

    # V5.8 Phase F — track Situation Room's outlook and top risk as evaluable
    # recommendations, contributing to its module self-evaluation.
    try:
        from app.services.recommendation_tracker import record_recommendation
        record_recommendation(
            db,
            narrative=narrative_sov[0]["narrative"] if narrative_sov else None,
            recommendation_text=outlook if isinstance(outlook, str) else str(outlook),
            category="MONITOR",
            priority="Medium",
            confidence="Medium",
            time_horizon="14 days",
            supporting_evidence=f"Situation Room outlook, engagement_index={metrics['engagement_index']}",
            expected_outcome="Narrative competition and engagement trends consistent with outlook",
            trigger_metric_name="engagement_index",
            trigger_metric_value=float(metrics["engagement_index"]),
            period_days=days,
            module="situation_room",
        )
        if risks:
            top_risk = risks[0]
            record_recommendation(
                db,
                narrative=narrative_sov[0]["narrative"] if narrative_sov else None,
                recommendation_text=top_risk.get("title", "") + " — " + top_risk.get("description", ""),
                category="ESCALATE" if top_risk.get("level") == "HIGH" else "MONITOR",
                priority=top_risk.get("level", "Medium").title(),
                confidence="Medium",
                time_horizon="14 days",
                supporting_evidence="Situation Room risk identification",
                expected_outcome="Risk materialises or resolves consistent with assessed level",
                trigger_metric_name="sentiment_score",
                trigger_metric_value=float(metrics["sentiment_score"]),
                period_days=days,
                module="situation_room",
            )
    except Exception:
        try:
            db.rollback()
        except Exception:
            pass

    return result


def generate_brief(db: Session, period: str = "weekly", days: int = 7) -> dict:
    room = generate_situation_room(db, days)
    metrics = compute_all_metrics(db, max(days, 30))  # use min 30 days for stable metrics
    eng_by_type = get_engagement_by_type(db, days)
    geography = get_geography(db)
    narrative_results = get_narrative_analysis(db, days)

    top_types = sorted(eng_by_type.items(), key=lambda x: x[1], reverse=True)
    eng_overview = "Community engagement was driven primarily by "
    if top_types:
        names = [t[0].replace("_", " ") for t in top_types[:2]]
        eng_overview += " and ".join(names) + f", totalling {metrics['total_engagements']} interactions."
    else:
        eng_overview = "No engagement events recorded this period."

    top_countries = [g["country"] for g in geography[:3] if g["country"]]
    geo_overview = f"Participants are primarily based in {', '.join(top_countries)}." if top_countries else "Geographic data not yet available."

    return {
        "brief_type": period, "period_days": days,
        "generated_at": room["generated_at"],
        "executive_summary": room["executive_summary"],
        "key_findings": room["key_findings"],
        "engagement_overview": eng_overview,
        "geographic_overview": geo_overview,
        "narrative_analysis": [generate_strategic_insight(n, i) for i, n in enumerate(narrative_results[:4])],
        "narrative_share_of_voice": room["narrative_share_of_voice"],
        "sentiment_analysis": room["metrics_summary"]["sentiment_plain"],
        "risks": room["risks"], "opportunities": room["opportunities"],
        "emerging_topics": room["emerging_topics"],
        "recommended_monitoring": room["recommended_monitoring"],
        "outlook": room["outlook"],
    }
