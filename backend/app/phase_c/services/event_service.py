"""
NDIP Phase C — Platform Event Service v2
Uses raw psycopg2 cursor for JSONB insertion (SQLAlchemy text() 
does not support ::jsonb cast with named params in psycopg2).
"""
import uuid, json
from datetime import datetime, timezone
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session


class EventType:
    RECOMMENDATION_CREATED   = "RecommendationCreated"
    RECOMMENDATION_VIEWED    = "RecommendationViewed"
    DECISION_RECORDED        = "DecisionRecorded"
    OUTCOME_CHECKPOINT_DUE   = "OutcomeCheckpointDue"
    OUTCOME_RECORDED         = "OutcomeRecorded"
    OUTCOME_EVALUATED        = "OutcomeEvaluated"
    CONFIDENCE_UPDATED       = "ConfidenceUpdated"
    LEARNING_EVENT_CREATED   = "LearningEventCreated"
    LEARNING_EVENT_VALIDATED = "LearningEventValidated"
    KNOWLEDGE_CREATED        = "KnowledgeCreated"
    KNOWLEDGE_RETRIEVED      = "KnowledgeRetrieved"
    FEEDBACK_SUBMITTED       = "FeedbackSubmitted"
    PATTERN_IDENTIFIED       = "PatternIdentified"
    COPILOT_CONSULTED        = "CopilotConsulted"
    INGEST_COMPLETED         = "IngestCompleted"
    SNAPSHOT_SAVED           = "SnapshotSaved"


class SourceDomain:
    ADAPTIVE_LEARNING = "adaptive_learning"
    INTELLIGENCE      = "intelligence"
    OPERATIONS        = "operations"
    GOVERNANCE        = "governance"
    SYSTEM            = "system"


