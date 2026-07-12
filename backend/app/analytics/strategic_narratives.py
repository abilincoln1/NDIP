"""
Strategic Narrative Framework
Maps topics and entities into high-level strategic narratives.
Produces executive-grade intelligence: share of voice, momentum, sentiment, confidence.
"""
from datetime import datetime, timedelta, timezone
from typing import Optional
from collections import defaultdict, Counter
import json
from sqlalchemy.orm import Session
from sqlalchemy import func

# ─── Strategic narrative definitions ─────────────────────────────────────────
# Each narrative has: keywords, entities, sub-themes
# A post is scored against each narrative — strongest match wins

STRATEGIC_NARRATIVES = {
    "Security": {
        "description": "Public safety, crime, terrorism, military operations, and civil unrest",
        "keywords": [
            "security", "safety", "crime", "violence", "terrorism", "insurgency",
            "kidnap", "abduction", "bandit", "bandits", "attack", "threat",
            "military", "police", "army", "navy", "airforce", "defence", "defense",
            "protest", "unrest", "tension", "conflict", "war", "hostage",
            "boko", "aqim", "iswap", "gunmen", "robbery", "theft", "murder",
        ],
        "weight": 1.2,
        "monitoring_threshold": 0.10,  # alert if below 10% share when security events active
    },
    "Economy": {
        "description": "Economic conditions, financial markets, trade, employment and business",
        "keywords": [
            "economy", "economic", "inflation", "gdp", "growth", "recession",
            "trade", "investment", "market", "finance", "fiscal", "monetary",
            "revenue", "budget", "debt", "deficit", "naira", "dollar", "currency",
            "exchange", "bank", "banking", "loan", "interest", "poverty",
            "unemployment", "employment", "jobs", "wage", "salary", "business",
            "enterprise", "industry", "oil", "petroleum", "commodity", "export",
            "import", "tariff", "tax", "remittance", "forex", "stock", "capital",
            "wealth", "subsidy", "fuel", "price", "cost", "expensive",
        ],
        "weight": 1.3,
        "monitoring_threshold": 0.15,
    },
    "Governance": {
        "description": "Government leadership, policy, legislation, and public administration",
        "keywords": [
            "government", "governance", "policy", "policies", "legislation", "law",
            "regulation", "reform", "corruption", "transparency", "accountability",
            "president", "minister", "parliament", "senate", "assembly", "council",
            "tinubu", "bola", "official", "administration", "cabinet", "judiciary", "court",
            "justice", "rights", "constitution", "federal", "state", "local",
            "municipal", "civic", "authority", "leadership", "cabinet", "minister",
            "obi", "atiku", "buhari", "shettima", "wike", "governor", "senator",
        ],
        "weight": 1.2,
        "monitoring_threshold": 0.10,
    },
    "Elections & Democracy": {
        "description": "Electoral processes, democratic institutions, and political participation",
        "keywords": [
            "election", "vote", "voting", "ballot", "candidate", "campaign",
            "democracy", "democratic", "party", "opposition", "ruling", "rigging",
            "inec", "tribunal", "petition", "result", "winner", "loser",
            "political", "civic", "participation", "representation", "franchise",
        ],
        "weight": 1.1,
        "monitoring_threshold": 0.05,
    },
    "Infrastructure": {
        "description": "Roads, housing, transportation, water, and public works",
        "keywords": [
            "infrastructure", "road", "roads", "highway", "bridge", "railway",
            "transport", "transportation", "airport", "seaport", "port",
            "construction", "building", "housing", "urban", "rural",
            "water", "sanitation", "sewage", "waste", "broadband", "internet",
        ],
        "weight": 0.9,
        "monitoring_threshold": 0.05,
    },
    "Energy": {
        "description": "Power supply, electricity, fuel, and energy policy",
        "keywords": [
            "energy", "power", "electricity", "fuel", "gas", "solar", "renewable",
            "generation", "transmission", "outage", "blackout", "nepa", "discos",
            "petroleum", "refinery", "pipeline", "subsidy", "kerosene", "diesel",
        ],
        "weight": 1.0,
        "monitoring_threshold": 0.05,
    },
    "Education": {
        "description": "Schools, universities, academic policy, and learning",
        "keywords": [
            "education", "school", "university", "college", "student", "teacher",
            "learning", "academic", "scholarship", "research", "literacy",
            "training", "graduate", "asuu", "strike", "tuition", "examination",
        ],
        "weight": 0.9,
        "monitoring_threshold": 0.05,
    },
    "Health": {
        "description": "Healthcare, disease, medical services, and public health",
        "keywords": [
            "health", "healthcare", "hospital", "doctor", "nurse", "medicine",
            "disease", "illness", "epidemic", "pandemic", "vaccine", "treatment",
            "mental", "malaria", "hiv", "aids", "cancer", "maternal", "mortality",
        ],
        "weight": 1.0,
        "monitoring_threshold": 0.05,
    },
    "Global Nigerian Engagement": {
        "description": "Nigerians abroad — community engagement, advocacy, identity, migration, remittances and civic participation",
        "keywords": [
            "diaspora", "migration", "migrant", "immigrant", "abroad", "overseas",
            "foreign", "international", "community", "identity", "culture",
            "heritage", "origin", "homeland", "citizenship", "passport", "visa",
            "dual", "british", "engagement", "representation", "advocacy",
            "nigeria", "nigerian", "africa", "african",
        ],
        "weight": 1.4,  # highest — core RTIFN mission
        "monitoring_threshold": 0.15,
    },
    "Investment": {
        "description": "Business investment, startups, technology, and economic development",
        "keywords": [
            "investment", "investor", "fund", "funding", "venture", "equity",
            "startup", "fintech", "technology", "innovation", "digital",
            "agriculture", "manufacturing", "logistics", "partnership",
            "collaboration", "foreign direct", "private sector",
        ],
        "weight": 1.1,
        "monitoring_threshold": 0.05,
    },
    "Media Representation": {
        "description": "How Nigerians and diaspora communities are portrayed in media",
        "keywords": [
            "media", "journalism", "journalist", "newspaper", "television",
            "broadcast", "social media", "narrative", "story", "coverage",
            "reporting", "press", "freedom", "propaganda", "image", "portrayal",
            "representation", "stereotype", "perception",
        ],
        "weight": 1.0,
        "monitoring_threshold": 0.05,
    },
}

