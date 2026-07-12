"""
NDIP V6.0 — Strategic Outcome Intelligence API Routes

This is the API surface for the registry and pipeline-management
capabilities that don't already flow through existing module routes
(National Pulse, Situation Room, Leadership Pack, etc. already return
V6.0 enrichment fields directly in their existing responses — see Phases
G/H/I/J/K of the completion report). This file covers:

  - Registry management (list/add stakeholders and opportunity types) —
    the "expand without code changes" capability the platform owner
    specifically required.
  - Stakeholder profile lookup (Phase D)
  - Opportunity pipeline listing and status advancement (Phase F)
  - Outcome chain logging (Phase E)
  - The consolidated Strategic Outcome Intelligence Dashboard (Phase N)
"""
import json
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.core.security import get_current_user
from app.models.models import (
    StakeholderRegistry, OpportunityRegistry, StakeholderProfile,
    OpportunityAssessment, OpportunityPipelineEvent, OutcomeChainLink,
    RecommendationRecord, StakeholderRelationship,
)
from app.schemas.schemas import (
    StakeholderRegistryCreate, OpportunityRegistryCreate,
    OpportunityStatusUpdate, OutcomeChainLinkCreate,
    StakeholderRelationshipCreate, StakeholderRegistryUpdate, OpportunityRegistryUpdate,
)
from app.services.cache import cache_key, get_cached, set_cached

# V6.2 Phase A -- cache TTL for the previously-uncached SOI Dashboard,
# shorter than Leadership Pack's 60min since this route re-detects
# opportunities from current discourse on every call.
TTL_SOI_DASHBOARD = 1800  # 30 min

router = APIRouter(prefix="/strategic-outcome", tags=["strategic-outcome-intelligence"])


@router.get("/registry/stakeholders")
def list_stakeholders(
    category: str = Query(None),
    active_only: bool = Query(True),
    db: Session = Depends(get_db),
    _: dict = Depends(get_current_user),
):
    q = db.query(StakeholderRegistry)
    if active_only:
        q = q.filter(StakeholderRegistry.is_active == True)
    if category:
        q = q.filter(StakeholderRegistry.category == category)
    rows = q.order_by(StakeholderRegistry.category, StakeholderRegistry.name).all()
    return {
        "count": len(rows),
        "stakeholders": [
            {
                "id": r.id, "name": r.name, "short_name": r.short_name,
                "category": r.category, "sector": r.sector,
                "role_description": r.role_description,
                "aliases": json.loads(r.aliases_json) if r.aliases_json else [],
                "is_active": r.is_active,
            } for r in rows
        ],
    }


