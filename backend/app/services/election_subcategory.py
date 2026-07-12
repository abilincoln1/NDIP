"""
NDIP V5.7 — Election Narrative Granularity Engine
Adds sub-category classification within the "Elections & Democracy" narrative.

Design principle: this is an ADDITIVE secondary layer, not a replacement.
The existing STRATEGIC_NARRATIVES top-level classification in
strategic_narratives.py is completely unchanged — every post still gets
assigned to "Elections & Democracy" exactly as before. This module takes
ONLY the posts already classified into that narrative and further classifies
them into one of 8 election sub-categories, purely for additional executive
insight. If this module fails entirely, the rest of the platform is
unaffected — Election Centre falls back to the original single-bucket view.

Sub-categories (condensed from the original 12-category V5.2 specification
into 8 to keep each category meaningfully distinct and avoid keyword overlap
at current data volumes — see "Known limitations" in the V5.7 completion
report for the rationale):

1. INEC & Electoral Administration
2. Campaign & Party Activity
3. Electoral Security
4. Civic Participation & Voter Education
5. Electoral Reform & Legal Process
6. Public Trust & Institutional Confidence
7. Diaspora Electoral Interest
8. General Electoral Commentary (catch-all for genuinely unclassifiable posts)
"""
from datetime import datetime, timezone, timedelta
from collections import defaultdict
from typing import Optional


ELECTION_SUBCATEGORIES = {
    "INEC & Electoral Administration": {
        "description": "INEC operations, voter registration, electoral logistics, and administrative announcements",
        "keywords": [
            "inec", "independent national electoral commission", "voter registration",
            "permanent voter card", "pvc", "card reader", "bvas", "polling unit",
            "electoral commission", "registration centre", "biometric", "collation",
            "returning officer", "electoral officer",
        ],
        "weight": 1.3,
    },
    "Campaign & Party Activity": {
        "description": "Party primaries, candidate announcements, rallies, and campaign messaging",
        "keywords": [
            "campaign", "rally", "primary", "primaries", "candidate", "manifesto",
            "endorsement", "defection", "coalition", "running mate", "flagbearer",
            "apc", "pdp", "labour party", "nnpp", "adc", "convention", "delegate",
        ],
        "weight": 1.2,
    },
    "Electoral Security": {
        "description": "Security incidents, violence, or threats specifically tied to electoral activity",
        "keywords": [
            "election violence", "ballot box snatching", "polling unit attack",
            "election security", "thugs", "vote buying", "intimidation",
            "disruption", "clash", "election day violence", "security deployment election",
        ],
        "weight": 1.4,
    },
    "Civic Participation & Voter Education": {
        "description": "Voter education campaigns, civic engagement drives, and democratic participation initiatives",
        "keywords": [
            "voter education", "civic education", "civic engagement", "youth vote",
            "turnout", "voter apathy", "voter awareness", "get out the vote",
            "civil society election", "election observer", "domestic observer",
        ],
        "weight": 1.1,
    },
    "Electoral Reform & Legal Process": {
        "description": "Tribunal cases, legal petitions, electoral law reform, and judicial electoral matters",
        "keywords": [
            "tribunal", "petition", "election petition", "electoral act", "supreme court election",
            "appeal court election", "electoral reform", "legal challenge", "nullify",
            "annul election", "court ruling election", "judgment election",
        ],
        "weight": 1.2,
    },
    "Public Trust & Institutional Confidence": {
        "description": "Public commentary on electoral credibility, transparency, and trust in the process",
        "keywords": [
            "credible election", "free and fair", "election credibility", "rigging",
            "electoral fraud", "transparency election", "election integrity",
            "trust in inec", "manipulation", "election malpractice",
        ],
        "weight": 1.2,
    },
    "Diaspora Electoral Interest": {
        "description": "Diaspora voting rights, overseas voter participation, and diaspora electoral advocacy",
        "keywords": [
            "diaspora vote", "diaspora voting", "overseas voting", "out-of-country voting",
            "diaspora franchise", "diaspora electoral", "absentee ballot nigeria",
            "diaspora suffrage",
        ],
        "weight": 1.3,
    },
}

CATCH_ALL_LABEL = "General Electoral Commentary"


def classify_election_subcategory(text: str) -> Optional[str]:
    """
    Classify a single election-related post's text into a sub-category.
    Returns the highest-scoring sub-category, or the catch-all label if
    no sub-category keywords match (post is still genuinely about elections,
    just not specific enough to sub-classify).
    """
    if not text:
        return None
    text_lower = text.lower()
    scores = {}
    for subcat, config in ELECTION_SUBCATEGORIES.items():
        hits = sum(1 for kw in config["keywords"] if kw in text_lower)
        if hits > 0:
            scores[subcat] = hits * config["weight"]

    if not scores:
        return CATCH_ALL_LABEL
    return max(scores, key=scores.get)