# ─── Topic relevance scoring ──────────────────────────────────────────────────

# Terms to suppress from executive findings (not real intelligence)
SUPPRESSED_TERMS = {
    # Months and dates
    "january", "february", "march", "april", "may", "june", "july", "august",
    "september", "october", "november", "december", "monday", "tuesday",
    "wednesday", "thursday", "friday", "saturday", "sunday",
    # Generic temporal
    "today", "yesterday", "tomorrow", "week", "month", "year", "annual",
    "daily", "weekly", "monthly", "quarterly", "recently", "soon",
    # Generic verbs/adjectives already caught by nlp quality
    "also", "just", "even", "only", "still", "already", "always", "never",
    # Platform artifacts
    "newsap", "newsa", "appeared", "continue", "reading", "click", "source",
    "reuters", "afp", "associated", "press", "agency", "wire",
}


def score_topic_relevance(topic: str, count: int, narrative_scores: dict) -> float:
    """
    Score a topic by strategic relevance, not just frequency.
    Factors: frequency, narrative alignment, strategic weight.
    """
    t = topic.lower()

    # Suppress low-value terms
    if t in SUPPRESSED_TERMS:
        return 0.0

    # Find best matching narrative
    best_weight = 0.0
    for narrative, config in STRATEGIC_NARRATIVES.items():
        if any(kw in t or t in kw for kw in config["keywords"]):
            best_weight = max(best_weight, config["weight"])

    if best_weight == 0:
        best_weight = 0.5  # unclassified but valid

    # Frequency score (logarithmic to prevent domination)
    import math
    freq_score = math.log(count + 1) / math.log(100)

    return round(min(freq_score * best_weight, 1.0), 4)


# ─── Narrative analysis engine ────────────────────────────────────────────────

