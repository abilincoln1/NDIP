"""
NDIP V6.0 Phase A/B/F — Strategic Opportunity Intelligence (SOI) Engine

Generates opportunity assessments from discourse signals detected by
stakeholder_registry.py's compute_opportunity_signals(), and manages the
opportunity pipeline lifecycle (Detected -> Assessed -> Engaged ->
In Progress -> Advanced -> Secured / Closed / Expired).

This module deliberately keeps "signal detection" (automatic, in
stakeholder_registry.py) separate from "assessment creation" (this module,
explicitly invoked) — a spike in mentions of "mini-grid" does not, by
itself, silently create a tracked opportunity. generate_opportunity_assessments()
is the one function that promotes a signal into a real OpportunityAssessment
row, and it is idempotent per registry entry per period (re-running it
updates evidence counts on an existing OPEN assessment rather than creating
duplicates — same dedup principle as V5.9's recommendation_tracker fix).
"""
from datetime import datetime, timezone, timedelta
import json

from sqlalchemy.orm import Session

from app.models.models import (
    OpportunityRegistry, OpportunityAssessment, OpportunityPipelineEvent,
    OpportunityPipelineStatus, StakeholderRegistry,
)
from app.services.stakeholder_registry import (
    compute_opportunity_signals, compute_stakeholder_mentions, _load_active_registry_aliases,
)


# Minimum mentions in the period for a signal to be promoted to a tracked
# assessment. Below this, it's noise — same "evidence threshold" principle
# used elsewhere in the platform (e.g. narrative classification confidence).
MIN_MENTIONS_FOR_ASSESSMENT = 3

STRATEGIC_VALUE_BY_MENTIONS = [
    (20, "Critical"),
    (10, "High"),
    (5, "Medium"),
]


def _strategic_value_for(mention_count: int) -> str:
    for threshold, value in STRATEGIC_VALUE_BY_MENTIONS:
        if mention_count >= threshold:
            return value
    return "Low"


def _find_aligned_stakeholders(db: Session, opportunity_registry_id: int, days: int) -> list:
    """
    Cross-references stakeholder mentions against the opportunity's
    typical_lead_stakeholder_ids_json (if set on the registry entry) plus
    any stakeholder mentioned in the same period within the sector implied
    by the opportunity category. This is a best-effort linkage, not a
    guarantee — see "Known limitations" in the V6.0 completion report.
    """
    opp = db.query(OpportunityRegistry).filter(OpportunityRegistry.id == opportunity_registry_id).first()
    if not opp:
        return []

    aligned_ids = set()
    if opp.typical_lead_stakeholder_ids_json:
        try:
            aligned_ids.update(json.loads(opp.typical_lead_stakeholder_ids_json))
        except (json.JSONDecodeError, TypeError):
            pass

    stakeholder_mentions = compute_stakeholder_mentions(db, days)
    stakeholder_lookup = {s.id: s for s in db.query(StakeholderRegistry).all()}

    # Sector-based fallback alignment: if the opportunity has no explicit
    # lead stakeholders configured, surface any mentioned stakeholder whose
    # sector matches the opportunity's category name loosely. This is a
    # heuristic, not a guarantee of true institutional ownership.
    if not aligned_ids:
        category_sector_hint = opp.category.replace("_", " ").title()
        for sid, data in stakeholder_mentions.items():
            sh = stakeholder_lookup.get(sid)
            if sh and sh.sector and category_sector_hint.split()[0].lower() in sh.sector.lower():
                aligned_ids.add(sid)

    results = []
    for sid in aligned_ids:
        sh = stakeholder_lookup.get(sid)
        if not sh:
            continue
        mention_data = stakeholder_mentions.get(sid, {"mention_count": 0})
        results.append({
            "stakeholder_id": sid,
            "name": sh.name,
            "category": sh.category,
            "role": sh.role_description or sh.sector or "",
            "mention_count": mention_data.get("mention_count", 0),
        })
    # Rank by mention volume — stakeholders actively appearing in the same
    # discourse as the opportunity are more likely to be the right first contact.
    results.sort(key=lambda r: r["mention_count"], reverse=True)
    return results


