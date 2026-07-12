"""
NDIP Phase C — Platform Event Service
Centralized event emission for all domains.
Every important action emits an event here.
Events are stored in platform_events (append-only audit spine).
"""
import uuid
from datetime import datetime, timezone
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import text


# ─── Event Type Constants ──────────────────────────────────────────────────

class EventType:
    # Adaptive Learning domain
    RECOMMENDATION_CREATED      = "RecommendationCreated"
    RECOMMENDATION_VIEWED       = "RecommendationViewed"
    DECISION_RECORDED           = "DecisionRecorded"
    OUTCOME_CHECKPOINT_DUE      = "OutcomeCheckpointDue"
    OUTCOME_RECORDED            = "OutcomeRecorded"
    OUTCOME_EVALUATED           = "OutcomeEvaluated"
    CONFIDENCE_UPDATED          = "ConfidenceUpdated"
    LEARNING_EVENT_CREATED      = "LearningEventCreated"
    LEARNING_EVENT_VALIDATED    = "LearningEventValidated"
    KNOWLEDGE_CREATED           = "KnowledgeCreated"
    KNOWLEDGE_RETRIEVED         = "KnowledgeRetrieved"
    FEEDBACK_SUBMITTED          = "FeedbackSubmitted"
    PATTERN_IDENTIFIED          = "PatternIdentified"
    COPILOT_CONSULTED           = "CopilotConsulted"

    # Intelligence domain
    INGEST_COMPLETED            = "IngestCompleted"
    NARRATIVE_UPDATED           = "NarrativeTrendUpdated"
    SNAPSHOT_SAVED              = "SnapshotSaved"
    CACHE_WARMED                = "CacheWarmed"

    # Governance
    ACCESS_DENIED               = "AccessDenied"
    CONFIGURATION_CHANGED       = "ConfigurationChanged"
    USER_CREATED                = "UserCreated"
    ROLE_ASSIGNED               = "RoleAssigned"


