"""
NDIP V6.1 Phase A/B/G -- Stakeholder Influence, Network & Momentum Engine

This module extends V6.0's stakeholder_registry.py with three new
capabilities, kept in a separate file because they are a genuinely
different kind of computation (composite scoring, graph traversal over
relationships, and time-series momentum) rather than more text matching:

  Phase A -- Stakeholder Influence Analysis: a six-factor composite score
      (Influence, Momentum, Narrative Impact, Opportunity Relevance,
      Engagement Priority, Relationship Strength) collapsed into a single
      Stakeholder Influence Index (Low/Medium/High/Critical).

  Phase B -- Stakeholder Network Mapping: traverses StakeholderRelationship
      edges to build dependency chains and a graph structure, reading from
      the relationship registry rather than any hard-coded org chart.

  Phase G -- Stakeholder Momentum Tracker: compares consecutive
      StakeholderMomentumSnapshot rows to derive a genuine trend label
      (Rising/Stable/Declining/Accelerating), replacing V6.0's single-period
      "Stakeholder Influence Shifts" proxy, which the V6.0 audit flagged as
      a known limitation (it could not distinguish "always been high" from
      "just became high").

PERFORMANCE NOTE (fixed in this version): the original implementation
called compute_stakeholder_influence() once per active stakeholder from
get_top_influence_stakeholders(), and that function's momentum
calculation independently re-queried and re-scanned the ENTIRE
NormalisedPost table (current period + previous period) for every single
stakeholder -- an O(stakeholders x posts x 2) cost that measured at 87
seconds for 45 stakeholders in live profiling (Leadership Pack, days=14).
get_emerging_stakeholders() then called get_top_influence_stakeholders()
a second time, doubling the cost again. Both issues are fixed below:
mention/momentum counts for ALL stakeholders are now computed in a single
pass over the post table (via batch helper functions), and
get_emerging_stakeholders() accepts a pre-computed ranked list instead of
recomputing it.

All functions here are read-heavy and best-effort: if V6.1 tables are
empty (e.g. before relationships are seeded, or before two momentum
snapshots exist), they degrade to honest partial results, not errors.
"""
from datetime import datetime, timezone, timedelta
import math

from sqlalchemy.orm import Session
from sqlalchemy import func

from app.models.models import (
    StakeholderRegistry, StakeholderRelationship, StakeholderInfluenceProfile,
    StakeholderMomentumSnapshot, RelationshipType, StakeholderInfluenceLevel,
    OpportunityAssessment,
)
from app.services.stakeholder_registry import compute_stakeholder_mentions


# --- Phase A: Stakeholder Influence Analysis -----------------------------------

def _narrative_impact_score_for_all(db: Session, days: int) -> float:
    """
    Narrative impact currently depends only on the platform's overall top
    share-of-voice, not on the individual stakeholder -- so it is the same
    value for every stakeholder in a given period. Computed once per
    request rather than once per stakeholder.
    """
    try:
        from app.analytics.strategic_narratives import get_narrative_analysis
        narratives = get_narrative_analysis(db, days)
        if not narratives:
            return 0.0
        top_sov = max((n.get("share_of_voice", 0) for n in narratives), default=0)
        return min(100.0, top_sov * 2.0) if top_sov else 0.0
    except Exception:
        return 0.0


def _relationship_strength_score(db: Session, stakeholder_id: int) -> float:
    """
    Stakeholders with more institutional relationships (reporting lines,
    funding ties, partnerships) carry more structural weight in the
    network, independent of how often they're mentioned in discourse.
    """
    edge_count = db.query(StakeholderRelationship).filter(
        (StakeholderRelationship.from_stakeholder_id == stakeholder_id) |
        (StakeholderRelationship.to_stakeholder_id == stakeholder_id),
        StakeholderRelationship.is_active == True,
    ).count()
    return min(100.0, edge_count * 20.0)


def _relationship_strength_scores_for_all(db: Session) -> dict:
    """Batched version: one query for all active relationships, counted per stakeholder, instead of one query per stakeholder."""
    edges = db.query(StakeholderRelationship).filter(StakeholderRelationship.is_active == True).all()
    counts = {}
    for e in edges:
        counts[e.from_stakeholder_id] = counts.get(e.from_stakeholder_id, 0) + 1
        counts[e.to_stakeholder_id] = counts.get(e.to_stakeholder_id, 0) + 1
    return {sid: min(100.0, count * 20.0) for sid, count in counts.items()}