def _recommended_engagement_for(category: str) -> str:
    """
    Maps opportunity category to a default recommended engagement action,
    drawn directly from the platform owner's specified examples. This is a
    starting suggestion, not a rigid rule — assessments can be edited.
    """
    mapping = {
        "PPP": "Submit concept note and request stakeholder meeting with the relevant PPP office.",
        "INFRASTRUCTURE": "Prepare policy brief and initiate partnership discussion with the lead implementing agency.",
        "ENERGY": "Request stakeholder meeting with the relevant energy agency and monitor programme development.",
        "WASTE_TO_ENERGY": "Prepare concept note for submission and engage diaspora chapters with relevant expertise.",
        "CLIMATE_FINANCE": "Monitor call for proposals and prepare a policy brief ahead of any application window.",
        "CARBON_MARKETS": "Join consultation process and monitor programme development.",
        "DIASPORA_INVESTMENT": "Engage diaspora chapters directly and prepare an investment positioning brief.",
        "FEDERAL_PROGRAMMES": "Request stakeholder meeting with the sponsoring federal ministry.",
        "STATE_PROGRAMMES": "Initiate partnership discussion with the relevant state agency.",
        "DEVELOPMENT_FINANCE": "Submit concept note to the relevant development finance institution.",
        "INTERNATIONAL_DONOR": "Respond to call for proposals or monitor for the next funding window.",
        "INNOVATION_ENTREPRENEURSHIP": "Engage diaspora chapters with relevant sector expertise.",
        "TRADE_INVESTMENT": "Initiate partnership discussion and prepare a trade positioning brief.",
        "INDUSTRIAL_DEVELOPMENT": "Request stakeholder meeting with the relevant industrial development agency.",
    }
    return mapping.get(category, "Monitor programme development and prepare a policy brief.")


def generate_opportunity_assessments(db: Session, days: int = 30) -> dict:
    """
    The core SOI function: scans discourse for opportunity signals, and for
    every signal at or above MIN_MENTIONS_FOR_ASSESSMENT, either creates a
    new OpportunityAssessment (status=DETECTED) or updates the evidence
    count on an existing OPEN one for the same opportunity_registry_id
    created within the last 30 days — avoiding the kind of duplicate-row
    accumulation found and fixed in V5.9's recommendation tracker.

    Returns {"created": int, "updated": int, "below_threshold": int}.
    """
    signals = compute_opportunity_signals(db, days)
    created = 0
    updated = 0
    below_threshold = 0
    recent_cutoff = datetime.now(timezone.utc) - timedelta(days=30)

    active_statuses = [
        OpportunityPipelineStatus.DETECTED, OpportunityPipelineStatus.ASSESSED,
        OpportunityPipelineStatus.ENGAGED, OpportunityPipelineStatus.IN_PROGRESS,
        OpportunityPipelineStatus.ADVANCED,
    ]

    for opp_id, data in signals.items():
        if data["mention_count"] < MIN_MENTIONS_FOR_ASSESSMENT:
            below_threshold += 1
            continue

        existing = db.query(OpportunityAssessment).filter(
            OpportunityAssessment.opportunity_registry_id == opp_id,
            OpportunityAssessment.status.in_(active_statuses),
            OpportunityAssessment.created_at >= recent_cutoff,
        ).order_by(OpportunityAssessment.created_at.desc()).first()

        stakeholders = _find_aligned_stakeholders(db, opp_id, days)
        stakeholders_json = json.dumps(stakeholders[:10])
        ranked_first = json.dumps([s["name"] for s in stakeholders[:3]])

        if existing:
            existing.evidence_post_count = data["mention_count"]
            existing.stakeholders_json = stakeholders_json
            existing.recommended_stakeholders_first_json = ranked_first
            existing.updated_at = datetime.now(timezone.utc)
            updated += 1
            continue

        category = data["category"]
        strategic_value = _strategic_value_for(data["mention_count"])
        confidence = "High" if data["source_count"] >= 3 else "Medium" if data["source_count"] >= 2 else "Low"

        assessment = OpportunityAssessment(
            opportunity_registry_id=opp_id,
            title=data["name"],
            category=category,
            what_opportunity_exists=(
                f"{data['name']} discourse detected — {data['mention_count']} mentions across "
                f"{data['source_count']} sources in the last {days} days."
            ),
            why_it_matters=(
                f"Sustained or growing discourse volume around {data['name']} suggests active "
                f"institutional or public attention in this programme area, which typically precedes "
                f"or accompanies funding windows, procurement activity, or partnership announcements."
            ),
            strategic_value=strategic_value,
            stakeholders_json=stakeholders_json,
            recommended_engagement=_recommended_engagement_for(category),
            recommended_stakeholders_first_json=ranked_first,
            expected_outcome="Early engagement position established ahead of formal programme announcements.",
            confidence=confidence,
            evidence_post_count=data["mention_count"],
            status=OpportunityPipelineStatus.DETECTED,
        )
        db.add(assessment)
        db.flush()  # get assessment.id for the pipeline event below

        db.add(OpportunityPipelineEvent(
            opportunity_id=assessment.id,
            event_type="status_change",
            from_status=None,
            to_status=OpportunityPipelineStatus.DETECTED.value,
            description=f"Opportunity detected from discourse analysis ({data['mention_count']} mentions, {data['source_count']} sources).",
        ))
        created += 1

    db.commit()
    return {"created": created, "updated": updated, "below_threshold": below_threshold}