@router.post("/registry/stakeholders", status_code=201)
def add_stakeholder(
    payload: StakeholderRegistryCreate,
    db: Session = Depends(get_db),
    _: dict = Depends(get_current_user),
):
    """
    Adds a new stakeholder to the registry. This is the mechanism by which
    NDIP's stakeholder coverage expands — no code change or redeployment
    required, per the platform owner's explicit instruction.
    """
    existing = db.query(StakeholderRegistry).filter(StakeholderRegistry.name == payload.name).first()
    if existing:
        raise HTTPException(status_code=400, detail=f"Stakeholder '{payload.name}' already exists (id={existing.id})")

    row = StakeholderRegistry(
        name=payload.name, short_name=payload.short_name, category=payload.category,
        sector=payload.sector, role_description=payload.role_description,
        aliases_json=json.dumps(payload.aliases) if payload.aliases else None,
        notes=payload.notes,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return {"id": row.id, "name": row.name, "message": "Stakeholder added to registry"}


@router.get("/registry/opportunities")
def list_opportunity_types(
    category: str = Query(None),
    active_only: bool = Query(True),
    db: Session = Depends(get_db),
    _: dict = Depends(get_current_user),
):
    q = db.query(OpportunityRegistry)
    if active_only:
        q = q.filter(OpportunityRegistry.is_active == True)
    if category:
        q = q.filter(OpportunityRegistry.category == category)
    rows = q.order_by(OpportunityRegistry.category, OpportunityRegistry.name).all()
    return {
        "count": len(rows),
        "opportunity_types": [
            {
                "id": r.id, "name": r.name, "category": r.category,
                "description": r.description,
                "aliases": json.loads(r.aliases_json) if r.aliases_json else [],
                "is_active": r.is_active,
            } for r in rows
        ],
    }


@router.post("/registry/opportunities", status_code=201)
def add_opportunity_type(
    payload: OpportunityRegistryCreate,
    db: Session = Depends(get_db),
    _: dict = Depends(get_current_user),
):
    """Adds a new opportunity programme type to the registry — same expand-without-code-change principle as stakeholders."""
    existing = db.query(OpportunityRegistry).filter(OpportunityRegistry.name == payload.name).first()
    if existing:
        raise HTTPException(status_code=400, detail=f"Opportunity type '{payload.name}' already exists (id={existing.id})")

    row = OpportunityRegistry(
        name=payload.name, category=payload.category, description=payload.description,
        aliases_json=json.dumps(payload.aliases) if payload.aliases else None,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return {"id": row.id, "name": row.name, "message": "Opportunity type added to registry"}


@router.get("/stakeholders/top")
def get_top_stakeholders_route(
    limit: int = Query(10, ge=1, le=50),
    days: int = Query(30, ge=1, le=90),
    db: Session = Depends(get_db),
    _: dict = Depends(get_current_user),
):
    from app.services.stakeholder_registry import get_top_stakeholders
    return {"stakeholders": get_top_stakeholders(db, limit=limit, days=days)}


@router.get("/stakeholders/{stakeholder_id}/profile")
def get_stakeholder_profile(
    stakeholder_id: int,
    days: int = Query(30, ge=1, le=90),
    db: Session = Depends(get_db),
    _: dict = Depends(get_current_user),
):
    """
    Phase D: full stakeholder profile — name, org, role, sector, all five
    scores, associated narratives/opportunities/programmes, recent
    activity, and monitoring priority.
    """
    stakeholder = db.query(StakeholderRegistry).filter(StakeholderRegistry.id == stakeholder_id).first()
    if not stakeholder:
        raise HTTPException(status_code=404, detail="Stakeholder not found")

    profile = db.query(StakeholderProfile).filter(
        StakeholderProfile.stakeholder_id == stakeholder_id,
        StakeholderProfile.period_days == days,
    ).order_by(StakeholderProfile.computed_at.desc()).first()

    if not profile:
        from app.services.stakeholder_registry import recompute_stakeholder_profiles
        recompute_stakeholder_profiles(db, days)
        profile = db.query(StakeholderProfile).filter(
            StakeholderProfile.stakeholder_id == stakeholder_id,
            StakeholderProfile.period_days == days,
        ).order_by(StakeholderProfile.computed_at.desc()).first()

    return {
        "stakeholder_name": stakeholder.name,
        "organisation": stakeholder.short_name or stakeholder.name,
        "role": stakeholder.role_description,
        "sector": stakeholder.sector,
        "category": stakeholder.category,
        "influence_score": profile.influence_score if profile else None,
        "visibility_score": profile.visibility_score if profile else None,
        "engagement_score": profile.engagement_score if profile else None,
        "opportunity_alignment_score": profile.opportunity_alignment_score if profile else None,
        "strategic_relevance_score": profile.strategic_relevance_score if profile else None,
        "associated_narratives": json.loads(profile.associated_narratives_json) if profile and profile.associated_narratives_json else [],
        "associated_opportunities": json.loads(profile.associated_opportunities_json) if profile and profile.associated_opportunities_json else [],
        "recent_activity": profile.recent_activity_summary if profile else "No activity recorded for this period.",
        "monitoring_priority": profile.monitoring_priority if profile else "Low",
        "data_available": profile is not None,
    }


@router.get("/opportunities")
def list_opportunities(
    status: str = Query(None),
    category: str = Query(None),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    _: dict = Depends(get_current_user),
):
    q = db.query(OpportunityAssessment)
    if status:
        q = q.filter(OpportunityAssessment.status == status)
    if category:
        q = q.filter(OpportunityAssessment.category == category)
    rows = q.order_by(OpportunityAssessment.updated_at.desc()).limit(limit).all()
    return {
        "count": len(rows),
        "opportunities": [
            {
                "id": o.id, "title": o.title, "category": o.category,
                "status": o.status, "strategic_value": o.strategic_value,
                "what_opportunity_exists": o.what_opportunity_exists,
                "why_it_matters": o.why_it_matters,
                "stakeholders": json.loads(o.stakeholders_json) if o.stakeholders_json else [],
                "recommended_engagement": o.recommended_engagement,
                "confidence": o.confidence,
                "evidence_post_count": o.evidence_post_count,
                "probability_of_success": o.probability_of_success,
                "next_milestone": o.next_milestone,
                "created_at": o.created_at.isoformat(),
                "updated_at": o.updated_at.isoformat(),
            } for o in rows
        ],
    }


@router.get("/opportunities/{opportunity_id}")
def get_opportunity_detail(
    opportunity_id: int,
    db: Session = Depends(get_db),
    _: dict = Depends(get_current_user),
):
    o = db.query(OpportunityAssessment).filter(OpportunityAssessment.id == opportunity_id).first()
    if not o:
        raise HTTPException(status_code=404, detail="Opportunity not found")
    events = db.query(OpportunityPipelineEvent).filter(
        OpportunityPipelineEvent.opportunity_id == opportunity_id
    ).order_by(OpportunityPipelineEvent.occurred_at.asc()).all()

    return {
        "id": o.id, "title": o.title, "category": o.category, "status": o.status,
        "strategic_value": o.strategic_value,
        "what_opportunity_exists": o.what_opportunity_exists,
        "why_it_matters": o.why_it_matters,
        "stakeholders": json.loads(o.stakeholders_json) if o.stakeholders_json else [],
        "recommended_engagement": o.recommended_engagement,
        "recommended_stakeholders_first": json.loads(o.recommended_stakeholders_first_json) if o.recommended_stakeholders_first_json else [],
        "expected_outcome": o.expected_outcome,
        "confidence": o.confidence,
        "evidence_post_count": o.evidence_post_count,
        "probability_of_success": o.probability_of_success,
        "next_milestone": o.next_milestone,
        "pipeline_history": [
            {
                "occurred_at": e.occurred_at.isoformat(), "event_type": e.event_type,
                "from_status": e.from_status, "to_status": e.to_status,
                "stakeholder_engaged": e.stakeholder_engaged, "description": e.description,
                "recorded_by": e.recorded_by,
            } for e in events
        ],
    }


@router.post("/opportunities/{opportunity_id}/advance")
def advance_opportunity(
    opportunity_id: int,
    payload: OpportunityStatusUpdate,
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """
    Phase F: moves an opportunity to a new pipeline status (Detected ->
    Assessed -> Engaged -> In Progress -> Advanced -> Secured/Closed/Expired)
    and logs the transition. This is the leadership-facing action endpoint
    ("Mark as Engaged", "Log meeting outcome", etc.).
    """
    from app.services.opportunity_intelligence import advance_opportunity_status
    try:
        opp = advance_opportunity_status(
            db, opportunity_id, payload.new_status, payload.description,
            stakeholder_engaged=payload.stakeholder_engaged,
            recorded_by=user.get("email"),
            probability_of_success=payload.probability_of_success,
            next_milestone=payload.next_milestone,
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return {"id": opp.id, "status": opp.status, "message": "Opportunity status updated"}


@router.post("/opportunities/generate")
def trigger_opportunity_generation(
    days: int = Query(30, ge=1, le=90),
    db: Session = Depends(get_db),
    _: dict = Depends(get_current_user),
):
    """
    Manually triggers a scan of current discourse for opportunity signals
    and promotes any at/above the evidence threshold to tracked
    OpportunityAssessment rows. (This also runs automatically as part of
    the dashboard endpoint below, but is exposed standalone for
    administration/testing.)
    """
    from app.services.opportunity_intelligence import generate_opportunity_assessments
    return generate_opportunity_assessments(db, days)


@router.get("/opportunities/pipeline/summary")
def pipeline_summary(
    db: Session = Depends(get_db),
    _: dict = Depends(get_current_user),
):
    from app.services.opportunity_intelligence import get_opportunity_pipeline_summary
    return {"pipeline_summary": get_opportunity_pipeline_summary(db)}


@router.post("/outcome-chain", status_code=201)
def log_outcome_chain_link(
    payload: OutcomeChainLinkCreate,
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """
    Phase E: logs a step in the Recommendation -> Leadership Action ->
    Stakeholder Engagement -> Outcome -> Impact chain for an existing
    RecommendationRecord. Each field is optional and can be filled in
    incrementally as the real-world process unfolds (e.g. log the
    leadership action today, the stakeholder engagement next week).
    """
    rec = db.query(RecommendationRecord).filter(RecommendationRecord.id == payload.recommendation_id).first()
    if not rec:
        raise HTTPException(status_code=404, detail="Recommendation not found")

    from datetime import datetime, timezone
    now = datetime.now(timezone.utc)
    link = OutcomeChainLink(
        recommendation_id=payload.recommendation_id,
        opportunity_id=payload.opportunity_id,
        leadership_action=payload.leadership_action,
        leadership_action_date=now if payload.leadership_action else None,
        stakeholder_engagement=payload.stakeholder_engagement,
        stakeholder_engagement_date=now if payload.stakeholder_engagement else None,
        outcome=payload.outcome,
        outcome_date=now if payload.outcome else None,
        impact=payload.impact,
        impact_date=now if payload.impact else None,
        recorded_by=user.get("email"),
    )
    db.add(link)
    db.commit()
    db.refresh(link)
    return {"id": link.id, "message": "Outcome chain link recorded"}


@router.get("/outcome-chain/{recommendation_id}")
def get_outcome_chain(
    recommendation_id: int,
    db: Session = Depends(get_db),
    _: dict = Depends(get_current_user),
):
    links = db.query(OutcomeChainLink).filter(
        OutcomeChainLink.recommendation_id == recommendation_id
    ).order_by(OutcomeChainLink.created_at.asc()).all()
    return {
        "recommendation_id": recommendation_id,
        "chain": [
            {
                "id": l.id, "created_at": l.created_at.isoformat(),
                "leadership_action": l.leadership_action,
                "stakeholder_engagement": l.stakeholder_engagement,
                "outcome": l.outcome, "impact": l.impact,
                "recorded_by": l.recorded_by,
            } for l in links
        ],
    }


@router.get("/dashboard")
def strategic_outcome_dashboard(
    days: int = Query(30, ge=1, le=90),
    db: Session = Depends(get_db),
    _: dict = Depends(get_current_user),
):
    """
    Phase N: the consolidated executive dashboard combining everything
    V6.0 added — top opportunities, stakeholder rankings, the opportunity
    pipeline, engagement priorities, the outcome tracker's strategic
    metrics, and decision quality. Generates fresh opportunity assessments
    from current discourse before returning, so the dashboard always
    reflects up-to-date signal detection rather than only previously
    promoted opportunities.
    """
    _cache_key = cache_key("soi-dashboard", f"days={days}")
    _cached = get_cached(_cache_key)
    if _cached is not None:
        _cached["_cached"] = True
        return _cached

    from app.services.opportunity_intelligence import (
        generate_opportunity_assessments, get_top_opportunities, get_opportunity_pipeline_summary,
    )
    from app.services.stakeholder_registry import get_top_stakeholders
    from app.services.intelligence_learning import run_intelligence_learning_cycle

    generation_result = generate_opportunity_assessments(db, days)

    top_opportunities = get_top_opportunities(db, limit=10)
    pipeline_summary_data = get_opportunity_pipeline_summary(db)
    top_stakeholders = get_top_stakeholders(db, limit=10, days=days)
    learning_cycle = run_intelligence_learning_cycle(db)

    value_counts = {"Critical": 0, "High": 0, "Medium": 0, "Low": 0}
    for o in top_opportunities:
        sv = o.get("strategic_value", "Low")
        value_counts[sv] = value_counts.get(sv, 0) + 1

    engagement_priorities = [
        s for s in top_stakeholders if s.get("monitoring_priority") in ("High", "Critical")
    ][:5]

    # V6.1.2 Phase B -- dossier-derived Decision Makers / Funding Sources /
    # Implementation breakdown per opportunity, reusing
    # generate_opportunity_dossier (no new computation engine; classifies
    # the same already-computed alignment data by real stakeholder_type).
    opportunity_dossiers = []
    try:
        from app.services.opportunity_dossier import generate_opportunity_dossier
        for o in top_opportunities[:10]:
            opp_id = o.get("id") or o.get("opportunity_id")
            if opp_id is None:
                continue
            try:
                dossier = generate_opportunity_dossier(db, opp_id)
                opportunity_dossiers.append({
                    "opportunity_id": opp_id,
                    "title": dossier["opportunity_assessment"],
                    "decision_makers": dossier["stakeholders_by_role"]["Decision Makers"],
                    "funding_sources": dossier["stakeholders_by_role"]["Funding Sources"],
                    "implementation": dossier["stakeholders_by_role"]["Implementation"],
                    "data_quality_notes": dossier["data_quality_notes"],
                })
            except Exception:
                continue
    except Exception:
        opportunity_dossiers = []

    result = {
        "period_days": days,
        "generation_summary": generation_result,
        "top_opportunities": top_opportunities,
        "stakeholder_rankings": top_stakeholders,
        "engagement_priorities": engagement_priorities,
        "opportunity_pipeline": pipeline_summary_data,
        "strategic_value_distribution": value_counts,
        "decision_quality_metrics": learning_cycle.get("decision_quality_metrics"),
        "strategic_outcome_metrics": learning_cycle.get("strategic_outcome_metrics"),
        "platform_learning_score": learning_cycle.get("platform_learning_score"),
        "opportunity_dossiers": opportunity_dossiers,
    }
    set_cached(_cache_key, result, TTL_SOI_DASHBOARD)
    return result


# ─── V6.1 Phase A: Stakeholder Influence Analysis ──────────────────────────────

@router.get("/v61/stakeholders/influence/top")
def get_top_stakeholder_influence(
    limit: int = Query(10, ge=1, le=50),
    days: int = Query(30, ge=1, le=90),
    db: Session = Depends(get_db),
    _: dict = Depends(get_current_user),
):
    from app.services.stakeholder_influence import get_top_influence_stakeholders
    return {"stakeholders": get_top_influence_stakeholders(db, limit=limit, days=days)}


@router.get("/v61/stakeholders/{stakeholder_id}/influence")
def get_stakeholder_influence_detail(
    stakeholder_id: int,
    days: int = Query(30, ge=1, le=90),
    db: Session = Depends(get_db),
    _: dict = Depends(get_current_user),
):
    from app.services.stakeholder_influence import compute_stakeholder_influence
    try:
        return compute_stakeholder_influence(db, stakeholder_id, days)
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))


# ─── V6.1 Phase B: Stakeholder Network Mapping ─────────────────────────────────

@router.get("/v61/stakeholders/{stakeholder_id}/relationships")
def get_relationships(
    stakeholder_id: int,
    db: Session = Depends(get_db),
    _: dict = Depends(get_current_user),
):
    from app.services.stakeholder_influence import get_stakeholder_relationships
    return get_stakeholder_relationships(db, stakeholder_id)


@router.get("/v61/stakeholders/{stakeholder_id}/dependency-chain")
def get_dependency_chain(
    stakeholder_id: int,
    db: Session = Depends(get_db),
    _: dict = Depends(get_current_user),
):
    from app.services.stakeholder_influence import build_dependency_chain
    return {"stakeholder_id": stakeholder_id, "chain": build_dependency_chain(db, stakeholder_id)}


@router.get("/v61/network/graph")
def get_network_graph_route(
    category: str = Query(None),
    db: Session = Depends(get_db),
    _: dict = Depends(get_current_user),
):
    from app.services.stakeholder_influence import get_network_graph
    return get_network_graph(db, category)


@router.post("/v61/relationships", status_code=201)
def add_relationship(
    payload: StakeholderRelationshipCreate,
    db: Session = Depends(get_db),
    _: dict = Depends(get_current_user),
):
    """Phase K: registry-management endpoint for adding a new stakeholder relationship without a code change."""
    from_exists = db.query(StakeholderRegistry).filter(StakeholderRegistry.id == payload.from_stakeholder_id).first()
    to_exists = db.query(StakeholderRegistry).filter(StakeholderRegistry.id == payload.to_stakeholder_id).first()
    if not from_exists or not to_exists:
        raise HTTPException(status_code=404, detail="One or both stakeholders not found")

    row = StakeholderRelationship(
        from_stakeholder_id=payload.from_stakeholder_id, to_stakeholder_id=payload.to_stakeholder_id,
        relationship_type=payload.relationship_type, description=payload.description,
        relevant_category=payload.relevant_category,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return {"id": row.id, "message": "Relationship added"}


@router.get("/v61/relationships")
def list_relationships(
    db: Session = Depends(get_db),
    _: dict = Depends(get_current_user),
):
    lookup = {s.id: s.name for s in db.query(StakeholderRegistry).all()}
    rows = db.query(StakeholderRelationship).filter(StakeholderRelationship.is_active == True).all()
    return {
        "count": len(rows),
        "relationships": [
            {
                "id": r.id, "from": lookup.get(r.from_stakeholder_id), "to": lookup.get(r.to_stakeholder_id),
                "type": r.relationship_type, "description": r.description, "relevant_category": r.relevant_category,
            } for r in rows
        ],
    }


@router.delete("/v61/relationships/{relationship_id}")
def delete_relationship(
    relationship_id: int,
    db: Session = Depends(get_db),
    _: dict = Depends(get_current_user),
):
    """Phase K: soft-delete (deactivate) rather than hard-delete, preserving history."""
    row = db.query(StakeholderRelationship).filter(StakeholderRelationship.id == relationship_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="Relationship not found")
    row.is_active = False
    db.commit()
    return {"message": "Relationship deactivated"}


# ─── V6.1 Phase D: Opportunity Alignment Engine ────────────────────────────────

@router.get("/v61/opportunities/{opportunity_id}/alignment")
def get_opportunity_alignment(
    opportunity_id: int,
    db: Session = Depends(get_db),
    _: dict = Depends(get_current_user),
):
    from app.services.opportunity_intelligence import compute_and_store_opportunity_alignment
    return {"opportunity_id": opportunity_id, "alignment": compute_and_store_opportunity_alignment(db, opportunity_id)}


# ─── V6.1 Phase E: Opportunity Readiness Index ─────────────────────────────────

@router.get("/v61/opportunities/{opportunity_id}/readiness")
def get_opportunity_readiness_route(
    opportunity_id: int,
    db: Session = Depends(get_db),
    _: dict = Depends(get_current_user),
):
    from app.services.opportunity_intelligence import compute_and_store_readiness
    try:
        return compute_and_store_readiness(db, opportunity_id)
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))


# ─── V6.1 Phase F: Engagement Pathway Engine ───────────────────────────────────

@router.get("/v61/opportunities/{opportunity_id}/pathway")
def get_pathway(
    opportunity_id: int,
    regenerate: bool = Query(False),
    db: Session = Depends(get_db),
    _: dict = Depends(get_current_user),
):
    from app.services.opportunity_intelligence import generate_engagement_pathway, get_current_pathway
    try:
        if regenerate:
            return generate_engagement_pathway(db, opportunity_id)
        return get_current_pathway(db, opportunity_id)
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/v61/pathway-steps/{step_id}/complete")
def complete_pathway_step(
    step_id: int,
    db: Session = Depends(get_db),
    _: dict = Depends(get_current_user),
):
    from app.models.models import EngagementStep
    from datetime import datetime, timezone
    step = db.query(EngagementStep).filter(EngagementStep.id == step_id).first()
    if not step:
        raise HTTPException(status_code=404, detail="Step not found")
    step.status = "Complete"
    step.completed_at = datetime.now(timezone.utc)
    db.commit()
    return {"id": step.id, "status": step.status}


# ─── V6.1 Phase C: Opportunity Execution Plan ───────────────────────────────────

@router.get("/v61/opportunities/{opportunity_id}/execution-plan")
def get_execution_plan(
    opportunity_id: int,
    db: Session = Depends(get_db),
    _: dict = Depends(get_current_user),
):
    from app.services.opportunity_intelligence import generate_execution_plan
    try:
        return generate_execution_plan(db, opportunity_id)
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/v611/opportunities/{opportunity_id}/dossier")
def get_opportunity_dossier(
    opportunity_id: int,
    db: Session = Depends(get_db),
    _: dict = Depends(get_current_user),
):
    """V6.1.1 Phase F -- Executive Opportunity Dossier, structuring the existing execution plan into the dossier's named sections (Decision Makers, Funding Sources, Implementation, Oversight)."""
    _cache_key = cache_key("opportunity-dossier", f"opportunity_id={opportunity_id}")
    _cached = get_cached(_cache_key)
    if _cached is not None:
        _cached["_cached"] = True
        return _cached
    from app.services.opportunity_dossier import generate_opportunity_dossier
    try:
        result = generate_opportunity_dossier(db, opportunity_id)
        set_cached(_cache_key, result, TTL_SOI_DASHBOARD)
        return result
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))