def _opportunity_relevance_score(db: Session, stakeholder_id: int) -> float:
    """
    How many currently tracked OpportunityAssessments name this stakeholder?
    Parses the JSON stakeholders_json field already populated by V6.0's
    opportunity_intelligence.generate_opportunity_assessments().
    """
    import json
    opportunities = db.query(OpportunityAssessment).all()
    count = 0
    for o in opportunities:
        if not o.stakeholders_json:
            continue
        try:
            stakeholders = json.loads(o.stakeholders_json)
        except (json.JSONDecodeError, TypeError):
            continue
        if any(s.get("stakeholder_id") == stakeholder_id for s in stakeholders):
            count += 1
    return min(100.0, count * 25.0)


def _opportunity_relevance_scores_for_all(db: Session) -> dict:
    """Batched version: one query for all OpportunityAssessment rows, counted per stakeholder, instead of one query per stakeholder."""
    import json
    opportunities = db.query(OpportunityAssessment).all()
    counts = {}
    for o in opportunities:
        if not o.stakeholders_json:
            continue
        try:
            stakeholders = json.loads(o.stakeholders_json)
        except (json.JSONDecodeError, TypeError):
            continue
        seen_this_opportunity = set()
        for s in stakeholders:
            sid = s.get("stakeholder_id")
            if sid is not None and sid not in seen_this_opportunity:
                counts[sid] = counts.get(sid, 0) + 1
                seen_this_opportunity.add(sid)
    return {sid: min(100.0, count * 25.0) for sid, count in counts.items()}


def _compute_momentum_scores_for_all(db: Session, days: int) -> dict:
    """
    Batched replacement for the old per-stakeholder _compute_momentum_score():
    loads the current-period and previous-period posts ONCE (not once per
    stakeholder), and for each post checks which stakeholders it matches in
    a single pass, building current/previous mention counts for every
    stakeholder together. This is the single biggest fix in this file --
    the old version re-ran this exact query and scan independently for
    each of 45 stakeholders.
    """
    from app.models.models import NormalisedPost
    from app.services.stakeholder_registry import _load_active_registry_aliases, match_stakeholders_in_text

    since = datetime.now(timezone.utc) - timedelta(days=days)
    prev_since = since - timedelta(days=days)

    aliases = _load_active_registry_aliases(db, StakeholderRegistry)

    current_posts = db.query(NormalisedPost.text).filter(
        NormalisedPost.published_at >= since, NormalisedPost.text.isnot(None)
    ).all()
    prev_posts = db.query(NormalisedPost.text).filter(
        NormalisedPost.published_at >= prev_since, NormalisedPost.published_at < since,
        NormalisedPost.text.isnot(None),
    ).all()

    current_counts = {sid: 0 for sid in aliases}
    prev_counts = {sid: 0 for sid in aliases}

    for (text,) in current_posts:
        for sid in match_stakeholders_in_text(text, aliases):
            current_counts[sid] += 1
    for (text,) in prev_posts:
        for sid in match_stakeholders_in_text(text, aliases):
            prev_counts[sid] += 1

    scores = {}
    for sid in aliases:
        current_count = current_counts[sid]
        prev_count = prev_counts[sid]
        if prev_count == 0:
            scores[sid] = 50.0 if current_count > 0 else 0.0
            continue
        pct_change = ((current_count - prev_count) / prev_count) * 100
        sign = 1 if pct_change >= 0 else -1
        damped = sign * math.log1p(abs(pct_change) / 100) * 12
        scores[sid] = max(0.0, min(100.0, 50.0 + damped))

    return scores