def get_election_subcategory_breakdown(db, days: int = 30) -> dict:
    """
    Take all posts already classified as "Elections & Democracy" by the
    top-level strategic_narratives engine, and further break them down
    into the 8 election sub-categories.

    Returns a structure designed to slot directly into the existing
    Election Centre page without disrupting any other section.
    """
    from app.models.models import NormalisedPost
    from app.analytics.strategic_narratives import score_post_against_narratives

    now = datetime.now(timezone.utc)
    since = now - timedelta(days=days)
    prev_since = since - timedelta(days=days)

    posts = db.query(NormalisedPost).filter(
        NormalisedPost.published_at >= since,
        NormalisedPost.nlp_processed == True,
        NormalisedPost.text.isnot(None),
    ).all()

    prev_posts = db.query(NormalisedPost).filter(
        NormalisedPost.published_at >= prev_since,
        NormalisedPost.published_at < since,
        NormalisedPost.nlp_processed == True,
        NormalisedPost.text.isnot(None),
    ).all()

    # Filter down to only posts the TOP-LEVEL engine already assigned to Elections & Democracy.
    # This guarantees zero double-counting and zero divergence from the main narrative figures.
    def is_election_post(post) -> bool:
        scores = score_post_against_narratives(post.text or "")
        if not scores:
            return False
        return max(scores, key=scores.get) == "Elections & Democracy"

    election_posts = [p for p in posts if is_election_post(p)]
    prev_election_posts = [p for p in prev_posts if is_election_post(p)]

    total_election = max(len(election_posts), 1)

    subcat_data = {s: {"count": 0, "sentiment_sum": 0.0, "sources": set(), "prev_count": 0}
                   for s in list(ELECTION_SUBCATEGORIES.keys()) + [CATCH_ALL_LABEL]}

    for post in election_posts:
        subcat = classify_election_subcategory(post.text or "")
        if subcat:
            subcat_data[subcat]["count"] += 1
            subcat_data[subcat]["sentiment_sum"] += post.sentiment_score or 0
            subcat_data[subcat]["sources"].add(post.source_platform or "unknown")

    for post in prev_election_posts:
        subcat = classify_election_subcategory(post.text or "")
        if subcat:
            subcat_data[subcat]["prev_count"] += 1

    breakdown = []
    for subcat, data in subcat_data.items():
        count = data["count"]
        if count == 0:
            continue
        prev_count = data["prev_count"]
        momentum = round((count - prev_count) / max(prev_count, 1) * 100, 1) if prev_count else (100.0 if count > 0 else 0.0)
        avg_sentiment = round(data["sentiment_sum"] / max(count, 1), 3)
        share_of_election_voice = round(count / total_election * 100, 1)

        breakdown.append({
            "subcategory": subcat,
            "description": ELECTION_SUBCATEGORIES.get(subcat, {}).get("description", "Electoral content not matching a specific sub-category"),
            "count": count,
            "prev_count": prev_count,
            "share_of_election_voice": share_of_election_voice,
            "momentum": min(momentum, 500) if momentum > 0 else max(momentum, -100),
            "momentum_direction": "rising" if momentum > 10 else "falling" if momentum < -10 else "stable",
            "avg_sentiment": avg_sentiment,
            "sentiment_label": "positive" if avg_sentiment > 0.1 else "negative" if avg_sentiment < -0.1 else "neutral",
            "source_count": len(data["sources"]),
        })

    breakdown.sort(key=lambda x: x["count"], reverse=True)

    # Executive interpretation
    dominant = breakdown[0] if breakdown else None
    fastest_rising = max(breakdown, key=lambda x: x["momentum"], default=None) if breakdown else None

    if dominant:
        what_driving = (
            f"{dominant['subcategory']} is the leading driver of electoral discourse this period, "
            f"accounting for {dominant['share_of_election_voice']}% of all election-related content "
            f"({dominant['count']} mentions). {dominant['description']}"
        )
    else:
        what_driving = "Insufficient election-specific content this period for sub-category analysis."

    catch_all_entry = next((b for b in breakdown if b["subcategory"] == CATCH_ALL_LABEL), None)
    catch_all_share = catch_all_entry["share_of_election_voice"] if catch_all_entry else 0
    classification_quality = (
        "High" if catch_all_share < 25 else "Medium" if catch_all_share < 50 else "Low"
    )

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "period_days": days,
        "total_election_posts": len(election_posts),
        "subcategory_breakdown": breakdown,
        "dominant_subcategory": dominant["subcategory"] if dominant else None,
        "what_is_driving_electoral_discourse": what_driving,
        "fastest_rising_subcategory": fastest_rising["subcategory"] if fastest_rising else None,
        "classification_quality": classification_quality,
        "classification_quality_note": (
            f"{catch_all_share}% of election content falls into General Electoral Commentary "
            f"(unclassified into a specific sub-category). "
            + (
                "Classification quality is good — most content maps to a clear sub-theme."
                if classification_quality == "High"
                else "A meaningful share of content does not match specific sub-category keywords — "
                     "this is expected at current data volumes and will improve as electoral discourse "
                     "increases approaching the 2027 election."
                if classification_quality == "Medium"
                else "Most election content is not yet sub-classifiable. This is expected this far from "
                     "the election (low absolute volume per sub-category) — interpret sub-category figures "
                     "directionally rather than precisely until volume increases."
            )
        ),
    }