def advance_opportunity_status(
    db: Session, opportunity_id: int, new_status: str,
    description: str, stakeholder_engaged: str = None,
    recorded_by: str = None, probability_of_success: float = None,
    next_milestone: str = None,
) -> OpportunityAssessment:
    """
    Moves an OpportunityAssessment to a new pipeline status and logs the
    transition as an OpportunityPipelineEvent. This is the function a
    leadership-facing UI action ("Mark as Engaged", "Log meeting outcome")
    would call — it is the only way status should change, so the event log
    always has a complete audit trail.
    """
    opp = db.query(OpportunityAssessment).filter(OpportunityAssessment.id == opportunity_id).first()
    if not opp:
        raise ValueError(f"OpportunityAssessment {opportunity_id} not found")

    old_status = opp.status
    opp.status = new_status
    opp.updated_at = datetime.now(timezone.utc)
    if probability_of_success is not None:
        opp.probability_of_success = probability_of_success
    if next_milestone is not None:
        opp.next_milestone = next_milestone

    db.add(OpportunityPipelineEvent(
        opportunity_id=opportunity_id,
        event_type="status_change",
        from_status=old_status,
        to_status=new_status,
        stakeholder_engaged=stakeholder_engaged,
        description=description,
        recorded_by=recorded_by,
    ))
    db.commit()
    db.refresh(opp)
    return opp


def get_opportunity_pipeline_summary(db: Session) -> dict:
    """
    Returns counts of active OpportunityAssessment rows grouped by status,
    for the Opportunity Pipeline Tracker (Phase F) shown on Leadership Pack
    and the V6.0 dashboard.
    """
    from sqlalchemy import func as sa_func
    rows = db.query(
        OpportunityAssessment.status, sa_func.count(OpportunityAssessment.id)
    ).group_by(OpportunityAssessment.status).all()
    counts = {status.value: 0 for status in OpportunityPipelineStatus}
    for status, count in rows:
        counts[status] = count
    return counts


def get_top_opportunities(db: Session, limit: int = 10) -> list:
    """
    Returns the highest strategic-value, most recently active opportunity
    assessments — for Leadership Pack's "Strategic Opportunities" panel and
    the V6.0 dashboard's "Top Opportunities".
    """
    value_order = {"Critical": 0, "High": 1, "Medium": 2, "Low": 3}
    active_statuses = [
        OpportunityPipelineStatus.DETECTED, OpportunityPipelineStatus.ASSESSED,
        OpportunityPipelineStatus.ENGAGED, OpportunityPipelineStatus.IN_PROGRESS,
        OpportunityPipelineStatus.ADVANCED,
    ]
    rows = db.query(OpportunityAssessment).filter(
        OpportunityAssessment.status.in_(active_statuses)
    ).order_by(OpportunityAssessment.updated_at.desc()).limit(limit * 3).all()

    rows.sort(key=lambda o: (value_order.get(o.strategic_value, 4), -o.evidence_post_count))
    rows = rows[:limit]

    results = []
    for o in rows:
        try:
            stakeholders = json.loads(o.stakeholders_json) if o.stakeholders_json else []
        except (json.JSONDecodeError, TypeError):
            stakeholders = []
        results.append({
            "id": o.id,
            "title": o.title,
            "category": o.category,
            "strategic_value": o.strategic_value,
            "status": o.status,
            "what_opportunity_exists": o.what_opportunity_exists,
            "why_it_matters": o.why_it_matters,
            "recommended_engagement": o.recommended_engagement,
            "stakeholders": stakeholders[:5],
            "confidence": o.confidence,
            "evidence_post_count": o.evidence_post_count,
            "probability_of_success": o.probability_of_success,
            "next_milestone": o.next_milestone,
        })
    return results


# ─── V6.1 Phase D: Opportunity Alignment Engine ───────────────────────────────
# Replaces the V6.0 placeholder opportunity_alignment_score (always 0.0,
# documented as a known limitation in the V6.0 audit) with a genuine
# five-factor score. This is a transparent heuristic, not a trained model --
# there is no historical engagement-outcome data yet to calibrate against,
# and that limitation is stated explicitly here rather than implied away by
# a confident-looking number.