# ─── V6.1 Phase G: Stakeholder Momentum Tracker ────────────────────────────────

@router.get("/v61/stakeholders/{stakeholder_id}/momentum")
def get_momentum(
    stakeholder_id: int,
    days: int = Query(30, ge=1, le=90),
    db: Session = Depends(get_db),
    _: dict = Depends(get_current_user),
):
    from app.services.stakeholder_influence import get_stakeholder_momentum
    return get_stakeholder_momentum(db, stakeholder_id, days)


# ─── V6.1 Phase L: Waste, Energy & Climate Intelligence ────────────────────────

@router.get("/v61/waste-energy-climate")
def get_waste_energy_climate(
    days: int = Query(30, ge=1, le=90),
    db: Session = Depends(get_db),
    _: dict = Depends(get_current_user),
):
    from app.services.opportunity_intelligence import get_waste_energy_climate_intelligence
    return get_waste_energy_climate_intelligence(db, days)


# ─── V6.1 Phase J: Learning Loop Expansion ─────────────────────────────────────

@router.get("/v61/learning/stakeholder-effectiveness")
def get_stakeholder_effectiveness(
    db: Session = Depends(get_db),
    _: dict = Depends(get_current_user),
):
    from app.services.intelligence_learning import compute_stakeholder_effectiveness_scores
    return compute_stakeholder_effectiveness_scores(db)