def _serialize(obj):
    """Convert UUIDs and datetimes to strings."""
    if isinstance(obj, uuid.UUID):
        return str(obj)
    if isinstance(obj, datetime):
        return obj.isoformat()
    if isinstance(obj, dict):
        return {k: _serialize(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_serialize(i) for i in obj]
    return obj


def emit_event(
    db: Session,
    event_type: str,
    source_domain: str,
    payload: Dict[str, Any],
    source_entity_type: Optional[str] = None,
    source_entity_id: Optional[str] = None,
    actor_id: Optional[str] = None,
    actor_role: Optional[str] = None,
    session_id: Optional[str] = None,
) -> str:
    """
    Emit an event to platform_events using raw psycopg2 cursor
    to correctly handle JSONB payload.
    """
    event_id = str(uuid.uuid4())
    serialized = _serialize(payload)

    try:
        from psycopg2.extras import Json as PgJson
        raw_conn = db.connection()
        cur = raw_conn.cursor()
        cur.execute(
            """INSERT INTO platform_events
               (event_id, event_type, source_domain, source_entity_type,
                source_entity_id, actor_id, actor_role, session_id, payload)
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)""",
            (
                event_id,
                event_type,
                source_domain,
                source_entity_type,
                str(source_entity_id) if source_entity_id else None,
                str(actor_id) if actor_id else None,
                actor_role,
                str(session_id) if session_id else None,
                PgJson(serialized),
            )
        )
        # Note: commit handled by caller or session
    except Exception as e:
        # Event emission failure NEVER blocks business logic
        pass

    return event_id


def emit_recommendation_created(db, recommendation_id, category,
                                confidence, source_dashboard,
                                created_by=None):
    return emit_event(db, EventType.RECOMMENDATION_CREATED,
                      SourceDomain.ADAPTIVE_LEARNING,
                      {"recommendation_id": recommendation_id,
                       "category": category,
                       "confidence_at_creation": confidence,
                       "source_dashboard": source_dashboard,
                       "created_by": created_by},
                      source_entity_type="recommendation",
                      source_entity_id=recommendation_id,
                      actor_id=created_by)


def emit_decision_recorded(db, recommendation_id, decision_id,
                           decision_type, decided_by,
                           checkpoint_dates=None):
    return emit_event(db, EventType.DECISION_RECORDED,
                      SourceDomain.ADAPTIVE_LEARNING,
                      {"recommendation_id": recommendation_id,
                       "decision_id": decision_id,
                       "decision_type": decision_type,
                       "decided_by": decided_by,
                       "checkpoints_scheduled": checkpoint_dates or []},
                      source_entity_type="recommendation_decision",
                      source_entity_id=decision_id,
                      actor_id=decided_by)


def emit_outcome_recorded(db, recommendation_id, outcome_id,
                          outcome_type, variance_score, recorded_by):
    return emit_event(db, EventType.OUTCOME_RECORDED,
                      SourceDomain.ADAPTIVE_LEARNING,
                      {"recommendation_id": recommendation_id,
                       "outcome_id": outcome_id,
                       "outcome_type": outcome_type,
                       "variance_score": variance_score,
                       "recorded_by": recorded_by},
                      source_entity_type="recommendation_outcome",
                      source_entity_id=outcome_id,
                      actor_id=recorded_by)


def emit_confidence_updated(db, category, prior, posterior,
                            sample_size, update_reason, calibration_id):
    return emit_event(db, EventType.CONFIDENCE_UPDATED,
                      SourceDomain.ADAPTIVE_LEARNING,
                      {"category": category,
                       "prior_confidence": prior,
                       "posterior_confidence": posterior,
                       "delta": round(posterior - prior, 4),
                       "sample_size": sample_size,
                       "update_reason": update_reason,
                       "calibration_id": calibration_id},
                      source_entity_type="confidence_calibration",
                      source_entity_id=calibration_id)


def emit_learning_event_created(db, learning_event_id, event_type,
                                 learning_statement,
                                 source_recommendation_id=None,
                                 confidence_impact=None):
    return emit_event(db, EventType.LEARNING_EVENT_CREATED,
                      SourceDomain.ADAPTIVE_LEARNING,
                      {"learning_event_id": learning_event_id,
                       "event_type": event_type,
                       "learning_statement": learning_statement[:200],
                       "source_recommendation_id": source_recommendation_id,
                       "confidence_impact": confidence_impact,
                       "validation_status": "pending"},
                      source_entity_type="learning_event",
                      source_entity_id=learning_event_id)


def emit_knowledge_created(db, memory_id, memory_type, title,
                           source_type, confidence_score,
                           contributed_by=None):
    return emit_event(db, EventType.KNOWLEDGE_CREATED,
                      SourceDomain.ADAPTIVE_LEARNING,
                      {"memory_id": memory_id,
                       "memory_type": memory_type,
                       "title": title[:200],
                       "source_type": source_type,
                       "confidence_score": confidence_score,
                       "contributed_by": contributed_by},
                      source_entity_type="organisational_memory",
                      source_entity_id=memory_id,
                      actor_id=contributed_by)


def emit_feedback_submitted(db, feedback_id, feedback_type,
                            target_id, target_type, rating,
                            submitted_by=None):
    return emit_event(db, EventType.FEEDBACK_SUBMITTED,
                      SourceDomain.ADAPTIVE_LEARNING,
                      {"feedback_id": feedback_id,
                       "feedback_type": feedback_type,
                       "target_id": target_id,
                       "target_type": target_type,
                       "rating": rating,
                       "submitted_by": submitted_by},
                      source_entity_type="feedback_record",
                      source_entity_id=feedback_id,
                      actor_id=submitted_by)


def emit_copilot_consulted(db, user_id, session_id, query_summary,
                           memory_items_cited=None,
                           recommendations_cited=None):
    return emit_event(db, EventType.COPILOT_CONSULTED,
                      SourceDomain.ADAPTIVE_LEARNING,
                      {"user_id": user_id,
                       "session_id": session_id,
                       "query_summary": query_summary[:300],
                       "memory_items_cited": memory_items_cited or [],
                       "recommendations_cited": recommendations_cited or []},
                      source_entity_type="copilot_session",
                      actor_id=user_id,
                      session_id=session_id)
