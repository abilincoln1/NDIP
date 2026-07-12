"""
NDIP V6.0 — Registry-Driven Classification Engine

Design principle (explicit platform-owner instruction): no stakeholder or
opportunity taxonomy is hard-coded into business logic. This module reads
StakeholderRegistry and OpportunityRegistry from the database and matches
their aliases against discourse text. Expanding coverage to a new ministry,
DFI, or programme type is a registry insert, not a code change or
deployment — unlike V5.7's ELECTION_SUBCATEGORIES, which is a fixed dict by
design (a deliberate, smaller-scope choice for that feature) and is NOT the
pattern this module follows.

This is additive only: it reads NormalisedPost data that already exists and
writes to the new V6.0 tables. It does not modify any V5.x classification,
narrative, or scoring logic.
"""
from datetime import datetime, timezone, timedelta
from collections import defaultdict
import json
import math

from sqlalchemy.orm import Session
from sqlalchemy import func

from app.models.models import (
    NormalisedPost, StakeholderRegistry, OpportunityRegistry,
    StakeholderProfile, OpportunityAssessment,
)


def _load_active_registry_aliases(db: Session, model):
    """
    Returns {registry_id: {"name": str, "aliases": [str, ...]}} for every
    active row in the given registry model (StakeholderRegistry or
    OpportunityRegistry). Aliases are lower-cased once here so every match
    call downstream does plain substring checks, not repeated lower() calls.
    """
    rows = db.query(model).filter(model.is_active == True).all()
    out = {}
    for r in rows:
        aliases = []
        if r.aliases_json:
            try:
                aliases = [a.lower() for a in json.loads(r.aliases_json)]
            except (json.JSONDecodeError, TypeError):
                aliases = []
        aliases.append(r.name.lower())
        if getattr(r, "short_name", None):
            aliases.append(r.short_name.lower())
        out[r.id] = {"name": r.name, "aliases": list(set(aliases))}
    return out


def match_stakeholders_in_text(text: str, registry_aliases: dict) -> list:
    """
    Returns the list of registry ids whose aliases appear in the given text
    (case-insensitive substring match). Intentionally simple — this is the
    same matching strength as the existing narrative keyword classifier
    (V5.5's narrative engine, V5.7's election sub-categories), not a new NLP
    capability. Multi-word aliases are checked as phrases.
    """
    if not text:
        return []
    text_lower = text.lower()
    matched = []
    for reg_id, info in registry_aliases.items():
        for alias in info["aliases"]:
            if alias and alias in text_lower:
                matched.append(reg_id)
                break
    return matched


def match_opportunities_in_text(text: str, registry_aliases: dict) -> list:
    """Same matching logic as match_stakeholders_in_text, for OpportunityRegistry."""
    return match_stakeholders_in_text(text, registry_aliases)


def compute_stakeholder_mentions(db: Session, days: int = 30) -> dict:
    """
    Scans NormalisedPost text over the given period and counts mentions per
    active stakeholder. Returns {stakeholder_id: {"name", "mention_count",
    "source_count", "sample_post_ids"}}. This is the read-only computation
    step; StakeholderProfile snapshots are written separately by
    recompute_stakeholder_profiles() so this function can also be reused
    for ad-hoc queries without writing anything.
    """
    since = datetime.now(timezone.utc) - timedelta(days=days)
    stakeholder_aliases = _load_active_registry_aliases(db, StakeholderRegistry)
    if not stakeholder_aliases:
        return {}

    posts = db.query(NormalisedPost.id, NormalisedPost.text, NormalisedPost.source_platform).filter(
        NormalisedPost.published_at >= since,
        NormalisedPost.text.isnot(None),
    ).all()

    mentions = defaultdict(lambda: {"mention_count": 0, "sources": set(), "sample_post_ids": []})
    for post_id, text, platform in posts:
        matched_ids = match_stakeholders_in_text(text, stakeholder_aliases)
        for sid in matched_ids:
            mentions[sid]["mention_count"] += 1
            mentions[sid]["sources"].add(platform)
            if len(mentions[sid]["sample_post_ids"]) < 5:
                mentions[sid]["sample_post_ids"].append(post_id)

    result = {}
    for sid, data in mentions.items():
        result[sid] = {
            "name": stakeholder_aliases[sid]["name"],
            "mention_count": data["mention_count"],
            "source_count": len(data["sources"]),
            "sample_post_ids": data["sample_post_ids"],
        }
    return result