# ─── V6.1 Phase K: Registry Management (update/delete, completing the admin UI's backend) ──

@router.patch("/registry/stakeholders/{stakeholder_id}")
def update_stakeholder(
    stakeholder_id: int,
    payload: StakeholderRegistryUpdate,
    db: Session = Depends(get_db),
    _: dict = Depends(get_current_user),
):
    row = db.query(StakeholderRegistry).filter(StakeholderRegistry.id == stakeholder_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="Stakeholder not found")
    data = payload.dict(exclude_unset=True)
    if "aliases" in data:
        row.aliases_json = json.dumps(data.pop("aliases"))
    for key, value in data.items():
        setattr(row, key, value)
    db.commit()
    return {"id": row.id, "message": "Stakeholder updated"}


@router.delete("/registry/stakeholders/{stakeholder_id}")
def deactivate_stakeholder(
    stakeholder_id: int,
    db: Session = Depends(get_db),
    _: dict = Depends(get_current_user),
):
    """Soft-delete: deactivates rather than hard-deletes, since stakeholder history (mentions, profiles) must remain valid."""
    row = db.query(StakeholderRegistry).filter(StakeholderRegistry.id == stakeholder_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="Stakeholder not found")
    row.is_active = False
    db.commit()
    return {"message": "Stakeholder deactivated"}


@router.patch("/registry/opportunities/{opportunity_type_id}")
def update_opportunity_type(
    opportunity_type_id: int,
    payload: OpportunityRegistryUpdate,
    db: Session = Depends(get_db),
    _: dict = Depends(get_current_user),
):
    row = db.query(OpportunityRegistry).filter(OpportunityRegistry.id == opportunity_type_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="Opportunity type not found")
    data = payload.dict(exclude_unset=True)
    if "aliases" in data:
        row.aliases_json = json.dumps(data.pop("aliases"))
    for key, value in data.items():
        setattr(row, key, value)
    db.commit()
    return {"id": row.id, "message": "Opportunity type updated"}


@router.delete("/registry/opportunities/{opportunity_type_id}")
def deactivate_opportunity_type(
    opportunity_type_id: int,
    db: Session = Depends(get_db),
    _: dict = Depends(get_current_user),
):
    row = db.query(OpportunityRegistry).filter(OpportunityRegistry.id == opportunity_type_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="Opportunity type not found")
    row.is_active = False
    db.commit()
    return {"message": "Opportunity type deactivated"}
