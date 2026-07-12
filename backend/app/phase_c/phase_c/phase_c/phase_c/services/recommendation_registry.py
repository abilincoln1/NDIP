"""
NDIP Phase C — Recommendation Registry Service
Automatically registers every recommendation generated anywhere in NDIP.
Called by the Copilot router after every response.
Users never see this — registration is invisible.
"""
import re
import uuid
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import text

from app.phase_c.services.event_service import emit_recommendation_created


# ─── Recommendation Categories ────────────────────────────────────────────

CATEGORIES = {
    "stakeholder_engage":   ["engage", "stakeholder", "contact", "reach out", "convene", "meet with"],
    "narrative_monitor":    ["monitor", "track", "watch", "observe", "follow"],
    "risk_escalate":        ["risk", "threat", "danger", "concern", "warning", "escalat"],
    "opportunity_pursue":   ["opportunity", "leverage", "capitalise", "amplify", "pursue"],
    "decision_urgent":      ["urgent", "immediate", "critical", "time-sensitive", "act now", "requires action"],
    "strategic_review":     ["review", "assess", "evaluate", "consider", "examine", "strategic"],
}

RECOMMENDATION_TRIGGERS = [
    r'\b(?:recommend|suggest|advise|should consider|would benefit|action required|'
    r'leadership (?:can|should|must)|consider engaging|opportunity to|'
    r'we (?:recommend|suggest|advise))\b',
]

TRIGGER_PATTERN = re.compile(
    '|'.join(RECOMMENDATION_TRIGGERS),
    re.IGNORECASE
)


def _classify_category(text: str) -> str:
    """Determine the recommendation category from text content."""
    text_lower = text.lower()
    for category, keywords in CATEGORIES.items():
        if any(kw in text_lower for kw in keywords):
            return category
    return "general"


def _extract_recommendation_sentences(response_text: str) -> List[str]:
    """
    Extract sentences that contain recommendation-class statements.
    Returns list of sentence strings.
    """
    # Split on sentence boundaries
    sentences = re.split(r'(?<=[.!?])\s+', response_text)
    recommendations = []

    for sentence in sentences:
        if TRIGGER_PATTERN.search(sentence) and len(sentence) > 30:
            recommendations.append(sentence.strip())

    return recommendations


def _build_title(text: str, category: str) -> str:
    """Generate a concise title from the recommendation text."""
    # Take first 80 chars, clean up
    title = text[:80].strip()
    if len(text) > 80:
        title += "..."
    # Capitalise first letter
    return title[:1].upper() + title[1:] if title else f"Recommendation ({category})"


def register_recommendation_from_copilot(
    db: Session,
    response_text: str,
    user_id: Optional[str],
    context_snapshot: Dict[str, Any],
    source_dashboard: str = "copilot",
    confidence: float = 0.65,
) -> List[str]:
    """
    Extract and register all recommendation-class statements from a Copilot response.
    Returns list of registered recommendation IDs.
    Called automatically by the Copilot router — invisible to users.
    """
    sentences = _extract_recommendation_sentences(response_text)
    if not sentences:
        return []

    registered_ids = []

    for sentence in sentences[:3]:  # Cap at 3 per response to avoid noise
        rec_id = str(uuid.uuid4())
        category = _classify_category(sentence)
        title = _build_title(sentence, category)

        # Extract any entities mentioned (simple capitalised noun extraction)
        entities = _extract_entities_simple(sentence)
        narratives = _extract_narratives_simple(sentence, context_snapshot)

        db.execute(text("""
            INSERT INTO recommendations
                (id, category, recommendation_type, source_dashboard,
                 title, recommendation_text, evidence_snapshot,
                 supporting_entities, supporting_narratives,
                 context_snapshot, confidence_at_creation,
                 model_version, expected_outcome, expected_horizon_days,
                 status, created_by, is_backfilled, tags)
            VALUES
                (:id, :category, :recommendation_type, :source_dashboard,
                 :title, :recommendation_text, :evidence_snapshot::jsonb,
                 :supporting_entities, :supporting_narratives,
                 :context_snapshot::jsonb, :confidence_at_creation,
                 :model_version, :expected_outcome, :expected_horizon_days,
                 :status, :created_by, FALSE, :tags)
        """), {
            "id":                       rec_id,
            "category":                 category,
            "recommendation_type":      "advisory",
            "source_dashboard":         source_dashboard,
            "title":                    title,
            "recommendation_text":      sentence,
            "evidence_snapshot":        "[]",
            "supporting_entities":      entities,
            "supporting_narratives":    narratives,
            "context_snapshot":         _safe_json(context_snapshot),
            "confidence_at_creation":   confidence,
            "model_version":            "v1.0",
            "expected_outcome":         "Positive impact on diaspora engagement",
            "expected_horizon_days":    90,
            "status":                   "pending",
            "created_by":               user_id,
            "tags":                     [category, source_dashboard],
        })

        # Emit event
        try:
            event_id = emit_recommendation_created(
                db=db,
                recommendation_id=rec_id,
                category=category,
                confidence=confidence,
                source_dashboard=source_dashboard,
                created_by=user_id,
            )
            # Link event back to recommendation
            db.execute(text("""
                UPDATE recommendations
                SET context_snapshot = context_snapshot || '{"platform_event_id": "' || :event_id || '"}'::jsonb
                WHERE id = :rec_id
            """), {"event_id": event_id, "rec_id": rec_id})
        except Exception:
            pass  # Event emission failure never blocks recommendation registration

        registered_ids.append(rec_id)

    db.commit()
    return registered_ids