def score_post_against_narratives(text: str) -> dict[str, float]:
    """Score a post's text against each strategic narrative."""
    if not text:
        return {}
    text_lower = text.lower()
    scores = {}
    for narrative, config in STRATEGIC_NARRATIVES.items():
        hits = sum(1 for kw in config["keywords"] if kw in text_lower)
        if hits > 0:
            scores[narrative] = round(hits * config["weight"], 3)
    return scores


# V6.2 Phase A perf fix -- request-scoped memoization. Confirmed live this
# session: get_narrative_analysis() was called 14 times within a single
# Leadership Pack request, each call independently re-scanning the full
# NormalisedPost table for the period.
#
# Keyed on (id(db), days). NO time-based TTL: an earlier version of this
# fix used a 5-second TTL, which was found (via live diagnostic, this
# session) to be SHORTER than the function's own real computation time
# (4-7s observed), meaning the very first cache entry had already
# expired by the time the second call checked it -- silently defeating
# the entire memoization. Correctness here comes from request scope, not
# a clock: each HTTP request gets a fresh SQLAlchemy Session, so id(db)
# is naturally unique per request, and a cache entry can never be served
# across two genuinely different requests. The only remaining concern is
# unbounded growth in a long-lived process, handled by the size bound
# below (insertion-order eviction, since Python 3.7+ dicts preserve
# insertion order).
import time as _time_module
_narrative_analysis_cache = {}
_NARRATIVE_ANALYSIS_CACHE_MAX_SIZE = 200


def get_narrative_analysis(db, days: int = 7) -> list[dict]:
    """
    Compute share of voice, momentum, sentiment, and confidence for each narrative.
    This is the core of the Strategic Intelligence layer.

    V6.2 perf fix: memoized per (session, days), no time-based expiry.
    V6.2 Phase A materialised intelligence: reads from narrative_trends
    table when fresh data exists (written within last 25h), falling back
    to live computation otherwise. Eliminates the ~3.4s post table scan
    on cache-cold requests when the ingest pipeline has run.
    """
    cache_key = (id(db), days)
    if cache_key in _narrative_analysis_cache:
        return _narrative_analysis_cache[cache_key]
    result = _get_narrative_analysis_from_materialised(db, days)
    if result is None:
        result = _get_narrative_analysis_uncached(db, days)
    _narrative_analysis_cache[cache_key] = result
    if len(_narrative_analysis_cache) > _NARRATIVE_ANALYSIS_CACHE_MAX_SIZE:
        oldest_key = next(iter(_narrative_analysis_cache))
        del _narrative_analysis_cache[oldest_key]
    return result


def _get_narrative_analysis_from_materialised(db, days: int = 7):
    """
    Fast path: read from narrative_trends when fresh data exists.
    Returns None if no fresh data found (triggers live computation fallback).
    Fresh = written within the last 25 hours (covers one daily ingest cycle).
    """
    try:
        from app.models.models import NarrativeTrend
        from datetime import datetime, timezone, timedelta
        cutoff = datetime.now(timezone.utc) - timedelta(hours=25)
        # Find the most recent date_bucket and read ONLY those rows,
        # not all rows from the last 25h (which accumulate across
        # multiple ingest runs and cause duplicate narrative entries).
        from sqlalchemy import func
        latest_bucket = db.query(func.max(NarrativeTrend.date_bucket)).filter(
            NarrativeTrend.created_at >= cutoff
        ).scalar()
        if not latest_bucket:
            return None
        rows = db.query(NarrativeTrend).filter(
            NarrativeTrend.date_bucket == latest_bucket
        ).order_by(NarrativeTrend.mention_count.desc()).all()
        if not rows:
            return None
        total = max(sum(r.mention_count for r in rows), 1)
        results = []
        for row in rows:
            if row.mention_count == 0:
                continue
            share_of_voice = round(row.mention_count / total * 100, 1)
            momentum = row.velocity or 0.0
            avg_sentiment = row.sentiment_avg or 0.0
            confidence = min(round((row.mention_count / 10 * 0.5 + 0.5), 2), 1.0)
            results.append({
                "narrative": row.narrative,
                "description": STRATEGIC_NARRATIVES.get(row.narrative, {}).get("description", row.narrative),
                "count": row.mention_count,
                "prev_count": 0,
                "share_of_voice": share_of_voice,
                "momentum": round(min(momentum, 500) if momentum > 0 else max(momentum, -100), 1),
                "momentum_direction": "rising" if momentum > 10 else "falling" if momentum < -10 else "stable",
                "avg_sentiment": round(avg_sentiment, 3),
                "sentiment_label": "positive" if avg_sentiment > 0.1 else "negative" if avg_sentiment < -0.1 else "neutral",
                "source_count": 0,
                "sources": [],
                "confidence": confidence,
                "confidence_label": "High" if confidence >= 0.7 else "Medium" if confidence >= 0.4 else "Low",
                "_from_materialised": True,
            })
        results.sort(key=lambda x: x["share_of_voice"], reverse=True)
        return results
    except Exception:
        return None