ALIGNMENT_CLASSIFICATION_THRESHOLDS = [
    (75, "Strategic"),
    (55, "Strong"),
    (30, "Moderate"),
]


def _alignment_classification(score: float) -> str:
    for threshold, label in ALIGNMENT_CLASSIFICATION_THRESHOLDS:
        if score >= threshold:
            return label
    return "Weak"


def compute_opportunity_alignment(db: Session, opportunity_id: int, stakeholder_id: int, _precomputed_narrative_score: float = None) -> dict:
    """
    Phase D: computes the five-factor alignment score for one
    opportunity-stakeholder pair.

      stakeholder_relevance: is this stakeholder already named in the
          opportunity's stakeholders_json (i.e. did discourse/registry
          matching already associate them)?
      narrative_alignment: does the opportunity's source_narrative match
          a narrative this stakeholder has measurable impact in (reuses
          stakeholder_influence.py's narrative impact score)?
      policy_alignment: does an active StakeholderRelationship connect this
          stakeholder to the opportunity's category (relevant_category)?
      sector_alignment: does the stakeholder's registry sector field
          textually relate to the opportunity's category?
      historical_engagement_relevance: has this stakeholder appeared in any
          OutcomeChainLink for a previously tracked opportunity? (Currently
          near-always 0 platform-wide, since OutcomeChainLink has no data
          yet -- see known limitations.)
    """
    import json
    from app.models.models import StakeholderRegistry, StakeholderRelationship
    from app.services.stakeholder_influence import compute_stakeholder_influence

    opp = db.query(OpportunityAssessment).filter(OpportunityAssessment.id == opportunity_id).first()
    stakeholder = db.query(StakeholderRegistry).filter(StakeholderRegistry.id == stakeholder_id).first()
    if not opp or not stakeholder:
        raise ValueError("Opportunity or stakeholder not found")

    # Stakeholder relevance
    stakeholder_relevance = 0.0
    if opp.stakeholders_json:
        try:
            named = json.loads(opp.stakeholders_json)
            if any(s.get("stakeholder_id") == stakeholder_id for s in named):
                stakeholder_relevance = 80.0
        except (json.JSONDecodeError, TypeError):
            pass

    # Narrative alignment -- V6.2 perf fix: uses a pre-computed score when
    # the caller supplies one (compute_and_store_opportunity_alignment does,
    # via a single batched call covering all stakeholders on this
    # opportunity at once), avoiding the per-stakeholder full-table scan
    # that compute_stakeholder_influence() performs internally. Falls back
    # to the original per-call computation only when called standalone
    # (e.g. from a single-pair API route), preserving existing behaviour
    # for that path.
    if _precomputed_narrative_score is not None:
        narrative_alignment = _precomputed_narrative_score
    else:
        influence = compute_stakeholder_influence(db, stakeholder_id, days=30)
        narrative_alignment = influence["narrative_impact_score"]

    # Policy alignment -- active relationship tagged to this opportunity's category
    policy_edge = db.query(StakeholderRelationship).filter(
        (StakeholderRelationship.from_stakeholder_id == stakeholder_id) |
        (StakeholderRelationship.to_stakeholder_id == stakeholder_id),
        StakeholderRelationship.relevant_category == opp.category,
        StakeholderRelationship.is_active == True,
    ).first()
    policy_alignment = 75.0 if policy_edge else 0.0

    # Sector alignment -- textual overlap between stakeholder sector and opportunity category
    category_words = set(opp.category.lower().replace("_", " ").split())
    sector_words = set((stakeholder.sector or "").lower().split())
    sector_alignment = 60.0 if category_words & sector_words else 0.0

    # Historical engagement relevance -- honest placeholder. OutcomeChainLink
    # has no stakeholder-attributed rows yet platform-wide (see known
    # limitations), so this factor cannot yet be computed from real data;
    # it is fixed at 0.0 rather than estimated, to avoid presenting a
    # fabricated number as if it reflected genuine history.
    historical_engagement_relevance = 0.0

    alignment_score = round(
        stakeholder_relevance * 0.30 +
        narrative_alignment * 0.20 +
        policy_alignment * 0.25 +
        sector_alignment * 0.15 +
        historical_engagement_relevance * 0.10,
        1,
    )
    classification = _alignment_classification(alignment_score)

    return {
        "opportunity_id": opportunity_id, "stakeholder_id": stakeholder_id,
        "stakeholder_name": stakeholder.name,
        "stakeholder_relevance": stakeholder_relevance,
        "narrative_alignment": round(narrative_alignment, 1),
        "policy_alignment": policy_alignment,
        "sector_alignment": sector_alignment,
        "historical_engagement_relevance": historical_engagement_relevance,
        "alignment_score": alignment_score,
        "classification": classification,
    }