def compute_opportunity_signals(db: Session, days: int = 30) -> dict:
    """
    Same approach as compute_stakeholder_mentions, scanning for opportunity
    registry aliases instead. Returns {opportunity_registry_id: {"name",
    "category", "mention_count", "source_count", "sample_post_ids"}}.
    """
    since = datetime.now(timezone.utc) - timedelta(days=days)
    opp_aliases = _load_active_registry_aliases(db, OpportunityRegistry)
    if not opp_aliases:
        return {}

    opp_rows = {r.id: r.category for r in db.query(OpportunityRegistry).filter(OpportunityRegistry.is_active == True).all()}

    posts = db.query(NormalisedPost.id, NormalisedPost.text, NormalisedPost.source_platform).filter(
        NormalisedPost.published_at >= since,
        NormalisedPost.text.isnot(None),
    ).all()

    signals = defaultdict(lambda: {"mention_count": 0, "sources": set(), "sample_post_ids": []})
    for post_id, text, platform in posts:
        matched_ids = match_opportunities_in_text(text, opp_aliases)
        for oid in matched_ids:
            signals[oid]["mention_count"] += 1
            signals[oid]["sources"].add(platform)
            if len(signals[oid]["sample_post_ids"]) < 5:
                signals[oid]["sample_post_ids"].append(post_id)

    result = {}
    for oid, data in signals.items():
        result[oid] = {
            "name": opp_aliases[oid]["name"],
            "category": opp_rows.get(oid, "UNKNOWN"),
            "mention_count": data["mention_count"],
            "source_count": len(data["sources"]),
            "sample_post_ids": data["sample_post_ids"],
        }
    return result


def recompute_stakeholder_profiles(db: Session, days: int = 30) -> int:
    """
    Writes a fresh StakeholderProfile snapshot row for every active
    stakeholder with at least one mention in the period. Scores are
    deliberately simple, transparent functions of observable signals
    (mention volume, source diversity) — not a black-box model — matching
    the platform's existing confidence/scoring conventions elsewhere
    (e.g. Decision Support's priority-to-confidence mapping). Returns the
    number of profile rows written.

    influence_score: scaled mention volume (0-100, log-dampened so one
        viral post doesn't dominate)
    visibility_score: source diversity (0-100, more distinct sources = more
        visible, not just more mentions from one source)
    engagement_score, opportunity_alignment_score, strategic_relevance_score:
        currently derived from the same base signals; intentionally simple
        for V6.0's first pass. Flagged in the completion report as a known
        limitation — see "Known limitations" for what real engagement and
        alignment scoring would require.
    """
    mentions = compute_stakeholder_mentions(db, days)
    written = 0
    for sid, data in mentions.items():
        mention_count = data["mention_count"]
        source_count = data["source_count"]

        # V6.1 fix: V6.0's original multipliers (influence *20, visibility
        # *15, engagement mention_count*0.5) all saturated at the 100
        # ceiling well within the range of real mention/source counts seen
        # in live discourse (e.g. REA's 1,838 mentions, 12 sources), which
        # is exactly the scoring-saturation limitation the V6.0 audit
        # flagged. These replacements preserve relative ordering across
        # the full 0-100 range instead of flattening everyone above a low
        # threshold to an identical 100.
        influence_score = min(100.0, math.log1p(mention_count) * 12)
        visibility_score = min(100.0, source_count * 8)
        engagement_score = min(100.0, min(70.0, math.log1p(mention_count) * 10) + min(30.0, source_count * 4))
        opportunity_alignment_score = 0.0   # requires opportunity-stakeholder linkage; see known limitations
        strategic_relevance_score = round((influence_score + visibility_score) / 2, 1)

        priority = "Low"
        if strategic_relevance_score >= 70:
            priority = "Critical"
        elif strategic_relevance_score >= 45:
            priority = "High"
        elif strategic_relevance_score >= 20:
            priority = "Medium"

        db.add(StakeholderProfile(
            stakeholder_id=sid,
            period_days=days,
            influence_score=round(influence_score, 1),
            visibility_score=round(visibility_score, 1),
            engagement_score=round(engagement_score, 1),
            opportunity_alignment_score=opportunity_alignment_score,
            strategic_relevance_score=strategic_relevance_score,
            mention_count=mention_count,
            recent_activity_summary=f"{mention_count} mentions across {source_count} sources in the last {days} days",
            monitoring_priority=priority,
        ))
        written += 1
    db.commit()
    return written


def get_top_stakeholders(db: Session, limit: int = 10, days: int = 30) -> list:
    """
    Returns the most recent StakeholderProfile snapshot per stakeholder,
    ranked by strategic_relevance_score, for display on dashboards
    (Leadership Pack Key Stakeholders, Situation Room Stakeholder Watchlist).
    Computes a fresh snapshot first so this always reflects current data
    rather than a stale cached profile.
    """
    recompute_stakeholder_profiles(db, days)

    subq = db.query(
        StakeholderProfile.stakeholder_id,
        func.max(StakeholderProfile.computed_at).label("max_computed_at")
    ).filter(StakeholderProfile.period_days == days).group_by(StakeholderProfile.stakeholder_id).subquery()

    profiles = db.query(StakeholderProfile).join(
        subq,
        (StakeholderProfile.stakeholder_id == subq.c.stakeholder_id) &
        (StakeholderProfile.computed_at == subq.c.max_computed_at)
    ).order_by(StakeholderProfile.strategic_relevance_score.desc()).limit(limit).all()

    stakeholder_lookup = {s.id: s for s in db.query(StakeholderRegistry).all()}

    results = []
    for p in profiles:
        sh = stakeholder_lookup.get(p.stakeholder_id)
        if not sh:
            continue
        results.append({
            "stakeholder_id": p.stakeholder_id,
            "name": sh.name,
            "short_name": sh.short_name,
            "category": sh.category,
            "sector": sh.sector,
            "influence_score": p.influence_score,
            "visibility_score": p.visibility_score,
            "engagement_score": p.engagement_score,
            "strategic_relevance_score": p.strategic_relevance_score,
            "monitoring_priority": p.monitoring_priority,
            "mention_count": p.mention_count,
            "recent_activity": p.recent_activity_summary,
        })
    return results