def compute_stakeholder_influence(db: Session, stakeholder_id: int, days: int = 30) -> dict:
    """
    Phase A: the full six-factor composite for one stakeholder.

    NOTE: this single-stakeholder function is kept for callers that need
    just one stakeholder's score (e.g. a detail page), but it is no longer
    used internally by get_top_influence_stakeholders() / Leadership Pack,
    which use the batched _for_all() helpers above instead to avoid the
    O(stakeholders x posts) cost this function has when called in a loop.
    """
    mentions = compute_stakeholder_mentions(db, days)
    data = mentions.get(stakeholder_id, {"mention_count": 0, "source_count": 0})
    mention_count = data["mention_count"]
    source_count = data["source_count"]

    influence_score = min(100.0, math.log1p(mention_count) * 12)
    engagement_priority_score = min(100.0, min(70.0, math.log1p(mention_count) * 10) + min(30.0, source_count * 4))

    momentum_scores = _compute_momentum_scores_for_all(db, days)
    momentum_score = momentum_scores.get(stakeholder_id, 0.0)

    narrative_impact_score = _narrative_impact_score_for_all(db, days)
    opportunity_relevance_score = _opportunity_relevance_score(db, stakeholder_id)
    relationship_strength_score = _relationship_strength_score(db, stakeholder_id)

    composite_index = round(
        influence_score * 0.25 +
        momentum_score * 0.15 +
        narrative_impact_score * 0.15 +
        opportunity_relevance_score * 0.20 +
        engagement_priority_score * 0.15 +
        relationship_strength_score * 0.10,
        1,
    )

    if composite_index >= 70:
        level = StakeholderInfluenceLevel.CRITICAL
    elif composite_index >= 45:
        level = StakeholderInfluenceLevel.HIGH
    elif composite_index >= 20:
        level = StakeholderInfluenceLevel.MEDIUM
    else:
        level = StakeholderInfluenceLevel.LOW

    return {
        "stakeholder_id": stakeholder_id,
        "influence_score": round(influence_score, 1),
        "momentum_score": round(momentum_score, 1),
        "narrative_impact_score": round(narrative_impact_score, 1),
        "opportunity_relevance_score": round(opportunity_relevance_score, 1),
        "engagement_priority_score": round(engagement_priority_score, 1),
        "relationship_strength_score": round(relationship_strength_score, 1),
        "composite_index": composite_index,
        "influence_level": level.value,
        "mention_count": mention_count,
        "source_count": source_count,
    }


def recompute_all_influence_profiles(db: Session, days: int = 30) -> int:
    """Writes a fresh StakeholderInfluenceProfile snapshot for every active stakeholder. Returns count written."""
    ranked = get_top_influence_stakeholders(db, limit=10000, days=days)
    written = 0
    for result in ranked:
        db.add(StakeholderInfluenceProfile(
            stakeholder_id=result["stakeholder_id"], period_days=days,
            influence_score=result["influence_score"],
            momentum_score=result["momentum_score"],
            narrative_impact_score=result["narrative_impact_score"],
            opportunity_relevance_score=result["opportunity_relevance_score"],
            engagement_priority_score=result["engagement_priority_score"],
            relationship_strength_score=result["relationship_strength_score"],
            composite_index=result["composite_index"],
            influence_level=result["influence_level"],
        ))
        written += 1
    db.commit()
    return written


def _get_top_influence_from_materialised(db: Session, limit: int, days: int):
    """
    Fast path: read pre-computed influence profiles from
    stakeholder_influence_profiles when fresh data exists (written within
    last 25 hours). Returns None to trigger live computation fallback.
    """
    try:
        from app.models.models import StakeholderInfluenceProfile, StakeholderRegistry as SR
        from datetime import datetime, timezone, timedelta
        cutoff = datetime.now(timezone.utc) - timedelta(hours=25)
        profiles = (
            db.query(StakeholderInfluenceProfile, SR)
            .join(SR, StakeholderInfluenceProfile.stakeholder_id == SR.id)
            .filter(
                StakeholderInfluenceProfile.computed_at >= cutoff,
                StakeholderInfluenceProfile.period_days == days,
                SR.is_active == True,
            )
            .order_by(StakeholderInfluenceProfile.composite_index.desc())
            .limit(limit)
            .all()
        )
        if not profiles:
            return None
        results = []
        for profile, stakeholder in profiles:
            results.append({
                "stakeholder_id": stakeholder.id,
                "name": stakeholder.name,
                "category": stakeholder.category,
                "sector": stakeholder.sector,
                "stakeholder_type": stakeholder.stakeholder_type,
                "influence_score": profile.influence_score,
                "momentum_score": profile.momentum_score,
                "narrative_impact_score": profile.narrative_impact_score,
                "opportunity_relevance_score": profile.opportunity_relevance_score,
                "engagement_priority_score": profile.engagement_priority_score,
                "relationship_strength_score": profile.relationship_strength_score,
                "composite_index": profile.composite_index,
                "influence_level": profile.influence_level.value if hasattr(profile.influence_level, "value") else str(profile.influence_level),
                "monitoring_priority": "Critical" if profile.composite_index >= 70 else "High" if profile.composite_index >= 50 else "Medium" if profile.composite_index >= 30 else "Low",
                "_from_materialised": True,
            })
        return results
    except Exception:
        return None