def compute_and_store_opportunity_alignment(db: Session, opportunity_id: int) -> list:
    """
    Computes and persists OpportunityAlignmentScore rows for every
    stakeholder named on the opportunity, returning the ranked list.
    """
    import json
    from app.models.models import OpportunityAlignmentScore

    opp = db.query(OpportunityAssessment).filter(OpportunityAssessment.id == opportunity_id).first()
    if not opp or not opp.stakeholders_json:
        return []

    try:
        named_stakeholders = json.loads(opp.stakeholders_json)
    except (json.JSONDecodeError, TypeError):
        return []

    # V6.2 perf fix: compute narrative impact scores for ALL stakeholders
    # on this opportunity in a single batched pass (one post-table scan
    # total), instead of compute_opportunity_alignment() triggering its own
    # full post-table scan once per stakeholder inside the loop below.
    from app.services.stakeholder_influence import _narrative_impact_score_for_all, _compute_momentum_scores_for_all
    _narrative_score_for_all_stakeholders = _narrative_impact_score_for_all(db, 30)  # same value platform-wide this period, computed once
    results = []
    for s in named_stakeholders:
        sid = s.get("stakeholder_id")
        if sid is None:
            continue
        try:
            result = compute_opportunity_alignment(db, opportunity_id, sid, _precomputed_narrative_score=_narrative_score_for_all_stakeholders)
        except ValueError:
            continue

        db.add(OpportunityAlignmentScore(
            opportunity_id=opportunity_id, stakeholder_id=sid,
            stakeholder_relevance=result["stakeholder_relevance"],
            narrative_alignment=result["narrative_alignment"],
            policy_alignment=result["policy_alignment"],
            sector_alignment=result["sector_alignment"],
            historical_engagement_relevance=result["historical_engagement_relevance"],
            alignment_score=result["alignment_score"],
            classification=result["classification"],
        ))
        results.append(result)

    db.commit()
    results.sort(key=lambda r: r["alignment_score"], reverse=True)
    return results


# ─── V6.1 Phase E: Opportunity Readiness Index ────────────────────────────────

READINESS_LABEL_THRESHOLDS = [
    (80, "Strategic Window"),
    (60, "Ready"),
    (40, "Developing"),
    (20, "Emerging"),
]


def _readiness_label(score: float) -> str:
    for threshold, label in READINESS_LABEL_THRESHOLDS:
        if score >= threshold:
            return label
    return "Not Ready"


def compute_opportunity_readiness(db: Session, opportunity_id: int, _precomputed_alignment_results: list = None) -> dict:
    """
    Phase E: six-factor readiness scoring. implementation_complexity is
    scored such that HIGHER complexity REDUCES readiness (it is inverted
    before being added to the composite).

    V6.2 perf fix: accepts an optional pre-computed alignment_results list
    (generate_execution_plan() already computes this once and passes it
    through), avoiding a second, fully redundant call to
    compute_and_store_opportunity_alignment() -- confirmed live this
    session to independently cost ~4s on its own, paid twice per dossier
    before this fix.
    """
    from app.models.models import OpportunityPipelineEvent

    opp = db.query(OpportunityAssessment).filter(OpportunityAssessment.id == opportunity_id).first()
    if not opp:
        raise ValueError("Opportunity not found")

    alignment_results = _precomputed_alignment_results if _precomputed_alignment_results is not None else compute_and_store_opportunity_alignment(db, opportunity_id)
    stakeholder_readiness = (
        sum(r["alignment_score"] for r in alignment_results) / len(alignment_results)
        if alignment_results else 0.0
    )

    policy_environment = max((r["policy_alignment"] for r in alignment_results), default=0.0)

    # Narrative momentum -- reuse the opportunity's own evidence_post_count
    # trend implicitly via strategic_value, since that is already derived
    # from mention volume.
    narrative_momentum = {"Critical": 100.0, "High": 75.0, "Medium": 50.0, "Low": 25.0}.get(opp.strategic_value, 25.0)

    # Public sentiment -- best-effort: confidence is the closest existing
    # proxy NDIP has for "how clearly is this opportunity understood/discussed".
    public_sentiment = {"High": 75.0, "Medium": 50.0, "Low": 25.0}.get(opp.confidence, 50.0)

    # Funding environment -- does any aligned stakeholder have a FUNDS relationship pointing at this category?
    from app.models.models import StakeholderRelationship
    funding_edge = db.query(StakeholderRelationship).filter(
        StakeholderRelationship.relationship_type == "FUNDS",
        StakeholderRelationship.relevant_category == opp.category,
        StakeholderRelationship.is_active == True,
    ).first()
    funding_environment = 70.0 if funding_edge else 20.0

    # Implementation complexity -- proxy: number of distinct stakeholders
    # required is treated as a complexity signal (more parties = harder to
    # coordinate). Inverted below.
    implementation_complexity = min(100.0, len(alignment_results) * 15.0)

    readiness_score = round(
        stakeholder_readiness * 0.25 +
        policy_environment * 0.20 +
        narrative_momentum * 0.20 +
        public_sentiment * 0.10 +
        funding_environment * 0.15 +
        (100.0 - implementation_complexity) * 0.10,
        1,
    )
    label = _readiness_label(readiness_score)

    return {
        "opportunity_id": opportunity_id,
        "stakeholder_readiness": round(stakeholder_readiness, 1),
        "policy_environment": round(policy_environment, 1),
        "narrative_momentum": narrative_momentum,
        "public_sentiment": public_sentiment,
        "funding_environment": funding_environment,
        "implementation_complexity": round(implementation_complexity, 1),
        "readiness_score": readiness_score,
        "readiness_label": label,
    }


