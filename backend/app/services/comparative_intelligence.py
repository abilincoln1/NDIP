"""
Comparative Intelligence Engine
Generates human-readable comparisons instead of raw numbers.
"Governance generated 2.5x more discussion than Security"
"""
from datetime import datetime, timedelta, timezone
from sqlalchemy.orm import Session
from app.analytics.strategic_narratives import get_narrative_analysis, STRATEGIC_NARRATIVES


def _ratio_text(a: float, b: float, a_name: str, b_name: str) -> str:
    if b == 0:
        return f"**{a_name}** dominated with no comparable coverage of {b_name}."
    ratio = round(a / b, 1)
    if ratio >= 3:
        return f"**{a_name}** generated {ratio}x more discussion than **{b_name}**."
    elif ratio >= 2:
        return f"**{a_name}** generated twice as much discussion as **{b_name}**."
    elif ratio >= 1.5:
        return f"**{a_name}** generated {ratio}x more discussion than **{b_name}**."
    elif ratio >= 1.1:
        return f"**{a_name}** generated slightly more discussion than **{b_name}**."
    else:
        return f"**{a_name}** and **{b_name}** generated comparable levels of discussion."


def get_narrative_comparisons(db: Session, days: int = 7) -> dict:
    narratives = get_narrative_analysis(db, days)
    if not narratives:
        return {"comparisons": [], "dominant": None, "fastest_rising": None, "largest_decline": None}

    comparisons = []
    # Top vs others
    top = narratives[0]
    for other in narratives[1:4]:
        text = _ratio_text(top["count"], other["count"], top["narrative"], other["narrative"])
        comparisons.append(text)

    # Adjacent comparisons
    for i in range(1, min(len(narratives), 4)):
        a, b = narratives[i-1], narratives[i]
        if a["share_of_voice"] > 5 and b["share_of_voice"] > 5:
            text = _ratio_text(a["count"], b["count"], a["narrative"], b["narrative"])
            if text not in comparisons:
                comparisons.append(text)

    # Fastest rising (by momentum)
    rising = sorted(narratives, key=lambda x: x.get("momentum", 0), reverse=True)
    fastest = rising[0] if rising else None

    # Largest decline
    declining = [n for n in narratives if n.get("momentum", 0) < -10]
    largest_decline = min(declining, key=lambda x: x.get("momentum", 0)) if declining else None

    return {
        "comparisons": comparisons[:4],
        "dominant": {
            "narrative": top["narrative"],
            "share_of_voice": top["share_of_voice"],
            "insight": f"**{top['narrative']}** is the dominant narrative, accounting for {top['share_of_voice']:.0f}% of all monitored discourse."
        },
        "fastest_rising": {
            "narrative": fastest["narrative"],
            "momentum": fastest["momentum"],
            "insight": f"**{fastest['narrative']}** is the fastest-growing narrative, with coverage increasing significantly."
        } if fastest else None,
        "largest_decline": {
            "narrative": largest_decline["narrative"],
            "insight": f"**{largest_decline['narrative']}** saw the largest decline in coverage this period."
        } if largest_decline else None,
        "narrative_count": len(narratives),
        "total_coverage": sum(n["count"] for n in narratives),
    }


def get_source_comparison_text(db: Session, days: int = 7) -> list[str]:
    from app.analytics.intelligence import get_source_comparison
    sources = get_source_comparison(db, days)
    if not sources:
        return []
    sources_sorted = sorted(sources, key=lambda x: x["total"], reverse=True)
    results = []
    if len(sources_sorted) >= 2:
        top = sources_sorted[0]
        second = sources_sorted[1]
        results.append(
            f"**{top['platform'].replace('_',' ').title()}** was the most active source with {top['total']} posts analysed."
        )
        if top["total"] > 0 and second["total"] > 0:
            ratio = round(top["total"] / second["total"], 1)
            if ratio >= 1.5:
                results.append(
                    f"It generated {ratio}x more content than **{second['platform'].replace('_',' ').title()}**."
                )
    return results


def get_time_comparison(db: Session, days: int = 7) -> dict:
    """Compare current period vs previous period across key metrics."""
    from app.analytics.engine import compute_all_metrics
    current = compute_all_metrics(db, days)
    previous = compute_all_metrics(db, days * 2)

    def pct_change(current_val, prev_val):
        if prev_val == 0:
            return None
        return round((current_val - prev_val) / prev_val * 100, 1)

    engagement_change = pct_change(
        current["engagement_index"],
        previous["engagement_index"] - current["engagement_index"] if previous["engagement_index"] > current["engagement_index"] else current["engagement_index"]
    )

    return {
        "current_period_days": days,
        "engagement_direction": "stable",
        "sentiment_direction": "stable" if abs(current["sentiment_score"] - previous["sentiment_score"]) < 0.05 else
            "improving" if current["sentiment_score"] > previous["sentiment_score"] else "declining",
        "summary": f"Comparing the current {days}-day period against the previous equivalent period.",
    }