def _get_narrative_analysis_uncached(db, days: int = 7) -> list[dict]:
    """
    Compute share of voice, momentum, sentiment, and confidence for each narrative.
    This is the core of the Strategic Intelligence layer.
    """
    from app.models.models import NormalisedPost
    now = datetime.now(timezone.utc)
    since = now - timedelta(days=days)
    prev_since = since - timedelta(days=days)

    # Current period posts
    posts = db.query(NormalisedPost).filter(
        NormalisedPost.published_at >= since,
        NormalisedPost.nlp_processed == True,
        NormalisedPost.text.isnot(None),
    ).all()

    # Previous period posts for momentum
    prev_posts = db.query(NormalisedPost).filter(
        NormalisedPost.published_at >= prev_since,
        NormalisedPost.published_at < since,
        NormalisedPost.nlp_processed == True,
        NormalisedPost.text.isnot(None),
    ).all()

    total = max(len(posts), 1)

    # Score each post
    narrative_data: dict = {n: {
        "count": 0, "sentiment_sum": 0.0, "sources": set(),
        "prev_count": 0, "posts": []
    } for n in STRATEGIC_NARRATIVES}

    for post in posts:
        scores = score_post_against_narratives(post.text or "")
        if scores:
            top_narrative = max(scores, key=scores.get)
            narrative_data[top_narrative]["count"] += 1
            narrative_data[top_narrative]["sentiment_sum"] += post.sentiment_score or 0
            narrative_data[top_narrative]["sources"].add(post.source_platform or "unknown")

    for post in prev_posts:
        scores = score_post_against_narratives(post.text or "")
        if scores:
            top_narrative = max(scores, key=scores.get)
            narrative_data[top_narrative]["prev_count"] += 1

    # Build results
    results = []
    for narrative, data in narrative_data.items():
        count = data["count"]
        if count == 0:
            continue
        prev_count = max(data["prev_count"], 0)
        momentum = round((count - prev_count) / max(prev_count, 1) * 100, 1)
        avg_sentiment = round(data["sentiment_sum"] / max(count, 1), 3)
        share_of_voice = round(count / total * 100, 1)
        source_count = len(data["sources"])
        confidence = min(round((count / 10 * 0.5 + source_count / 3 * 0.5), 2), 1.0)
        confidence_label = "High" if confidence >= 0.7 else "Medium" if confidence >= 0.4 else "Low"

        results.append({
            "narrative": narrative,
            "description": STRATEGIC_NARRATIVES[narrative]["description"],
            "count": count,
            "prev_count": prev_count,
            "share_of_voice": share_of_voice,
            "momentum": min(momentum, 500) if momentum > 0 else max(momentum, -100),
            "momentum_direction": "rising" if momentum > 10 else "falling" if momentum < -10 else "stable",
            "avg_sentiment": avg_sentiment,
            "sentiment_label": "positive" if avg_sentiment > 0.1 else "negative" if avg_sentiment < -0.1 else "neutral",
            "source_count": source_count,
            "sources": list(data["sources"]),
            "confidence": confidence,
            "confidence_label": confidence_label,
        })

    results.sort(key=lambda x: x["share_of_voice"], reverse=True)
    return results


