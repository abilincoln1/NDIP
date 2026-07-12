"""
NDIP Phase C — Adaptive Learning API Router
All learning domain endpoints under /api/learning/
Zero changes to existing routes.
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import Optional, List
from datetime import datetime, timezone, timedelta
from pydantic import BaseModel
import uuid

from app.db.database import get_db
from app.core.security import get_current_user

from app.phase_c.services.event_service import (
    emit_decision_recorded,
    emit_outcome_recorded,
    emit_feedback_submitted,
    emit_learning_event_created,
    emit_knowledge_created,
)

router = APIRouter(prefix="/api/learning", tags=["adaptive_learning"])

# Checkpoint schedule in days
CHECKPOINT_DAYS = [30, 60, 90, 180, 365]


# ─── Pydantic Schemas ──────────────────────────────────────────────────────

class DecisionCreate(BaseModel):
    decision_type: str              # accept/reject/defer/modify/partially_accept/cancel
    rationale: Optional[str] = None
    notes: Optional[str] = None
    rejection_category: Optional[str] = None
    modified_recommendation: Optional[str] = None
    modification_reason: Optional[str] = None
    approving_executive: Optional[str] = None
    usefulness_score: Optional[int] = None
    clarity_score: Optional[int] = None
    accuracy_score: Optional[int] = None


class OutcomeCreate(BaseModel):
    outcome_type: str               # successful/partially_successful/unsuccessful/unable_to_evaluate
    expected_outcome: str
    actual_outcome: str
    variance_description: Optional[str] = None
    variance_score: Optional[float] = None
    lessons_learned: Optional[str] = None
    contributing_factors: Optional[str] = None
    unexpected_consequences: Optional[str] = None
    counterfactual: Optional[str] = None
    checkpoint_id: Optional[str] = None


class FeedbackCreate(BaseModel):
    feedback_type: str              # recommendation/dashboard/copilot/outcome
    target_id: Optional[str] = None
    target_type: Optional[str] = None
    rating: str                     # helpful/not_helpful/partially_helpful/incorrect/needs_evidence
    usefulness_score: Optional[int] = None
    accuracy_score: Optional[int] = None
    clarity_score: Optional[int] = None
    free_text: Optional[str] = None
    dashboard_context: Optional[str] = None


class MemoryCreate(BaseModel):
    memory_type: str
    title: str
    content: str
    tags: Optional[List[str]] = []
    entities: Optional[List[str]] = []
    confidence_score: Optional[float] = 0.5


class LearningEventValidate(BaseModel):
    validation_status: str          # validated/rejected
    notes: Optional[str] = None


# ─── Recommendations ──────────────────────────────────────────────────────

@router.get("/recommendations")
async def list_recommendations(
    status: Optional[str] = None,
    category: Optional[str] = None,
    limit: int = Query(default=50, le=200),
    offset: int = 0,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """List all registered recommendations with optional filters."""
    filters = ["1=1"]
    params = {"limit": limit, "offset": offset}

    if status:
        filters.append("status = :status")
        params["status"] = status
    if category:
        filters.append("category = :category")
        params["category"] = category

    where = " AND ".join(filters)

    rows = db.execute(text(f"""
        SELECT id, created_at, category, recommendation_type,
               source_dashboard, title, recommendation_text,
               confidence_at_creation, risk_score, expected_outcome,
               expected_horizon_days, status, created_by,
               is_backfilled, view_count, tags
        FROM recommendations
        WHERE {where}
        ORDER BY created_at DESC
        LIMIT :limit OFFSET :offset
    """), params).fetchall()

    total = db.execute(text(f"""
        SELECT COUNT(*) FROM recommendations WHERE {where}
    """), params).scalar()

    return {
        "total": total,
        "limit": limit,
        "offset": offset,
        "recommendations": [dict(r._mapping) for r in rows]
    }


@router.get("/recommendations/{recommendation_id}")
async def get_recommendation(
    recommendation_id: str,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Get full recommendation detail including decisions, outcomes, and learning."""
    rec = db.execute(text("""
        SELECT * FROM recommendations WHERE id = :id
    """), {"id": recommendation_id}).fetchone()

    if not rec:
        raise HTTPException(status_code=404, detail="Recommendation not found")

    # Update view tracking
    db.execute(text("""
        UPDATE recommendations
        SET view_count = view_count + 1,
            last_viewed_at = NOW(),
            first_viewed_at = COALESCE(first_viewed_at, NOW())
        WHERE id = :id
    """), {"id": recommendation_id})
    db.commit()

    # Fetch related records
    decisions = db.execute(text("""
        SELECT * FROM recommendation_decisions
        WHERE recommendation_id = :id
        ORDER BY created_at DESC
    """), {"id": recommendation_id}).fetchall()

    checkpoints = db.execute(text("""
        SELECT * FROM outcome_checkpoints
        WHERE recommendation_id = :id
        ORDER BY checkpoint_number ASC
    """), {"id": recommendation_id}).fetchall()

    outcomes = db.execute(text("""
        SELECT * FROM recommendation_outcomes
        WHERE recommendation_id = :id
        ORDER BY recorded_at DESC
    """), {"id": recommendation_id}).fetchall()

    learning = db.execute(text("""
        SELECT * FROM learning_events
        WHERE source_recommendation_id = :id
        ORDER BY occurred_at DESC
    """), {"id": recommendation_id}).fetchall()

    return {
        "recommendation":   dict(rec._mapping),
        "decisions":        [dict(r._mapping) for r in decisions],
        "checkpoints":      [dict(r._mapping) for r in checkpoints],
        "outcomes":         [dict(r._mapping) for r in outcomes],
        "learning_events":  [dict(r._mapping) for r in learning],
    }