def compute_and_store_readiness(db: Session, opportunity_id: int) -> dict:
    from app.models.models import OpportunityReadinessAssessment
    result = compute_opportunity_readiness(db, opportunity_id)
    db.add(OpportunityReadinessAssessment(
        opportunity_id=opportunity_id,
        stakeholder_readiness=result["stakeholder_readiness"],
        policy_environment=result["policy_environment"],
        narrative_momentum=result["narrative_momentum"],
        public_sentiment=result["public_sentiment"],
        funding_environment=result["funding_environment"],
        implementation_complexity=result["implementation_complexity"],
        readiness_score=result["readiness_score"],
        readiness_label=result["readiness_label"],
    ))
    db.commit()
    return result


# ─── V6.1 Phase F: Engagement Pathway Engine ──────────────────────────────────

_PATHWAY_TEMPLATE = [
    "Identify and confirm the lead stakeholder(s) for this opportunity.",
    "Engage institutional leadership through an initial introductory contact.",
    "Establish a working relationship and clarify mutual interest.",
    "Develop a proposal or concept note aligned to the stakeholder's mandate.",
    "Advance the opportunity toward formal review or partnership commitment.",
]


def generate_engagement_pathway(db: Session, opportunity_id: int) -> dict:
    """
    Phase F: generates an ordered, named engagement pathway for an
    opportunity. The five-step structure follows the spec's own example
    template; step 1 and step 2 are personalised with the opportunity's
    actual ranked stakeholders where available, rather than left generic.
    Marks any prior pathway for this opportunity as superseded
    (is_current=False) rather than deleting it, preserving history.
    """
    import json
    from app.models.models import EngagementPathway, EngagementStep

    opp = db.query(OpportunityAssessment).filter(OpportunityAssessment.id == opportunity_id).first()
    if not opp:
        raise ValueError("Opportunity not found")

    db.query(EngagementPathway).filter(
        EngagementPathway.opportunity_id == opportunity_id, EngagementPathway.is_current == True
    ).update({"is_current": False})

    stakeholders = []
    if opp.stakeholders_json:
        try:
            stakeholders = json.loads(opp.stakeholders_json)
        except (json.JSONDecodeError, TypeError):
            pass

    # Bug fix (V6.0A activation cycle): stakeholders_json is stored in
    # DETECTION order (raw mention count at the time the opportunity was
    # first found), which has no relationship to alignment strength. The
    # engagement pathway's "first contact" must reflect the opportunity's
    # actual computed alignment ranking, not the incidental detection
    # order -- otherwise this function can recommend approaching a
    # Moderate-alignment stakeholder before a Strong-alignment one,
    # contradicting the "Who matters?" section of the same execution plan.
    from app.models.models import OpportunityAlignmentScore as _OAS
    # NOTE: compute_and_store_opportunity_alignment() writes a fresh row on
    # every call with no dedup (separate, pre-existing issue, flagged for
    # the V6.0A completion report's known limitations) -- so this query can
    # return many historical rows per stakeholder. Take only the most
    # recent row per distinct stakeholder_id before ranking.
    all_alignment_rows = db.query(_OAS).filter(_OAS.opportunity_id == opportunity_id).order_by(_OAS.computed_at.desc()).all()
    most_recent_by_stakeholder = {}
    for row in all_alignment_rows:
        if row.stakeholder_id not in most_recent_by_stakeholder:
            most_recent_by_stakeholder[row.stakeholder_id] = row

    # Tie-break must match compute_and_store_opportunity_alignment()'s own
    # behaviour exactly: that function does results.sort(key=alignment_score,
    # reverse=True), and Python's sort is stable, so ties fall back to
    # stakeholders_json order. Sorting here by (-score, stakeholders_json
    # position) reproduces that ordering, so "Who matters?" and this
    # engagement sequence always agree, including on genuine ties.
    stakeholders_json_order = {s.get("stakeholder_id"): i for i, s in enumerate(stakeholders)}
    alignment_rows = sorted(
        most_recent_by_stakeholder.values(),
        key=lambda r: (-r.alignment_score, stakeholders_json_order.get(r.stakeholder_id, 999)),
    )
    if alignment_rows:
        alignment_order_ids = [row.stakeholder_id for row in alignment_rows]
        stakeholder_lookup = {s.get("stakeholder_id"): s for s in stakeholders}
        stakeholders = [stakeholder_lookup[sid] for sid in alignment_order_ids if sid in stakeholder_lookup]

    pathway = EngagementPathway(opportunity_id=opportunity_id, is_current=True)
    db.add(pathway)
    db.flush()

    first_contact = stakeholders[0]["name"] if stakeholders else None
    second_contact = stakeholders[1]["name"] if len(stakeholders) > 1 else None

    step_descriptions = list(_PATHWAY_TEMPLATE)
    if first_contact:
        step_descriptions[0] = f"Identify and confirm {first_contact} as the lead stakeholder for this opportunity."
        step_descriptions[1] = f"Engage {first_contact}'s leadership through an initial introductory contact."
    if second_contact:
        step_descriptions[2] = f"Establish a working relationship with {first_contact} and bring in {second_contact} as a secondary stakeholder."

    for i, desc in enumerate(step_descriptions, start=1):
        stakeholder_id = None
        if i <= 2 and stakeholders:
            stakeholder_id = stakeholders[0].get("stakeholder_id")
        db.add(EngagementStep(
            pathway_id=pathway.id, step_number=i, description=desc,
            stakeholder_id=stakeholder_id, status="Pending",
        ))

    db.commit()
    db.refresh(pathway)

    steps = db.query(EngagementStep).filter(EngagementStep.pathway_id == pathway.id).order_by(EngagementStep.step_number).all()
    return {
        "pathway_id": pathway.id, "opportunity_id": opportunity_id,
        "generated_at": pathway.generated_at.isoformat(),
        "steps": [
            {"step_number": s.step_number, "description": s.description, "status": s.status, "stakeholder_id": s.stakeholder_id}
            for s in steps
        ],
    }


