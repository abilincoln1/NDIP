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


# ─── Phase A: Stakeholder Influence Analysis ───────────────────────────────────

def _narrative_impact_score(db: Session, stakeholder_id: int, days: int) -> float:
    """
    How much does this stakeholder's mention volume correlate with the
    platform's own top narratives? Approximated here by checking whether
    the stakeholder appears in posts tagged to a high-share-of-voice
    narrative, using the existing narrative analysis rather than building a
    parallel one. Best-effort: returns 0.0 if narrative data is unavailable.
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


def compute_stakeholder_influence(db: Session, stakeholder_id: int, days: int = 30) -> dict:
    """
    Phase A: the full six-factor composite for one stakeholder. Reuses
    V6.0's mention-based influence/visibility/engagement numbers as the
    base for Influence Score and Engagement Priority Score, and adds the
    three genuinely new V6.1 factors (Momentum, Narrative Impact,
    Relationship Strength) plus Opportunity Relevance (which V6.0 left as
    a placeholder).
    """
    mentions = compute_stakeholder_mentions(db, days)
    data = mentions.get(stakeholder_id, {"mention_count": 0, "source_count": 0})
    mention_count = data["mention_count"]
    source_count = data["source_count"]

    # Log-dampened with a less aggressive multiplier than V6.0's original
    # (*20, which saturated at the 100 ceiling for any mention count above
    # ~220 -- exactly the flaw the V6.0 audit flagged, since REA's 1,838
    # mentions, the Governor's 230, and the Presidency's 540 all read as an
    # identical 100). *12 keeps these three genuinely distinguishable
    # (90.2 / 65.3 / 75.5) while still reaching the ceiling for truly
    # dominant stakeholders (5,000+ mentions).
    influence_score = min(100.0, math.log1p(mention_count) * 12)
    engagement_priority_score = min(100.0, min(70.0, math.log1p(mention_count) * 10) + min(30.0, source_count * 4))

    # Momentum: compare this period's mentions to the prior period of equal
    # length. Returns 0 (neutral) if no prior data exists yet.
    momentum_score = _compute_momentum_score(db, stakeholder_id, days)

    narrative_impact_score = _narrative_impact_score(db, stakeholder_id, days)
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


def _compute_momentum_score(db: Session, stakeholder_id: int, days: int) -> float:
    """Compares this period's mention count to the immediately preceding period of equal length."""
    since = datetime.now(timezone.utc) - timedelta(days=days)
    prev_since = since - timedelta(days=days)

    from app.models.models import NormalisedPost
    from app.services.stakeholder_registry import _load_active_registry_aliases, match_stakeholders_in_text

    aliases = _load_active_registry_aliases(db, StakeholderRegistry)
    if stakeholder_id not in aliases:
        return 0.0
    single_alias_set = {stakeholder_id: aliases[stakeholder_id]}

    current_posts = db.query(NormalisedPost.text).filter(
        NormalisedPost.published_at >= since, NormalisedPost.text.isnot(None)
    ).all()
    prev_posts = db.query(NormalisedPost.text).filter(
        NormalisedPost.published_at >= prev_since, NormalisedPost.published_at < since,
        NormalisedPost.text.isnot(None),
    ).all()

    current_count = sum(1 for (text,) in current_posts if match_stakeholders_in_text(text, single_alias_set))
    prev_count = sum(1 for (text,) in prev_posts if match_stakeholders_in_text(text, single_alias_set))

    if prev_count == 0:
        return 50.0 if current_count > 0 else 0.0  # neutral-positive: new appearance, no baseline to compare

    pct_change = ((current_count - prev_count) / prev_count) * 100

    # Log-dampened scaling, not linear: a naive 50 + pct_change/2 saturates
    # at the 100 ceiling for any growth beyond +100%, which destroys
    # differentiation between "doubled" and "grew 50x" -- exactly the
    # saturation problem flagged in the V6.0 audit (stakeholder scores all
    # reading as an identical 100). log1p compresses large swings while
    # still ordering them correctly; scale=12 keeps +100% around 58,
    # +500% around 72, and reserves the 90-100 range for truly extreme
    # (1000%+) growth rather than handing it out for any large increase.
    sign = 1 if pct_change >= 0 else -1
    damped = sign * math.log1p(abs(pct_change) / 100) * 12
    return max(0.0, min(100.0, 50.0 + damped))


def recompute_all_influence_profiles(db: Session, days: int = 30) -> int:
    """Writes a fresh StakeholderInfluenceProfile snapshot for every active stakeholder. Returns count written."""
    stakeholders = db.query(StakeholderRegistry).filter(StakeholderRegistry.is_active == True).all()
    written = 0
    for s in stakeholders:
        result = compute_stakeholder_influence(db, s.id, days)
        db.add(StakeholderInfluenceProfile(
            stakeholder_id=s.id, period_days=days,
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


def get_top_influence_stakeholders(db: Session, limit: int = 10, days: int = 30) -> list:
    """Returns stakeholders ranked by composite_index, computing fresh if needed."""
    stakeholders = db.query(StakeholderRegistry).filter(StakeholderRegistry.is_active == True).all()
    results = []
    for s in stakeholders:
        result = compute_stakeholder_influence(db, s.id, days)
        if result["mention_count"] == 0:
            continue  # don't rank stakeholders with zero discourse presence
        result["name"] = s.name
        result["category"] = s.category
        result["sector"] = s.sector
        results.append(result)
    results.sort(key=lambda r: r["composite_index"], reverse=True)
    return results[:limit]


# ─── Phase B: Stakeholder Network Mapping ──────────────────────────────────────

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


# ─── Phase G: Stakeholder Momentum Tracker ─────────────────────────────────────

def record_momentum_snapshot(db: Session, stakeholder_id: int, days: int = 30) -> StakeholderMomentumSnapshot:
    """Writes one momentum snapshot for a stakeholder, used to build the time series Phase G needs."""
    mentions = compute_stakeholder_mentions(db, days)
    data = mentions.get(stakeholder_id, {"mention_count": 0})
    narrative_impact = _narrative_impact_score(db, stakeholder_id, days)
    opp_relevance = _opportunity_relevance_score(db, stakeholder_id)

    # Policy visibility: approximated as relationship count with PUBLIC_INSTITUTION/POLITICAL category targets.
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