def get_underrepresented_narratives(narrative_results: list[dict], days: int = 7) -> list[dict]:
    """Alert when important narratives are below expected threshold."""
    alerts = []
    present = {r["narrative"] for r in narrative_results}
    for narrative, config in STRATEGIC_NARRATIVES.items():
        threshold = config["monitoring_threshold"]
        matching = next((r for r in narrative_results if r["narrative"] == narrative), None)
        if matching:
            if matching["share_of_voice"] / 100 < threshold and config["weight"] >= 1.0:
                alerts.append({
                    "narrative": narrative,
                    "message": f"'{narrative}' appears underrepresented ({matching['share_of_voice']}% share of voice). "
                               f"Expected at least {threshold*100:.0f}% for this narrative category.",
                    "share_of_voice": matching["share_of_voice"],
                })
        elif config["weight"] >= 1.2:
            alerts.append({
                "narrative": narrative,
                "message": f"'{narrative}' has no detected coverage in this period. "
                           f"This is a high-priority monitoring category.",
                "share_of_voice": 0,
            })
    return alerts


def generate_strategic_insight(narrative: dict, rank: int, prev_count: int = 0) -> str:
    """
    Convert narrative data into an executive insight.
    Answers: Why does this matter? What changed? What should leadership monitor?
    """
    name = narrative["narrative"]
    sov = narrative["share_of_voice"]
    momentum = narrative["momentum"]
    sentiment = narrative["sentiment_label"]
    direction = narrative["momentum_direction"]

    # Build insight
    if rank == 0:
        opening = f"**{name}** dominated monitored conversations this period, accounting for {sov:.0f}% of all public discourse."
    elif sov >= 15:
        opening = f"**{name}** was a major theme in monitored sources, representing {sov:.0f}% of public conversation."
    else:
        opening = f"**{name}** accounted for {sov:.0f}% of monitored discourse."

    # Momentum context
    if direction == "rising" and prev_count == 0:
        momentum_text = " This narrative gained significant traction during this monitoring period."
    elif direction == "rising" and momentum > 100:
        momentum_text = " Discussion increased significantly — this is a rapidly developing narrative requiring close attention."
    elif direction == "rising" and momentum > 25:
        momentum_text = f" Coverage grew meaningfully compared to the previous period."
    elif direction == "rising":
        momentum_text = f" Coverage increased compared to the previous period."
    elif direction == "falling" and momentum < -25:
        momentum_text = f" Discussion declined ({abs(momentum):.0f}%) — this narrative may be losing public attention."
    elif direction == "falling":
        momentum_text = f" Coverage decreased slightly from the previous period."
    else:
        momentum_text = " Coverage remained stable."

    # Sentiment context
    if sentiment == "positive":
        sentiment_text = " The tone of coverage was broadly positive."
    elif sentiment == "negative":
        sentiment_text = " The tone of coverage was predominantly negative — leadership should review whether a public response is warranted."
    else:
        sentiment_text = " Coverage was largely neutral in tone."

    return opening + momentum_text + sentiment_text


def generate_opportunity_insights(narrative_results: list[dict]) -> list[dict]:
    """Identify strategic opportunities from narrative data."""
    opportunities = []
    for nar in narrative_results:
        # Rising positive narrative = opportunity
        if nar["momentum_direction"] == "rising" and nar["sentiment_label"] == "positive" and nar["momentum"] > 20:
            opportunities.append({
                "title": f"Growing Positive Coverage: {nar['narrative']}",
                "detail": f"Positive discussion about {nar['narrative'].lower()} increased by {nar['momentum']:.0f}% this period. "
                          f"This is an opportunity to amplify constructive narratives and strengthen public positioning.",
                "action": f"Engage with the {nar['narrative'].lower()} conversation through official communications.",
                "confidence_label": nar["confidence_label"],
                "source_count": nar["source_count"],
                "mention_count": nar["count"],
            })
        # High engagement diaspora narrative
        if nar["narrative"] == "Global Nigerian Engagement" and nar["share_of_voice"] > 20:
            opportunities.append({
                "title": "High Diaspora Engagement Window",
                "detail": f"Diaspora-related content represents {nar['share_of_voice']:.0f}% of monitored discourse — the highest share of voice. "
                          f"This is an ideal moment for targeted community outreach and engagement campaigns.",
                "action": "Launch a community engagement initiative or public call to action.",
                "confidence_label": nar["confidence_label"],
                "source_count": nar["source_count"],
                "mention_count": nar["count"],
            })
    return opportunities[:4]