def get_top_opportunity_signals(db: Session, limit: int = 10, days: int = 30) -> list:
    """
    Returns the strongest opportunity signals detected in discourse this
    period, ranked by mention volume. This is signal detection only — it
    does NOT create OpportunityAssessment rows (that's a deliberate human
    or Decision-Support-triggered step, see opportunity_intelligence.py)
    so a spike in mentions doesn't silently fabricate a tracked opportunity
    pipeline entry without review.
    """
    signals = compute_opportunity_signals(db, days)
    ranked = sorted(signals.items(), key=lambda kv: kv[1]["mention_count"], reverse=True)[:limit]
    return [
        {"opportunity_registry_id": oid, **data}
        for oid, data in ranked
    ]


# ─── V6.0 Phase L — Platform-wide recommendation enrichment ───────────────────
# A single shared function, called from every module's recommendation
# generation path (Decision Support, National Pulse, Situation Room,
# Leadership Pack, Election Intelligence, GNEI, Entity Intelligence,
# Narrative Intelligence, SOI) rather than duplicating this logic eight
# times. Each module passes its recommendation text/narrative; this
# function returns the additional fields the V6.0 spec requires every
# recommendation to carry, derived from registry data already loaded once
# per call (not once per module) for efficiency.

_STAKEHOLDER_ALIAS_CACHE = {"loaded_at": None, "aliases": None}
_CACHE_TTL_SECONDS = 300  # 5 minutes — registry data changes rarely; avoid reloading on every recommendation


def _get_cached_stakeholder_aliases(db: Session) -> dict:
    now = datetime.now(timezone.utc)
    cached_at = _STAKEHOLDER_ALIAS_CACHE["loaded_at"]
    if cached_at is None or (now - cached_at).total_seconds() > _CACHE_TTL_SECONDS:
        _STAKEHOLDER_ALIAS_CACHE["aliases"] = _load_active_registry_aliases(db, StakeholderRegistry)
        _STAKEHOLDER_ALIAS_CACHE["loaded_at"] = now
    return _STAKEHOLDER_ALIAS_CACHE["aliases"]


def enrich_recommendation_with_stakeholders(db: Session, recommendation_text: str, narrative: str = None) -> dict:
    """
    Phase L: given a recommendation's text (and optionally its narrative),
    returns the platform-wide enrichment fields every recommendation should
    carry from V6.0 onward:
        stakeholders_to_engage, recommended_first_contact,
        recommended_next_action, expected_strategic_outcome,
        opportunity_alignment, outcome_probability

    This matches stakeholders mentioned IN the recommendation text itself
    (e.g. a recommendation that says "Engage the Rural Electrification
    Agency" will surface REA as a stakeholder) — it does not invent
    stakeholders the recommendation doesn't already reference. If no
    stakeholder is matched, the enrichment degrades gracefully to empty/None
    fields rather than fabricating a plausible-sounding but ungrounded
    answer; callers should treat an empty stakeholders_to_engage list as a
    legitimate, honest result, not a failure.
    """
    aliases = _get_cached_stakeholder_aliases(db)
    matched_ids = match_stakeholders_in_text(recommendation_text or "", aliases)

    stakeholders_to_engage = [aliases[mid]["name"] for mid in matched_ids][:5]
    recommended_first_contact = stakeholders_to_engage[0] if stakeholders_to_engage else None

    if stakeholders_to_engage:
        recommended_next_action = f"Initiate contact with {recommended_first_contact}."
        expected_strategic_outcome = (
            f"Engagement with {recommended_first_contact} clarifies feasibility and next steps."
        )
        outcome_probability = 0.5  # neutral prior; no historical engagement-outcome data exists yet (see known limitations)
    else:
        recommended_next_action = None
        expected_strategic_outcome = None
        outcome_probability = None

    # Opportunity alignment: does this recommendation's narrative overlap
    # with any actively tracked opportunity? Best-effort string match against
    # tracked OpportunityAssessment titles for the same narrative.
    opportunity_alignment = None
    if narrative:
        aligned = db.query(OpportunityAssessment).filter(
            OpportunityAssessment.source_narrative == narrative
        ).order_by(OpportunityAssessment.updated_at.desc()).first()
        if aligned:
            opportunity_alignment = aligned.title

    return {
        "stakeholders_to_engage": stakeholders_to_engage,
        "recommended_first_contact": recommended_first_contact,
        "recommended_next_action": recommended_next_action,
        "expected_strategic_outcome": expected_strategic_outcome,
        "opportunity_alignment": opportunity_alignment,
        "outcome_probability": outcome_probability,
    }