def get_current_pathway(db: Session, opportunity_id: int) -> dict:
    """Returns the current (non-superseded) pathway for an opportunity, generating one if none exists."""
    from app.models.models import EngagementPathway, EngagementStep

    pathway = db.query(EngagementPathway).filter(
        EngagementPathway.opportunity_id == opportunity_id, EngagementPathway.is_current == True
    ).first()
    if not pathway:
        return generate_engagement_pathway(db, opportunity_id)

    steps = db.query(EngagementStep).filter(EngagementStep.pathway_id == pathway.id).order_by(EngagementStep.step_number).all()
    return {
        "pathway_id": pathway.id, "opportunity_id": opportunity_id,
        "generated_at": pathway.generated_at.isoformat(),
        "steps": [
            {"step_number": s.step_number, "description": s.description, "status": s.status, "stakeholder_id": s.stakeholder_id}
            for s in steps
        ],
    }


# ─── V6.1 Phase C: Opportunity Execution Plan ─────────────────────────────────

def generate_execution_plan(db: Session, opportunity_id: int) -> dict:
    """
    Phase C: the upgraded opportunity output the spec asks for, combining
    everything V6.1 adds (alignment, readiness, pathway) into one
    structured Opportunity Execution Plan with the exact sections
    specified: Opportunity, Strategic Value, Required Stakeholders,
    Recommended Engagement Sequence, Potential Barriers, Required
    Approvals, Required Partnerships, Expected Outcomes, Confidence Assessment.
    """
    opp = db.query(OpportunityAssessment).filter(OpportunityAssessment.id == opportunity_id).first()
    if not opp:
        raise ValueError("Opportunity not found")

    alignment_results = compute_and_store_opportunity_alignment(db, opportunity_id)
    readiness = compute_opportunity_readiness(db, opportunity_id, _precomputed_alignment_results=alignment_results)
    pathway = get_current_pathway(db, opportunity_id)

    required_stakeholders = [
        {"name": r["stakeholder_name"], "alignment_score": r["alignment_score"], "classification": r["classification"]}
        for r in alignment_results
    ]

    # Potential barriers -- derived honestly from the readiness breakdown:
    # any factor scoring low is surfaced as a named barrier, rather than a
    # generic boilerplate list.
    barriers = []
    if readiness["funding_environment"] < 50:
        barriers.append("No confirmed funding relationship identified for this opportunity category yet.")
    if readiness["implementation_complexity"] > 60:
        barriers.append("Coordination complexity is elevated due to the number of stakeholders required.")
    if readiness["policy_environment"] < 30:
        barriers.append("No active policy/regulatory relationship currently links a known stakeholder to this opportunity area.")
    if not barriers:
        barriers.append("No significant barriers identified from current data; monitor for emerging risks as engagement proceeds.")

    required_approvals = [s["name"] for s in required_stakeholders if s["classification"] in ("Strong", "Strategic")][:3]
    required_partnerships = [s["name"] for s in required_stakeholders if s["classification"] == "Moderate"][:3]

    return {
        "opportunity_id": opportunity_id,
        "opportunity": opp.title,
        "strategic_value": opp.strategic_value,
        "required_stakeholders": required_stakeholders,
        "recommended_engagement_sequence": pathway["steps"],
        "potential_barriers": barriers,
        "required_approvals": required_approvals or ["None identified at current alignment levels."],
        "required_partnerships": required_partnerships or ["None identified at current alignment levels."],
        "expected_outcomes": opp.expected_outcome,
        "confidence_assessment": {
            "confidence": opp.confidence,
            "readiness_score": readiness["readiness_score"],
            "readiness_label": readiness["readiness_label"],
        },
    }