def register_recommendation_manual(
    db: Session,
    title: str,
    recommendation_text: str,
    category: str,
    source_dashboard: str,
    user_id: Optional[str],
    expected_outcome: str = "",
    expected_horizon_days: int = 90,
    confidence: float = 0.65,
    evidence_snapshot: list = None,
    supporting_entities: list = None,
    context_snapshot: dict = None,
    tags: list = None,
) -> str:
    """
    Register a recommendation manually (e.g. from dashboard alerts).
    Returns the recommendation ID.
    """
    rec_id = str(uuid.uuid4())

    db.execute(text("""
        INSERT INTO recommendations
            (id, category, recommendation_type, source_dashboard,
             title, recommendation_text, evidence_snapshot,
             supporting_entities, context_snapshot,
             confidence_at_creation, model_version,
             expected_outcome, expected_horizon_days,
             status, created_by, is_backfilled, tags)
        VALUES
            (:id, :category, 'advisory', :source_dashboard,
             :title, :recommendation_text, :evidence_snapshot::jsonb,
             :supporting_entities, :context_snapshot::jsonb,
             :confidence, 'v1.0',
             :expected_outcome, :expected_horizon_days,
             'pending', :created_by, FALSE, :tags)
    """), {
        "id":                   rec_id,
        "category":             category,
        "source_dashboard":     source_dashboard,
        "title":                title,
        "recommendation_text":  recommendation_text,
        "evidence_snapshot":    _safe_json(evidence_snapshot or []),
        "supporting_entities":  supporting_entities or [],
        "context_snapshot":     _safe_json(context_snapshot or {}),
        "confidence":           confidence,
        "expected_outcome":     expected_outcome,
        "expected_horizon_days": expected_horizon_days,
        "created_by":           user_id,
        "tags":                 tags or [category],
    })

    emit_recommendation_created(
        db=db,
        recommendation_id=rec_id,
        category=category,
        confidence=confidence,
        source_dashboard=source_dashboard,
        created_by=user_id,
    )

    db.commit()
    return rec_id


def backfill_historical_recommendations(db: Session) -> int:
    """
    One-time import of historical recommendations from daily_intelligence_snapshots.
    Extracts Copilot recommendations from snapshot data where available.
    Returns count of records created.
    """
    count = 0

    try:
        rows = db.execute(text("""
            SELECT snapshot_date, narrative_summary, opportunities_summary,
                   engagement_index, sentiment_score
            FROM daily_intelligence_snapshots
            ORDER BY snapshot_date ASC
        """)).fetchall()
    except Exception:
        return 0  # Table may not exist yet

    for row in rows:
        # Extract any recommendation-class text from summaries
        texts_to_scan = []
        if row.narrative_summary:
            texts_to_scan.append(str(row.narrative_summary))
        if row.opportunities_summary:
            texts_to_scan.append(str(row.opportunities_summary))

        for text_content in texts_to_scan:
            sentences = _extract_recommendation_sentences(text_content)
            for sentence in sentences[:2]:
                rec_id = str(uuid.uuid4())
                category = _classify_category(sentence)
                title = _build_title(sentence, category)

                try:
                    db.execute(text("""
                        INSERT INTO recommendations
                            (id, category, recommendation_type, source_dashboard,
                             title, recommendation_text, confidence_at_creation,
                             model_version, expected_outcome, expected_horizon_days,
                             status, is_backfilled, backfill_source,
                             original_timestamp, tags)
                        VALUES
                            (:id, :category, 'advisory', 'daily_snapshot',
                             :title, :sentence, 0.60,
                             'v1.0', '', 90,
                             'completed', TRUE, 'daily_intelligence_snapshots',
                             :snapshot_date, :tags)
                        ON CONFLICT DO NOTHING
                    """), {
                        "id":           rec_id,
                        "category":     category,
                        "title":        title,
                        "sentence":     sentence,
                        "snapshot_date": row.snapshot_date,
                        "tags":         [category, "backfilled"],
                    })
                    count += 1
                except Exception:
                    db.rollback()
                    continue

    db.commit()
    return count


def _extract_entities_simple(text: str) -> List[str]:
    """Simple capitalised noun extraction for entity tagging."""
    # Match sequences of capitalised words (crude but functional without spaCy)
    pattern = re.compile(r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b')
    candidates = pattern.findall(text)
    # Filter common words
    stopwords = {'The', 'This', 'That', 'These', 'Those', 'Leadership', 'Nigeria'}
    return list(set(c for c in candidates if c not in stopwords))[:5]


def _extract_narratives_simple(text: str, context: Dict) -> List[str]:
    """Extract narrative references from text and context."""
    narratives = []
    if context and isinstance(context, dict):
        if 'narratives' in context:
            for n in context.get('narratives', [])[:3]:
                if isinstance(n, dict) and 'name' in n:
                    narratives.append(n['name'])
                elif isinstance(n, str):
                    narratives.append(n)
    return narratives


def _safe_json(obj: Any) -> str:
    """Safely serialize to JSON string."""
    import json
    try:
        return json.dumps(obj)
    except Exception:
        return "[]" if isinstance(obj, list) else "{}"
