"""
NDIP National Pulse Executive Intelligence v5.4
Transforms National Pulse from score dashboard into executive intelligence flagship.
"""
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from app.analytics.strategic_narratives import get_narrative_analysis


def generate_national_pulse_executive(db: Session, days: int, pulse_score: int, pulse_label: str) -> dict:
    from app.analytics.engine import compute_all_metrics
    from app.services.risk_opportunity import detect_all_risks, detect_all_opportunities
    from app.services.source_quality import get_source_quality_report

    narratives = get_narrative_analysis(db, days)
    risks = detect_all_risks(db, days)
    opportunities = detect_all_opportunities(db, days)
    source_quality = get_source_quality_report(db, days)

    gov = next((n for n in narratives if n["narrative"] == "Governance"), None)
    econ = next((n for n in narratives if n["narrative"] == "Economy"), None)
    sec = next((n for n in narratives if n["narrative"] == "Security"), None)
    diaspora = next((n for n in narratives if n["narrative"] == "Global Nigerian Engagement"), None)
    elections = next((n for n in narratives if n["narrative"] == "Elections & Democracy"), None)

    # Executive Assessment
    if pulse_score >= 75:
        pulse_context = "The national discourse environment is broadly positive and stable — a favourable period for diaspora engagement and community initiatives."
    elif pulse_score >= 55:
        pulse_context = "Nigeria's public discourse is stable with no critical concerns. Established narratives are maintaining their positions without significant disruption."
    elif pulse_score >= 40:
        pulse_context = "The national discourse environment shows signs of moderate stress. Specific narrative areas warrant leadership monitoring."
    else:
        pulse_context = "The national discourse environment indicates elevated concern across multiple narrative areas. Leadership attention is recommended."

    narrative_landscape = ""
    if gov and econ:
        g_e_ratio = round(gov["share_of_voice"] / max(econ["share_of_voice"], 0.1), 1)
        narrative_landscape = (
            f"Governance remains the dominant national narrative, attracting {g_e_ratio}x more attention than "
            f"economic issues — indicating leadership performance and institutional effectiveness remain the "
            f"primary drivers of public discourse. "
        )
    if sec and sec["share_of_voice"] > 10:
        narrative_landscape += (
            f"Security discourse at {sec['share_of_voice']:.0f}% share of voice represents a persistent thread "
            f"that warrants {'immediate attention' if sec['sentiment_label'] == 'negative' else 'continued monitoring'}. "
        )
    if diaspora and diaspora["share_of_voice"] > 20:
        narrative_landscape += (
            f"Strong diaspora engagement narrative ({diaspora['share_of_voice']:.0f}%) indicates overseas "
            f"Nigerian communities are actively engaged with national developments."
        )

    executive_assessment = f"{pulse_context} {narrative_landscape}".strip()

    # Why It Matters
    why_matters = []
    if diaspora and diaspora["share_of_voice"] > 25:
        why_matters.append(
            f"Global Nigerian Engagement dominates at {diaspora['share_of_voice']:.0f}% — directly reflecting "
            f"RTIFN's core mission environment. High diaspora engagement is a leading indicator of community mobilisation readiness."
        )
    if gov:
        if gov["sentiment_label"] == "negative":
            why_matters.append(
                "Negative governance sentiment signals declining institutional trust — a pattern that historically "
                "precedes increased diaspora advocacy activity and community pressure for policy responses."
            )
        else:
            why_matters.append(
                f"Positive governance sentiment ({gov['share_of_voice']:.0f}%) creates a constructive environment "
                f"for diaspora-government engagement and policy advocacy positioning."
            )
    if sec and sec["share_of_voice"] > 12:
        why_matters.append(
            f"Security discourse at {sec['share_of_voice']:.0f}% directly affects diaspora decisions about "
            f"visiting Nigeria, investing, and encouraging family return migration."
        )
    if elections:
        why_matters.append(
            f"Electoral discourse at {elections['share_of_voice']:.0f}% — with 230+ days to the 2027 election — "
            f"represents early civic mobilisation signals that RTIFN should monitor and engage with proactively."
        )
    if not why_matters:
        why_matters.append(
            "Current discourse patterns enable RTIFN to calibrate community communications and engagement strategies "
            "based on real-time public intelligence."
        )

    # What Changed
    changes = []
    surging = sorted([n for n in narratives if n["momentum_direction"] == "rising" and n["momentum"] > 50],
                     key=lambda x: x["momentum"], reverse=True)
    declining = [n for n in narratives if n["momentum_direction"] == "falling" and n["momentum"] < -20]

    for n in surging[:3]:
        if n["momentum"] > 200:
            desc = f"**{n['narrative']}** surged {n['momentum']:.0f}% — an exceptional acceleration typically indicating a significant triggering event or sustained media campaign."
        elif n["momentum"] > 100:
            desc = f"**{n['narrative']}** more than doubled ({n['momentum']:.0f}%) — genuine increased public attention rather than normal variation."
        else:
            desc = f"**{n['narrative']}** grew {n['momentum']:.0f}% — a meaningful build in public attention."
        changes.append({"narrative": n["narrative"], "direction": "rising", "momentum": n["momentum"], "description": desc})

    for n in declining[:1]:
        desc = f"**{n['narrative']}** declined {abs(n['momentum']):.0f}% — {'a significant retreat suggesting narrative displacement' if n['momentum'] < -50 else 'a moderate decline'}."
        changes.append({"narrative": n["narrative"], "direction": "falling", "momentum": n["momentum"], "description": desc})

    if not changes:
        changes.append({"narrative": "All", "direction": "stable", "momentum": 0,
                        "description": "Discourse patterns remained broadly stable. No significant narrative shifts detected."})

    # Leadership Watch Items
    watch_items = []
    for r in [r for r in risks if r.get("level") in ("Critical", "Warning")][:2]:
        watch_items.append({"item": r["title"], "urgency": "High" if r.get("level") == "Warning" else "Critical",
                            "reason": r["detail"][:150], "monitoring": "Daily"})
    for n in surging[:2]:
        if n.get("sentiment_label") == "negative":
            watch_items.append({"item": f"{n['narrative']} — Negative Surge", "urgency": "High",
                                "reason": f"Negative sentiment + {n['momentum']:.0f}% growth = leading risk indicator.", "monitoring": "Daily"})
    if elections and elections["momentum"] > 200:
        watch_items.append({"item": f"Electoral Discourse Surge ({elections['momentum']:.0f}%)", "urgency": "Medium",
                            "reason": "Rapid electoral acceleration may indicate early campaign or institutional event.", "monitoring": "Weekly"})
    if not watch_items:
        watch_items.append({"item": "Routine Monitoring", "urgency": "Low",
                           "reason": "No elevated concerns. Continue standard monitoring.", "monitoring": "Weekly"})

    # Recommended Actions
    actions = []
    if diaspora and diaspora["sentiment_label"] == "positive" and diaspora["share_of_voice"] > 25:
        from app.services.executive_decision_engine import build_recommendation
        actions.append(build_recommendation(
            db,
            category="ENGAGE", priority="High",
            issue=f"Global Nigerian Engagement at {diaspora['share_of_voice']:.0f}% with positive sentiment",
            action="Issue a public statement, content series, or membership drive capitalising on current peak diaspora engagement.",
            reasoning="High positive diaspora engagement creates a 1-2 week communications window before narrative attention shifts.",
            expected_outcome="Increased RTIFN visibility and community engagement during a peak attention period.",
            evidence=f"{diaspora['count']} diaspora records" if diaspora.get("count") else "Diaspora engagement data",
            time_horizon="7 days",
        ))
    if gov and gov["sentiment_label"] == "positive" and gov["share_of_voice"] > 15:
        from app.services.executive_decision_engine import build_recommendation
        actions.append(build_recommendation(
            db,
            category="ENGAGE", priority="High",
            issue=f"Governance at {gov['share_of_voice']:.0f}% with positive sentiment",
            action="Publish RTIFN commentary positioning diaspora community as constructive governance stakeholder.",
            reasoning="Positive governance discourse creates a favourable window for diaspora-government engagement.",
            expected_outcome="Strengthened RTIFN positioning ahead of 2027 election cycle.",
            evidence=f"{gov['count']} governance records" if gov.get("count") else "Governance discourse data",
            time_horizon="7 days",
        ))
    if sec and sec["sentiment_label"] == "negative" and sec["share_of_voice"] > 15:
        from app.services.executive_decision_engine import build_recommendation
        actions.append(build_recommendation(
            db,
            category="PREPARE", priority="High",
            issue=f"Security at {sec['share_of_voice']:.0f}% with negative sentiment",
            action="Prepare community briefing note. Monitor geographic concentration. Avoid amplifying negative narratives.",
            reasoning="Negative security discourse suppresses diaspora engagement and investment confidence.",
            expected_outcome="Reduced community anxiety and maintained engagement levels.",
            evidence=f"{sec['count']} security records" if sec.get("count") else "Security discourse data",
            time_horizon="30 days",
        ))
    for r in [r for r in risks if r.get("level") in ("Critical", "Warning")][:1]:
        from app.services.executive_decision_engine import build_recommendation
        actions.append(build_recommendation(
            db,
            category="PREPARE", priority="High",
            issue=r["title"],
            action=r.get("action", "Monitor and prepare appropriate response."),
            reasoning=r["detail"][:120],
            expected_outcome="Reduced risk exposure and improved situational awareness.",
            evidence=f"{r.get('evidence_count', 0)} records",
            time_horizon="30 days",
        ))
    if not actions:
        from app.services.executive_decision_engine import build_recommendation
        actions.append(build_recommendation(
            db,
            category="MONITOR", priority="Medium",
            issue="Stable environment — no immediate triggers",
            action="Continue daily monitoring. Review Leadership Pack weekly.",
            reasoning="No elevated concerns detected this period.",
            expected_outcome="Sustained intelligence quality and early warning capability.",
            evidence="No elevated narrative triggers this period",
            time_horizon="Ongoing",
        ))

    # Integrate Decision Support Engine
    try:
        from app.services.decision_support import generate_decision_support
        decision_support = generate_decision_support(db, days)
    except Exception:
        decision_support = None

    return {
        "executive_assessment": executive_assessment,
        "why_it_matters": why_matters,
        "what_changed": changes,
        "leadership_watch_items": watch_items[:5],
        "recommended_actions": actions[:4],
        "decision_support": decision_support,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