# ─── V6.1 Phase L: Waste, Energy & Climate Intelligence ──────────────────────

def get_waste_energy_climate_intelligence(db: Session, days: int = 30) -> dict:
    """
    Phase L: a dedicated cross-section over the existing opportunity and
    stakeholder data, filtered to the strategic category cluster the spec
    names (Waste Management, Waste-to-Energy, Climate Finance, Renewable
    Energy, Rural Electrification, Energy Access, Carbon Markets,
    Infrastructure Development, Green Investment). This is a REPORTING
    VIEW, not a new data model -- it reuses generate_opportunity_assessments,
    get_top_opportunity_signals, and get_top_stakeholders, filtered to this
    category cluster, rather than duplicating their underlying logic.
    """
    from app.models.models import WASTE_ENERGY_CLIMATE_CATEGORIES
    from app.services.stakeholder_registry import get_top_opportunity_signals

    category_values = [c.value for c in WASTE_ENERGY_CLIMATE_CATEGORIES]

    opportunities = db.query(OpportunityAssessment).filter(
        OpportunityAssessment.category.in_(category_values)
    ).order_by(OpportunityAssessment.updated_at.desc()).all()

    all_signals = get_top_opportunity_signals(db, limit=30, days=days)
    category_signals = [s for s in all_signals if s.get("category") in category_values]

    from app.models.models import StakeholderRelationship, StakeholderRegistry
    relevant_stakeholder_ids = {
        r.from_stakeholder_id for r in db.query(StakeholderRelationship).filter(
            StakeholderRelationship.relevant_category.in_(category_values),
            StakeholderRelationship.is_active == True,
        ).all()
    } | {
        r.to_stakeholder_id for r in db.query(StakeholderRelationship).filter(
            StakeholderRelationship.relevant_category.in_(category_values),
            StakeholderRelationship.is_active == True,
        ).all()
    }
    stakeholder_lookup = {s.id: s for s in db.query(StakeholderRegistry).filter(StakeholderRegistry.id.in_(relevant_stakeholder_ids)).all()}

    return {
        "categories_tracked": category_values,
        "opportunities": [
            {"id": o.id, "title": o.title, "category": o.category, "status": o.status, "strategic_value": o.strategic_value}
            for o in opportunities
        ],
        "opportunity_signals": category_signals,
        "relevant_stakeholders": [
            {"id": sid, "name": s.name, "category": s.category, "sector": s.sector}
            for sid, s in stakeholder_lookup.items()
        ],
        "funding_signals": [
            s for s in category_signals if s.get("category") in ("CLIMATE_FINANCE", "GREEN_INVESTMENT", "DEVELOPMENT_FINANCE")
        ],
        "policy_signals": [
            s for s in category_signals if s.get("category") in ("FEDERAL_PROGRAMMES", "STATE_PROGRAMMES")
        ],
    }