def get_top_influence_stakeholders(db: Session, limit: int = 10, days: int = 30) -> list:
    """
    Returns stakeholders ranked by composite_index, computing fresh.

    PERFORMANCE: this now computes mentions, momentum, narrative impact,
    relationship strength, and opportunity relevance for ALL active
    stakeholders using batched single-pass helpers, instead of calling
    compute_stakeholder_influence() (which independently re-scans the post
    table) once per stakeholder. Measured at 87s for 45 stakeholders
    before this fix; the batched version should complete in well under a
    second for the same data volume.

    V6.2 Phase A: reads from stakeholder_influence_profiles when fresh
    data exists (written within last 25h by ingest pipeline).
    """
    materialised = _get_top_influence_from_materialised(db, limit, days)
    if materialised is not None:
        return materialised
    stakeholders = db.query(StakeholderRegistry).filter(StakeholderRegistry.is_active == True).all()

    mentions = compute_stakeholder_mentions(db, days)
    momentum_scores = _compute_momentum_scores_for_all(db, days)
    relationship_scores = _relationship_strength_scores_for_all(db)
    opportunity_scores = _opportunity_relevance_scores_for_all(db)
    narrative_impact_score = _narrative_impact_score_for_all(db, days)  # same value for every stakeholder this period

    results = []
    for s in stakeholders:
        data = mentions.get(s.id, {"mention_count": 0, "source_count": 0})
        mention_count = data["mention_count"]
        source_count = data["source_count"]
        if mention_count == 0:
            continue  # don't rank stakeholders with zero discourse presence

        influence_score = min(100.0, math.log1p(mention_count) * 12)
        engagement_priority_score = min(100.0, min(70.0, math.log1p(mention_count) * 10) + min(30.0, source_count * 4))
        momentum_score = momentum_scores.get(s.id, 0.0)
        relationship_strength_score = relationship_scores.get(s.id, 0.0)
        opportunity_relevance_score = opportunity_scores.get(s.id, 0.0)

        composite_index = round(
            influence_score * 0.25 +
            momentum_score * 0.15 +
            narrative_impact_score * 0.15 +
            opportunity_relevance_score * 0.20 +
            engagement_priority_score * 0.15 +
            relationship_strength_score * 0.10,
            1,
        )

        if composite_index >= 70:
            level = StakeholderInfluenceLevel.CRITICAL
        elif composite_index >= 45:
            level = StakeholderInfluenceLevel.HIGH
        elif composite_index >= 20:
            level = StakeholderInfluenceLevel.MEDIUM
        else:
            level = StakeholderInfluenceLevel.LOW

        results.append({
            "stakeholder_id": s.id,
            "name": s.name,
            "category": s.category,
            "sector": s.sector,
            "influence_score": round(influence_score, 1),
            "momentum_score": round(momentum_score, 1),
            "narrative_impact_score": round(narrative_impact_score, 1),
            "opportunity_relevance_score": round(opportunity_relevance_score, 1),
            "engagement_priority_score": round(engagement_priority_score, 1),
            "relationship_strength_score": round(relationship_strength_score, 1),
            "composite_index": composite_index,
            "influence_level": level.value,
            "mention_count": mention_count,
            "source_count": source_count,
        })

    results.sort(key=lambda r: r["composite_index"], reverse=True)
    return results[:limit]