class SourceDomain:
    ADAPTIVE_LEARNING   = "adaptive_learning"
    INTELLIGENCE        = "intelligence"
    OPERATIONS          = "operations"
    GOVERNANCE          = "governance"
    SYSTEM              = "system"


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
    Emit an event to the platform_events table.
    Returns the event_id UUID string.
    This is the single function all code uses to emit events.
    """
    event_id = str(uuid.uuid4())

    # Serialize any UUID values in payload
    serialized_payload = _serialize_payload(payload)

    db.execute(text("""
        INSERT INTO platform_events
            (event_id, event_type, source_domain, source_entity_type,
             source_entity_id, actor_id, actor_role, session_id, payload)
        VALUES
            (:event_id, :event_type, :source_domain, :source_entity_type,
             :source_entity_id, :actor_id, :actor_role, :session_id,
             :payload::jsonb)
    """), {
        "event_id":             event_id,
        "event_type":           event_type,
        "source_domain":        source_domain,
        "source_entity_type":   source_entity_type,
        "source_entity_id":     str(source_entity_id) if source_entity_id else None,
        "actor_id":             str(actor_id) if actor_id else None,
        "actor_role":           actor_role,
        "session_id":           str(session_id) if session_id else None,
        "payload":              _to_json_str(serialized_payload),
    })

    return event_id


def _serialize_payload(payload: Dict) -> Dict:
    """Convert UUIDs and datetimes to strings for JSON serialization."""
    import json

    def _convert(obj):
        if isinstance(obj, uuid.UUID):
            return str(obj)
        if isinstance(obj, datetime):
            return obj.isoformat()
        if isinstance(obj, dict):
            return {k: _convert(v) for k, v in obj.items()}
        if isinstance(obj, list):
            return [_convert(i) for i in obj]
        return obj

    return _convert(payload)


def _to_json_str(payload: Dict) -> str:
    import json
    return json.dumps(payload)


# ─── Convenience emitters ──────────────────────────────────────────────────

def emit_recommendation_created(db: Session, recommendation_id: str,
                                 category: str, confidence: float,
                                 source_dashboard: str, created_by: str = None) -> str:
    return emit_event(
        db=db,
        event_type=EventType.RECOMMENDATION_CREATED,
        source_domain=SourceDomain.ADAPTIVE_LEARNING,
        source_entity_type="recommendation",
        source_entity_id=recommendation_id,
        actor_id=created_by,
        payload={
            "recommendation_id": recommendation_id,
            "category": category,
            "confidence_at_creation": confidence,
            "source_dashboard": source_dashboard,
            "created_by": created_by,
        }
    )


def emit_decision_recorded(db: Session, recommendation_id: str,
                            decision_id: str, decision_type: str,
                            decided_by: str, checkpoint_dates: list = None) -> str:
    return emit_event(
        db=db,
        event_type=EventType.DECISION_RECORDED,
        source_domain=SourceDomain.ADAPTIVE_LEARNING,
        source_entity_type="recommendation_decision",
        source_entity_id=decision_id,
        actor_id=decided_by,
        payload={
            "recommendation_id": recommendation_id,
            "decision_id": decision_id,
            "decision_type": decision_type,
            "decided_by": decided_by,
            "checkpoints_scheduled": checkpoint_dates or [],
        }
    )


def emit_outcome_recorded(db: Session, recommendation_id: str,
                           outcome_id: str, outcome_type: str,
                           variance_score: float, recorded_by: str) -> str:
    return emit_event(
        db=db,
        event_type=EventType.OUTCOME_RECORDED,
        source_domain=SourceDomain.ADAPTIVE_LEARNING,
        source_entity_type="recommendation_outcome",
        source_entity_id=outcome_id,
        actor_id=recorded_by,
        payload={
            "recommendation_id": recommendation_id,
            "outcome_id": outcome_id,
            "outcome_type": outcome_type,
            "variance_score": variance_score,
            "recorded_by": recorded_by,
        }
    )


def emit_confidence_updated(db: Session, category: str, prior: float,
                             posterior: float, sample_size: int,
                             update_reason: str, calibration_id: str) -> str:
    return emit_event(
        db=db,
        event_type=EventType.CONFIDENCE_UPDATED,
        source_domain=SourceDomain.ADAPTIVE_LEARNING,
        source_entity_type="confidence_calibration",
        source_entity_id=calibration_id,
        payload={
            "category": category,
            "prior_confidence": prior,
            "posterior_confidence": posterior,
            "delta": round(posterior - prior, 4),
            "sample_size": sample_size,
            "update_reason": update_reason,
            "calibration_id": calibration_id,
        }
    )


def emit_learning_event_created(db: Session, learning_event_id: str,
                                  event_type: str, learning_statement: str,
                                  source_recommendation_id: str = None,
                                  confidence_impact: float = None) -> str:
    return emit_event(
        db=db,
        event_type=EventType.LEARNING_EVENT_CREATED,
        source_domain=SourceDomain.ADAPTIVE_LEARNING,
        source_entity_type="learning_event",
        source_entity_id=learning_event_id,
        payload={
            "learning_event_id": learning_event_id,
            "event_type": event_type,
            "learning_statement": learning_statement[:200],
            "source_recommendation_id": source_recommendation_id,
            "confidence_impact": confidence_impact,
            "validation_status": "pending",
        }
    )


def emit_knowledge_created(db: Session, memory_id: str, memory_type: str,
                            title: str, source_type: str,
                            confidence_score: float, contributed_by: str = None) -> str:
    return emit_event(
        db=db,
        event_type=EventType.KNOWLEDGE_CREATED,
        source_domain=SourceDomain.ADAPTIVE_LEARNING,
        source_entity_type="organisational_memory",
        source_entity_id=memory_id,
        actor_id=contributed_by,
        payload={
            "memory_id": memory_id,
            "memory_type": memory_type,
            "title": title[:200],
            "source_type": source_type,
            "confidence_score": confidence_score,
            "contributed_by": contributed_by,
        }
    )


def emit_copilot_consulted(db: Session, user_id: str, session_id: str,
                            query_summary: str, memory_items_cited: list = None,
                            recommendations_cited: list = None) -> str:
    return emit_event(
        db=db,
        event_type=EventType.COPILOT_CONSULTED,
        source_domain=SourceDomain.ADAPTIVE_LEARNING,
        source_entity_type="copilot_session",
        actor_id=user_id,
        session_id=session_id,
        payload={
            "user_id": user_id,
            "session_id": session_id,
            "query_summary": query_summary[:300],
            "memory_items_cited": memory_items_cited or [],
            "recommendations_cited": recommendations_cited or [],
        }
    )


def emit_feedback_submitted(db: Session, feedback_id: str, feedback_type: str,
                             target_id: str, target_type: str,
                             rating: str, submitted_by: str = None) -> str:
    return emit_event(
        db=db,
        event_type=EventType.FEEDBACK_SUBMITTED,
        source_domain=SourceDomain.ADAPTIVE_LEARNING,
        source_entity_type="feedback_record",
        source_entity_id=feedback_id,
        actor_id=submitted_by,
        payload={
            "feedback_id": feedback_id,
            "feedback_type": feedback_type,
            "target_id": target_id,
            "target_type": target_type,
            "rating": rating,
            "submitted_by": submitted_by,
        }
    )