# ─── Decisions ────────────────────────────────────────────────────────────

@router.post("/recommendations/{recommendation_id}/decisions")
async def record_decision(
    recommendation_id: str,
    body: DecisionCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    Record a decision on a recommendation.
    If accepted/modified/partially_accepted: schedules outcome checkpoints automatically.
    """
    # Verify recommendation exists
    rec = db.execute(text("""
        SELECT id, status, expected_horizon_days
        FROM recommendations WHERE id = :id
    """), {"id": recommendation_id}).fetchone()

    if not rec:
        raise HTTPException(status_code=404, detail="Recommendation not found")

    decision_id = str(uuid.uuid4())
    user_id = str(current_user.id if hasattr(current_user, "id") else current_user.get("id") or current_user.get("sub", "unknown"))

    # Insert decision record
    db.execute(text("""
        INSERT INTO recommendation_decisions
            (id, recommendation_id, decision_type, decided_by, decided_at,
             approving_executive, rationale, notes,
             modified_recommendation, modification_reason,
             rejection_category, usefulness_score, clarity_score, accuracy_score)
        VALUES
            (:id, :recommendation_id, :decision_type, :decided_by, NOW(),
             :approving_executive, :rationale, :notes,
             :modified_recommendation, :modification_reason,
             :rejection_category, :usefulness_score, :clarity_score, :accuracy_score)
    """), {
        "id":                       decision_id,
        "recommendation_id":        recommendation_id,
        "decision_type":            body.decision_type,
        "decided_by":               user_id,
        "approving_executive":      body.approving_executive,
        "rationale":                body.rationale,
        "notes":                    body.notes,
        "modified_recommendation":  body.modified_recommendation,
        "modification_reason":      body.modification_reason,
        "rejection_category":       body.rejection_category,
        "usefulness_score":         body.usefulness_score,
        "clarity_score":            body.clarity_score,
        "accuracy_score":           body.accuracy_score,
    })

    # Update recommendation status
    new_status = body.decision_type if body.decision_type in [
        'rejected', 'deferred', 'cancelled'
    ] else 'accepted'
    if body.decision_type == 'partially_accept':
        new_status = 'accepted'

    db.execute(text("""
        UPDATE recommendations SET status = :status WHERE id = :id
    """), {"status": new_status, "id": recommendation_id})

    # Schedule checkpoints if accepted
    checkpoint_dates = []
    if body.decision_type in ['accept', 'modify', 'partially_accept']:
        now = datetime.now(timezone.utc)
        for i, days in enumerate(CHECKPOINT_DAYS, 1):
            due_date = now + timedelta(days=days)
            checkpoint_dates.append(due_date.isoformat())
            db.execute(text("""
                INSERT INTO outcome_checkpoints
                    (id, recommendation_id, checkpoint_number, due_date, due_days, status)
                VALUES
                    (:id, :recommendation_id, :number, :due_date, :due_days, 'pending')
                ON CONFLICT (recommendation_id, checkpoint_number) DO NOTHING
            """), {
                "id":               str(uuid.uuid4()),
                "recommendation_id": recommendation_id,
                "number":           i,
                "due_date":         due_date,
                "due_days":         days,
            })

    # Emit event
    emit_decision_recorded(
        db=db,
        recommendation_id=recommendation_id,
        decision_id=decision_id,
        decision_type=body.decision_type,
        decided_by=user_id,
        checkpoint_dates=checkpoint_dates,
    )

    db.commit()

    return {
        "decision_id":          decision_id,
        "recommendation_id":    recommendation_id,
        "decision_type":        body.decision_type,
        "status_updated_to":    new_status,
        "checkpoints_scheduled": len(checkpoint_dates),
        "checkpoint_dates":     checkpoint_dates,
    }


# ─── Checkpoints ──────────────────────────────────────────────────────────

@router.get("/checkpoints/pending")
async def get_pending_checkpoints(
    overdue_only: bool = False,
    limit: int = Query(default=20, le=100),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Get pending outcome checkpoints, optionally filtered to overdue only."""
    where = "oc.status = 'pending'"
    if overdue_only:
        where += " AND oc.due_date < NOW()"

    rows = db.execute(text(f"""
        SELECT
            oc.id AS checkpoint_id,
            oc.recommendation_id,
            oc.checkpoint_number,
            oc.due_date,
            oc.due_days,
            oc.status,
            EXTRACT(DAYS FROM NOW() - oc.due_date) AS days_overdue,
            r.title AS recommendation_title,
            r.category,
            r.expected_outcome,
            r.confidence_at_creation
        FROM outcome_checkpoints oc
        JOIN recommendations r ON r.id = oc.recommendation_id
        WHERE {where}
        ORDER BY oc.due_date ASC
        LIMIT :limit
    """), {"limit": limit}).fetchall()

    return {"checkpoints": [dict(r._mapping) for r in rows]}


# ─── Outcomes ─────────────────────────────────────────────────────────────

@router.post("/recommendations/{recommendation_id}/outcomes")
async def record_outcome(
    recommendation_id: str,
    body: OutcomeCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    Record an outcome for a recommendation.
    Automatically triggers evaluation and Bayesian confidence update.
    """
    rec = db.execute(text("""
        SELECT id, category, confidence_at_creation, expected_horizon_days
        FROM recommendations WHERE id = :id
    """), {"id": recommendation_id}).fetchone()

    if not rec:
        raise HTTPException(status_code=404, detail="Recommendation not found")

    user_id = str(current_user.id if hasattr(current_user, "id") else current_user.get("id") or current_user.get("sub", "unknown"))
    outcome_id = str(uuid.uuid4())

    # Get days since decision (for delay calculation)
    decision = db.execute(text("""
        SELECT decided_at FROM recommendation_decisions
        WHERE recommendation_id = :id
        ORDER BY decided_at ASC LIMIT 1
    """), {"id": recommendation_id}).fetchone()

    delay_days = None
    if decision and decision.decided_at:
        elapsed = datetime.now(timezone.utc) - decision.decided_at.replace(tzinfo=timezone.utc)
        delay_days = elapsed.days

    # Insert outcome
    db.execute(text("""
        INSERT INTO recommendation_outcomes
            (id, recommendation_id, checkpoint_id, recorded_by, recorded_at,
             outcome_type, expected_outcome, actual_outcome,
             variance_description, variance_score, delay_days,
             unexpected_consequences, lessons_learned,
             contributing_factors, counterfactual)
        VALUES
            (:id, :recommendation_id, :checkpoint_id, :recorded_by, NOW(),
             :outcome_type, :expected_outcome, :actual_outcome,
             :variance_description, :variance_score, :delay_days,
             :unexpected_consequences, :lessons_learned,
             :contributing_factors, :counterfactual)
    """), {
        "id":                       outcome_id,
        "recommendation_id":        recommendation_id,
        "checkpoint_id":            body.checkpoint_id,
        "recorded_by":              user_id,
        "outcome_type":             body.outcome_type,
        "expected_outcome":         body.expected_outcome,
        "actual_outcome":           body.actual_outcome,
        "variance_description":     body.variance_description,
        "variance_score":           body.variance_score,
        "delay_days":               delay_days,
        "unexpected_consequences":  body.unexpected_consequences,
        "lessons_learned":          body.lessons_learned,
        "contributing_factors":     body.contributing_factors,
        "counterfactual":           body.counterfactual,
    })

    # Mark checkpoint as completed
    if body.checkpoint_id:
        db.execute(text("""
            UPDATE outcome_checkpoints
            SET status = 'completed', completed_at = NOW()
            WHERE id = :id
        """), {"id": body.checkpoint_id})

    # Update recommendation status
    db.execute(text("""
        UPDATE recommendations SET status = 'evaluating' WHERE id = :id
    """), {"id": recommendation_id})

    # Emit outcome recorded event
    emit_outcome_recorded(
        db=db,
        recommendation_id=recommendation_id,
        outcome_id=outcome_id,
        outcome_type=body.outcome_type,
        variance_score=body.variance_score or 0.5,
        recorded_by=user_id,
    )

    db.commit()

    # Run automatic evaluation (non-blocking)
    evaluation_result = _run_automatic_evaluation(
        db=db,
        outcome_id=outcome_id,
        recommendation_id=recommendation_id,
        outcome_type=body.outcome_type,
        variance_score=body.variance_score,
        category=rec.category,
        confidence_at_creation=rec.confidence_at_creation,
        lessons_learned=body.lessons_learned,
    )

    return {
        "outcome_id":           outcome_id,
        "recommendation_id":    recommendation_id,
        "outcome_type":         body.outcome_type,
        "evaluation_triggered": True,
        "evaluation_result":    evaluation_result,
    }


def _run_automatic_evaluation(
    db: Session,
    outcome_id: str,
    recommendation_id: str,
    outcome_type: str,
    variance_score: Optional[float],
    category: str,
    confidence_at_creation: float,
    lessons_learned: Optional[str] = None,
) -> dict:
    """
    Automatically evaluate an outcome and update Bayesian confidence.
    This is the core of the closed learning loop.
    """
    # Map outcome type to success score
    success_scores = {
        "successful":           1.0,
        "partially_successful": 0.5,
        "unsuccessful":         0.0,
        "unable_to_evaluate":   None,  # No confidence update for unevaluable
    }
    success_score = success_scores.get(outcome_type)

    if success_score is None:
        return {"status": "skipped", "reason": "unable_to_evaluate"}

    # Use variance_score if provided, otherwise use success_score
    if variance_score is not None:
        effective_score = (success_score + variance_score) / 2
    else:
        effective_score = success_score

    # Classify outcome
    if effective_score >= 0.8:
        classification = "strong_success"
    elif effective_score >= 0.6:
        classification = "success"
    elif effective_score >= 0.4:
        classification = "partial"
    elif effective_score >= 0.2:
        classification = "failure"
    else:
        classification = "strong_failure"

    # Get current calibration for this category
    calibration = db.execute(text("""
        SELECT posterior_confidence, sample_size, success_count,
               failure_count, partial_count
        FROM confidence_calibrations
        WHERE recommendation_category = :category
        ORDER BY created_at DESC LIMIT 1
    """), {"category": category}).fetchone()

    if calibration:
        prior = calibration.posterior_confidence
        prior_weight = max(calibration.sample_size, 10)  # Min weight of 10
        success_count = calibration.success_count
        failure_count = calibration.failure_count
        partial_count = calibration.partial_count
    else:
        prior = confidence_at_creation
        prior_weight = 10
        success_count = 0
        failure_count = 0
        partial_count = 0

    # Bayesian update
    evidence_weight = 0.7  # Standard evidence quality for automated evaluation
    posterior = (prior * prior_weight + effective_score * evidence_weight) / \
                (prior_weight + evidence_weight)
    posterior = round(max(0.1, min(0.99, posterior)), 4)
    calibration_delta = round(posterior - prior, 4)

    # Update counts
    if outcome_type == "successful":
        success_count += 1
    elif outcome_type == "unsuccessful":
        failure_count += 1
    else:
        partial_count += 1

    new_sample_size = (calibration.sample_size if calibration else 0) + 1

    # Create evaluation record
    evaluation_id = str(uuid.uuid4())
    db.execute(text("""
        INSERT INTO outcome_evaluations
            (id, outcome_id, recommendation_id, evaluated_at,
             evaluation_method, success_classification, success_score,
             confidence_before, confidence_after, calibration_delta,
             evidence_quality)
        VALUES
            (:id, :outcome_id, :recommendation_id, NOW(),
             'automatic', :success_classification, :success_score,
             :confidence_before, :confidence_after, :calibration_delta,
             :evidence_quality)
    """), {
        "id":                   evaluation_id,
        "outcome_id":           outcome_id,
        "recommendation_id":    recommendation_id,
        "success_classification": classification,
        "success_score":        effective_score,
        "confidence_before":    prior,
        "confidence_after":     posterior,
        "calibration_delta":    calibration_delta,
        "evidence_quality":     evidence_weight,
    })

    # Create new calibration record (append-only)
    calibration_id = str(uuid.uuid4())
    db.execute(text("""
        INSERT INTO confidence_calibrations
            (id, recommendation_category, prior_confidence, posterior_confidence,
             sample_size, success_count, failure_count, partial_count,
             update_reason, evidence_weight, bayesian_prior_weight,
             triggered_by_evaluation_id, model_version)
        VALUES
            (:id, :category, :prior, :posterior,
             :sample_size, :success_count, :failure_count, :partial_count,
             :update_reason, :evidence_weight, :prior_weight,
             :evaluation_id, 'v1.0')
    """), {
        "id":               calibration_id,
        "category":         category,
        "prior":            prior,
        "posterior":        posterior,
        "sample_size":      new_sample_size,
        "success_count":    success_count,
        "failure_count":    failure_count,
        "partial_count":    partial_count,
        "update_reason":    f"outcome_{outcome_type}",
        "evidence_weight":  evidence_weight,
        "prior_weight":     float(prior_weight),
        "evaluation_id":    evaluation_id,
    })

    # Update recommendation status to completed
    db.execute(text("""
        UPDATE recommendations SET status = 'completed' WHERE id = :id
    """), {"id": recommendation_id})

    # Create learning event candidate
    _create_learning_event(
        db=db,
        recommendation_id=recommendation_id,
        outcome_id=outcome_id,
        evaluation_id=evaluation_id,
        calibration_id=calibration_id,
        outcome_type=outcome_type,
        classification=classification,
        category=category,
        lessons_learned=lessons_learned,
        confidence_before=prior,
        confidence_after=posterior,
    )

    db.commit()

    return {
        "status":               "completed",
        "evaluation_id":        evaluation_id,
        "calibration_id":       calibration_id,
        "success_classification": classification,
        "confidence_before":    prior,
        "confidence_after":     posterior,
        "calibration_delta":    calibration_delta,
    }


def _create_learning_event(
    db: Session,
    recommendation_id: str,
    outcome_id: str,
    evaluation_id: str,
    calibration_id: str,
    outcome_type: str,
    classification: str,
    category: str,
    lessons_learned: Optional[str],
    confidence_before: float,
    confidence_after: float,
):
    """Extract a learning statement and create a pending learning event."""
    # Build learning statement
    if lessons_learned and len(lessons_learned) > 20:
        statement = lessons_learned
    else:
        direction = "improved" if confidence_after > confidence_before else "decreased"
        statement = (
            f"A {category.replace('_', ' ')} recommendation resulted in a {outcome_type.replace('_', ' ')} "
            f"outcome ({classification}). Platform confidence {direction} from "
            f"{confidence_before:.0%} to {confidence_after:.0%}."
        )

    applicable = f"When making {category.replace('_', ' ')} recommendations in similar contexts."

    provenance = {
        "recommendation_id":    recommendation_id,
        "outcome_id":           outcome_id,
        "evaluation_id":        evaluation_id,
        "calibration_id":       calibration_id,
        "outcome_type":         outcome_type,
        "classification":       classification,
        "confidence_before":    confidence_before,
        "confidence_after":     confidence_after,
        "generated_by":         "automatic_evaluation",
        "generated_at":         datetime.now(timezone.utc).isoformat(),
    }

    import json
    learning_event_id = str(uuid.uuid4())

    db.execute(text("""
        INSERT INTO learning_events
            (id, event_type, learning_statement, applicable_conditions,
             confidence_impact, significance,
             source_recommendation_id, source_outcome_id,
             source_evaluation_id, source_calibration_id,
             provenance_json, validation_status, tags)
        VALUES
            (:id, 'lesson_extracted', :statement, :applicable,
             :confidence_impact, :significance,
             :recommendation_id, :outcome_id,
             :evaluation_id, :calibration_id,
             CAST(:provenance AS jsonb), 'pending', :tags)
    """), {
        "id":                   learning_event_id,
        "statement":            statement,
        "applicable":           applicable,
        "confidence_impact":    round(confidence_after - confidence_before, 4),
        "significance":         "high" if abs(confidence_after - confidence_before) > 0.05 else "medium",
        "recommendation_id":    recommendation_id,
        "outcome_id":           outcome_id,
        "evaluation_id":        evaluation_id,
        "calibration_id":       calibration_id,
        "provenance":           json.dumps(provenance),
        "tags":                 [category, outcome_type, classification],
    })

    emit_learning_event_created(
        db=db,
        learning_event_id=learning_event_id,
        event_type="lesson_extracted",
        learning_statement=statement,
        source_recommendation_id=recommendation_id,
        confidence_impact=round(confidence_after - confidence_before, 4),
    )


# ─── Calibration ──────────────────────────────────────────────────────────

@router.get("/calibration/current")
async def get_current_calibration(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Get the latest confidence calibration per recommendation category."""
    rows = db.execute(text("""
        SELECT DISTINCT ON (recommendation_category)
            recommendation_category,
            posterior_confidence AS current_confidence,
            sample_size,
            success_count,
            failure_count,
            partial_count,
            created_at AS last_updated,
            update_reason
        FROM confidence_calibrations
        ORDER BY recommendation_category, created_at DESC
    """)).fetchall()

    return {"calibrations": [dict(r._mapping) for r in rows]}


@router.get("/calibration/{category}/history")
async def get_calibration_history(
    category: str,
    days: int = Query(default=90, le=365),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Get calibration history for a specific category."""
    rows = db.execute(text("""
        SELECT id, created_at, prior_confidence, posterior_confidence,
               sample_size, update_reason, calibration_delta,
               (posterior_confidence - prior_confidence) AS delta
        FROM confidence_calibrations
        WHERE recommendation_category = :category
          AND created_at > NOW() - INTERVAL ':days days'
        ORDER BY created_at ASC
    """), {"category": category, "days": days}).fetchall()

    return {
        "category": category,
        "history": [dict(r._mapping) for r in rows]
    }


# ─── Learning Events ──────────────────────────────────────────────────────

@router.get("/events")
async def list_learning_events(
    status: Optional[str] = "pending",
    limit: int = Query(default=20, le=100),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """List learning events, defaulting to pending (requiring validation)."""
    params = {"limit": limit}
    where = "1=1"
    if status:
        where += " AND validation_status = :status"
        params["status"] = status

    rows = db.execute(text(f"""
        SELECT id, occurred_at, event_type, learning_statement,
               applicable_conditions, confidence_impact, significance,
               source_recommendation_id, validation_status, tags
        FROM learning_events
        WHERE {where}
        ORDER BY occurred_at DESC
        LIMIT :limit
    """), params).fetchall()

    return {"learning_events": [dict(r._mapping) for r in rows]}


@router.patch("/events/{event_id}/validate")
async def validate_learning_event(
    event_id: str,
    body: LearningEventValidate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    Validate or reject a learning event.
    If validated: automatically creates an organisational memory entry.
    """
    event = db.execute(text("""
        SELECT * FROM learning_events WHERE id = :id
    """), {"id": event_id}).fetchone()

    if not event:
        raise HTTPException(status_code=404, detail="Learning event not found")

    user_id = str(current_user.id if hasattr(current_user, "id") else current_user.get("id") or current_user.get("sub", "unknown"))

    db.execute(text("""
        UPDATE learning_events
        SET validation_status = :status,
            validated_by = :validated_by,
            validated_at = NOW(),
            rejection_reason = :notes
        WHERE id = :id
    """), {
        "status":       body.validation_status,
        "validated_by": user_id,
        "notes":        body.notes,
        "id":           event_id,
    })

    memory_id = None
    if body.validation_status == "validated":
        memory_id = _create_memory_from_learning_event(db, event, user_id)

    db.commit()

    return {
        "event_id":         event_id,
        "validation_status": body.validation_status,
        "memory_created":   memory_id is not None,
        "memory_id":        memory_id,
    }


def _create_memory_from_learning_event(db: Session, event, validated_by: str) -> str:
    """Create an organisational memory entry from a validated learning event."""
    import json
    memory_id = str(uuid.uuid4())

    # Build tags from event
    tags = list(event.tags or []) + ["validated", "learning_engine"]

    db.execute(text("""
        INSERT INTO organisational_memory
            (id, memory_type, title, content,
             tags, source_type,
             source_learning_event_id, source_recommendation_id,
             contributed_by, validated_by, validated_at,
             confidence_score, validation_status, access_level)
        VALUES
            (:id, 'lesson', :title, :content,
             :tags, 'learning_engine',
             :learning_event_id, :recommendation_id,
             :contributed_by, :validated_by, NOW(),
             :confidence, 'validated', 'standard')
    """), {
        "id":                   memory_id,
        "title":                event.learning_statement[:200],
        "content":              (
            f"{event.learning_statement}\n\n"
            f"Applicable when: {event.applicable_conditions or 'Not specified'}\n\n"
            f"Confidence impact: {event.confidence_impact or 'Unknown'}"
        ),
        "tags":                 tags,
        "learning_event_id":    str(event.id),
        "recommendation_id":    str(event.source_recommendation_id) if event.source_recommendation_id else None,
        "contributed_by":       validated_by,
        "validated_by":         validated_by,
        "confidence":           0.75,  # Validated by human — higher base confidence
    })

    emit_knowledge_created(
        db=db,
        memory_id=memory_id,
        memory_type="lesson",
        title=event.learning_statement[:200],
        source_type="learning_engine",
        confidence_score=0.75,
        contributed_by=validated_by,
    )

    return memory_id


# ─── Organisational Memory ────────────────────────────────────────────────

@router.get("/memory/search")
async def search_memory(
    q: str,
    limit: int = Query(default=5, le=20),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    Full-text search of organisational memory.
    Used by Copilot before generating responses.
    """
    rows = db.execute(text("""
        SELECT id, memory_type, title, content, tags, entities,
               confidence_score, validation_status, retrieval_count,
               created_at, source_type,
               ts_rank(
                   to_tsvector('english', title || ' ' || content),
                   plainto_tsquery('english', :q)
               ) AS relevance_score
        FROM organisational_memory
        WHERE to_tsvector('english', title || ' ' || content)
              @@ plainto_tsquery('english', :q)
          AND validation_status = 'validated'
          AND access_level != 'restricted'
        ORDER BY relevance_score DESC, confidence_score DESC
        LIMIT :limit
    """), {"q": q, "limit": limit}).fetchall()

    # Update retrieval counts
    if rows:
        ids = [str(r.id) for r in rows]
        db.execute(text("""
            UPDATE organisational_memory
            SET retrieval_count = retrieval_count + 1,
                last_retrieved = NOW()
            WHERE id = ANY(CAST(:ids AS uuid[]))
        """), {"ids": ids})
        db.commit()

    return {"results": [dict(r._mapping) for r in rows], "query": q}


@router.get("/memory")
async def list_memory(
    memory_type: Optional[str] = None,
    validation_status: Optional[str] = "validated",
    limit: int = Query(default=20, le=100),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Browse organisational memory."""
    filters = ["access_level != 'restricted'"]
    params = {"limit": limit}

    if memory_type:
        filters.append("memory_type = :memory_type")
        params["memory_type"] = memory_type
    if validation_status:
        filters.append("validation_status = :validation_status")
        params["validation_status"] = validation_status

    where = " AND ".join(filters)

    rows = db.execute(text(f"""
        SELECT id, memory_type, title, content, tags, entities,
               confidence_score, validation_status, retrieval_count,
               copilot_citation_count, created_at, source_type
        FROM organisational_memory
        WHERE {where}
        ORDER BY created_at DESC
        LIMIT :limit
    """), params).fetchall()

    return {"memory_items": [dict(r._mapping) for r in rows]}


@router.post("/memory")
async def create_memory(
    body: MemoryCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Manually contribute a memory item (institutional knowledge)."""
    import json
    memory_id = str(uuid.uuid4())
    user_id = str(current_user.id if hasattr(current_user, "id") else current_user.get("id") or current_user.get("sub", "unknown"))

    db.execute(text("""
        INSERT INTO organisational_memory
            (id, memory_type, title, content, tags, entities,
             source_type, contributed_by, confidence_score,
             validation_status, access_level)
        VALUES
            (:id, :memory_type, :title, :content, :tags, :entities,
             'analyst', :contributed_by, :confidence,
             'pending', 'standard')
    """), {
        "id":           memory_id,
        "memory_type":  body.memory_type,
        "title":        body.title,
        "content":      body.content,
        "tags":         body.tags,
        "entities":     body.entities,
        "contributed_by": user_id,
        "confidence":   body.confidence_score,
    })
    db.commit()

    return {"memory_id": memory_id, "status": "created", "validation_status": "pending"}


# ─── Feedback ─────────────────────────────────────────────────────────────

@router.post("/feedback")
async def submit_feedback(
    body: FeedbackCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Submit feedback on any platform surface."""
    feedback_id = str(uuid.uuid4())
    user_id = str(current_user.id if hasattr(current_user, "id") else current_user.get("id") or current_user.get("sub", "unknown"))

    db.execute(text("""
        INSERT INTO feedback_records
            (id, submitted_by, feedback_type, target_id, target_type,
             rating, usefulness_score, accuracy_score, clarity_score,
             free_text, dashboard_context)
        VALUES
            (:id, :submitted_by, :feedback_type, :target_id, :target_type,
             :rating, :usefulness_score, :accuracy_score, :clarity_score,
             :free_text, :dashboard_context)
    """), {
        "id":               feedback_id,
        "submitted_by":     user_id,
        "feedback_type":    body.feedback_type,
        "target_id":        body.target_id,
        "target_type":      body.target_type,
        "rating":           body.rating,
        "usefulness_score": body.usefulness_score,
        "accuracy_score":   body.accuracy_score,
        "clarity_score":    body.clarity_score,
        "free_text":        body.free_text,
        "dashboard_context": body.dashboard_context,
    })

    emit_feedback_submitted(
        db=db,
        feedback_id=feedback_id,
        feedback_type=body.feedback_type,
        target_id=body.target_id or "",
        target_type=body.target_type or "",
        rating=body.rating,
        submitted_by=user_id,
    )

    db.commit()
    return {"feedback_id": feedback_id, "status": "recorded"}


# ─── Strategic Learning Dashboard ─────────────────────────────────────────

@router.get("/dashboard/summary")
async def get_learning_dashboard(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Strategic Learning Dashboard — executive view of platform learning."""

    # Recommendation stats
    rec_stats = db.execute(text("""
        SELECT
            COUNT(*) AS total,
            COUNT(*) FILTER (WHERE status = 'pending') AS pending,
            COUNT(*) FILTER (WHERE status = 'accepted') AS accepted,
            COUNT(*) FILTER (WHERE status = 'rejected') AS rejected,
            COUNT(*) FILTER (WHERE status = 'completed') AS completed
        FROM recommendations
        WHERE is_backfilled = FALSE
    """)).fetchone()

    # Success rate from evaluations
    eval_stats = db.execute(text("""
        SELECT
            COUNT(*) AS total_evaluated,
            AVG(success_score) AS avg_success_score,
            COUNT(*) FILTER (WHERE success_score >= 0.6) AS successes,
            COUNT(*) FILTER (WHERE success_score < 0.4) AS failures
        FROM outcome_evaluations
    """)).fetchone()

    success_rate = None
    if eval_stats.total_evaluated and eval_stats.total_evaluated > 0:
        success_rate = round(eval_stats.successes / eval_stats.total_evaluated * 100, 1)

    # Prediction accuracy (how well confidence predicted outcomes)
    accuracy = db.execute(text("""
        SELECT AVG(ABS(success_score - confidence_before)) AS avg_error
        FROM outcome_evaluations
    """)).scalar()
    prediction_accuracy = round((1 - (accuracy or 0.5)) * 100, 1)

    # Learning velocity (events per week)
    learning_velocity = db.execute(text("""
        SELECT COUNT(*) FROM learning_events
        WHERE occurred_at > NOW() - INTERVAL '7 days'
    """)).scalar()

    # Knowledge growth (memory items)
    knowledge_items = db.execute(text("""
        SELECT COUNT(*) FROM organisational_memory
        WHERE validation_status = 'validated'
    """)).scalar()

    pending_validations = db.execute(text("""
        SELECT COUNT(*) FROM learning_events
        WHERE validation_status = 'pending'
    """)).scalar()

    overdue_checkpoints = db.execute(text("""
        SELECT COUNT(*) FROM outcome_checkpoints
        WHERE status = 'pending' AND due_date < NOW()
    """)).scalar()

    # Current calibration per category
    calibrations = db.execute(text("""
        SELECT DISTINCT ON (recommendation_category)
            recommendation_category,
            posterior_confidence AS confidence,
            sample_size
        FROM confidence_calibrations
        ORDER BY recommendation_category, created_at DESC
    """)).fetchall()

    # Top performing categories (by success rate)
    category_performance = db.execute(text("""
        SELECT
            r.category,
            COUNT(oe.id) AS evaluated,
            AVG(oe.success_score) AS avg_success,
            COUNT(*) FILTER (WHERE oe.success_score >= 0.6) AS successes
        FROM outcome_evaluations oe
        JOIN recommendations r ON r.id = oe.recommendation_id
        GROUP BY r.category
        HAVING COUNT(oe.id) >= 1
        ORDER BY AVG(oe.success_score) DESC
    """)).fetchall()

    return {
        "recommendation_stats": dict(rec_stats._mapping) if rec_stats else {},
        "recommendation_success_rate": success_rate,
        "prediction_accuracy": prediction_accuracy,
        "learning_velocity_per_week": learning_velocity,
        "knowledge_items_validated": knowledge_items,
        "pending_learning_validations": pending_validations,
        "overdue_checkpoints": overdue_checkpoints,
        "calibrations_by_category": [dict(r._mapping) for r in calibrations],
        "category_performance": [dict(r._mapping) for r in category_performance],
    }


@router.get("/dashboard/confidence-trend")
async def get_confidence_trend(
    category: Optional[str] = None,
    days: int = Query(default=90, le=365),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Confidence calibration trend over time."""
    params = {"days": days}
    where = "created_at > NOW() - INTERVAL ':days days'"
    if category:
        where += " AND recommendation_category = :category"
        params["category"] = category

    rows = db.execute(text(f"""
        SELECT
            DATE_TRUNC('day', created_at) AS date,
            recommendation_category,
            AVG(posterior_confidence) AS avg_confidence,
            MAX(sample_size) AS sample_size
        FROM confidence_calibrations
        WHERE {where}
        GROUP BY DATE_TRUNC('day', created_at), recommendation_category
        ORDER BY date ASC
    """), params).fetchall()

    return {"trend": [dict(r._mapping) for r in rows]}