def get_emerging_stakeholders(db: Session, limit: int = 10, days: int = 30, top_tier_cutoff: int = 5, _precomputed_ranked: list = None) -> list:
    """
    Phase H/I -- "Emerging Stakeholders" distinct from "Top Strategic
    Stakeholders": defined honestly as stakeholders with strong momentum
    (>=65, i.e. genuinely rising, not just stable) who are NOT already in
    the top composite_index tier.

    PERFORMANCE: accepts an optional _precomputed_ranked list (the result
    of an already-completed get_top_influence_stakeholders call) so callers
    that need both the top stakeholders AND the emerging stakeholders in
    the same request (e.g. Leadership Pack) do not pay for the expensive
    ranking computation twice. If not provided, computes it fresh as
    before (e.g. for standalone API callers).
    """
    all_ranked = _precomputed_ranked if _precomputed_ranked is not None else get_top_influence_stakeholders(db, limit=50, days=days)
    top_tier_ids = {r["stakeholder_id"] for r in all_ranked[:top_tier_cutoff]}
    emerging = [
        r for r in all_ranked
        if r["stakeholder_id"] not in top_tier_ids and r["momentum_score"] >= 65
    ]
    emerging.sort(key=lambda r: r["momentum_score"], reverse=True)
    return emerging[:limit]


# --- Phase B: Stakeholder Network Mapping --------------------------------------

def get_stakeholder_relationships(db: Session, stakeholder_id: int) -> dict:
    """Returns all direct relationships (incoming and outgoing) for one stakeholder."""
    outgoing = db.query(StakeholderRelationship).filter(
        StakeholderRelationship.from_stakeholder_id == stakeholder_id,
        StakeholderRelationship.is_active == True,
    ).all()
    incoming = db.query(StakeholderRelationship).filter(
        StakeholderRelationship.to_stakeholder_id == stakeholder_id,
        StakeholderRelationship.is_active == True,
    ).all()

    lookup = {s.id: s.name for s in db.query(StakeholderRegistry).all()}

    return {
        "outgoing": [
            {"to": lookup.get(r.to_stakeholder_id), "type": r.relationship_type, "description": r.description}
            for r in outgoing
        ],
        "incoming": [
            {"from": lookup.get(r.from_stakeholder_id), "type": r.relationship_type, "description": r.description}
            for r in incoming
        ],
    }


def build_dependency_chain(db: Session, stakeholder_id: int, max_depth: int = 5) -> list:
    """
    Phase B: traces a stakeholder's REPORTS_TO / OWNS_PROGRAMME chain
    upward (e.g. REA -> Ministry of Power -> ...) using breadth-first
    traversal over StakeholderRelationship edges, stopping at max_depth or
    when no further upward relationship exists. This is the "Stakeholder
    Dependency Map" / "Influence Chain" the spec describes.
    """
    lookup = {s.id: s.name for s in db.query(StakeholderRegistry).all()}
    chain = []
    current_id = stakeholder_id
    visited = {stakeholder_id}

    for _ in range(max_depth):
        edge = db.query(StakeholderRelationship).filter(
            StakeholderRelationship.from_stakeholder_id == current_id,
            StakeholderRelationship.relationship_type.in_([RelationshipType.REPORTS_TO, RelationshipType.OWNS_PROGRAMME]),
            StakeholderRelationship.is_active == True,
        ).first()
        if not edge or edge.to_stakeholder_id in visited:
            break
        chain.append({
            "from": lookup.get(current_id), "to": lookup.get(edge.to_stakeholder_id),
            "type": edge.relationship_type, "description": edge.description,
        })
        visited.add(edge.to_stakeholder_id)
        current_id = edge.to_stakeholder_id

    return chain


def get_network_graph(db: Session, category: str = None) -> dict:
    """
    Phase B: returns the full relationship graph (nodes + edges) for
    visualisation, optionally filtered to relationships tagged with a
    specific opportunity category (relevant_category).
    """
    q = db.query(StakeholderRelationship).filter(StakeholderRelationship.is_active == True)
    if category:
        q = q.filter(StakeholderRelationship.relevant_category == category)
    edges = q.all()

    lookup = {s.id: s for s in db.query(StakeholderRegistry).all()}
    node_ids = set()
    for e in edges:
        node_ids.add(e.from_stakeholder_id)
        node_ids.add(e.to_stakeholder_id)

    nodes = [
        {"id": nid, "name": lookup[nid].name, "category": lookup[nid].category}
        for nid in node_ids if nid in lookup
    ]
    edge_list = [
        {"from": e.from_stakeholder_id, "to": e.to_stakeholder_id,
         "type": e.relationship_type, "category": e.relevant_category}
        for e in edges
    ]
    return {"nodes": nodes, "edges": edge_list}


# --- Phase G: Stakeholder Momentum Tracker -------------------------------------

def record_momentum_snapshot(db: Session, stakeholder_id: int, days: int = 30) -> StakeholderMomentumSnapshot:
    """Writes one momentum snapshot for a stakeholder, used to build the time series Phase G needs."""
    mentions = compute_stakeholder_mentions(db, days)
    data = mentions.get(stakeholder_id, {"mention_count": 0})
    narrative_impact = _narrative_impact_score_for_all(db, days)
    opp_relevance = _opportunity_relevance_score(db, stakeholder_id)

    policy_edges = db.query(StakeholderRelationship).filter(
        (StakeholderRelationship.from_stakeholder_id == stakeholder_id) |
        (StakeholderRelationship.to_stakeholder_id == stakeholder_id),
    ).count()
    policy_visibility = min(100.0, policy_edges * 15.0)

    label = _derive_momentum_label(db, stakeholder_id, data["mention_count"])

    snapshot = StakeholderMomentumSnapshot(
        stakeholder_id=stakeholder_id,
        mention_count=data["mention_count"],
        narrative_visibility=round(narrative_impact, 1),
        opportunity_relevance=round(opp_relevance, 1),
        policy_visibility=round(policy_visibility, 1),
        momentum_label=label,
    )
    db.add(snapshot)
    db.commit()
    return snapshot


def _derive_momentum_label(db: Session, stakeholder_id: int, current_mentions: int) -> str:
    """
    Compares the current mention count to the two most recent prior
    snapshots to classify Rising/Stable/Declining/Accelerating. Requires
    at least one prior snapshot; returns "Stable" if this is the first
    snapshot ever recorded for this stakeholder (an honest default, not a
    fabricated trend).
    """
    prior = db.query(StakeholderMomentumSnapshot).filter(
        StakeholderMomentumSnapshot.stakeholder_id == stakeholder_id
    ).order_by(StakeholderMomentumSnapshot.snapshot_at.desc()).limit(2).all()

    if not prior:
        return "Stable"

    last = prior[0].mention_count
    if last == 0:
        return "Rising" if current_mentions > 0 else "Stable"

    pct_change = ((current_mentions - last) / last) * 100

    if len(prior) == 2:
        prev_change = ((prior[0].mention_count - prior[1].mention_count) / prior[1].mention_count) * 100 if prior[1].mention_count else 0
        if pct_change > 20 and prev_change > 20:
            return "Accelerating"

    if pct_change > 15:
        return "Rising"
    if pct_change < -15:
        return "Declining"
    return "Stable"


def get_stakeholder_momentum(db: Session, stakeholder_id: int, days: int = 30) -> dict:
    """Records a fresh snapshot and returns it alongside the short recent history for display."""
    snapshot = record_momentum_snapshot(db, stakeholder_id, days)
    history = db.query(StakeholderMomentumSnapshot).filter(
        StakeholderMomentumSnapshot.stakeholder_id == stakeholder_id
    ).order_by(StakeholderMomentumSnapshot.snapshot_at.desc()).limit(6).all()

    return {
        "current": {
            "mention_count": snapshot.mention_count,
            "narrative_visibility": snapshot.narrative_visibility,
            "opportunity_relevance": snapshot.opportunity_relevance,
            "policy_visibility": snapshot.policy_visibility,
            "momentum_label": snapshot.momentum_label,
        },
        "history": [
            {"snapshot_at": h.snapshot_at.isoformat(), "mention_count": h.mention_count, "momentum_label": h.momentum_label}
            for h in reversed(history)
        ],
    }
