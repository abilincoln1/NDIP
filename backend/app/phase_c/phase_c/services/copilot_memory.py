"""
NDIP Phase C — Copilot Memory Integration
Enriches every Copilot query with relevant organisational memory.
The existing Copilot router calls get_memory_context() before
sending the request to Anthropic.

Integration: add to app/routers/copilot.py before the Anthropic API call.
"""
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import Optional, List, Dict, Any
import re


def get_memory_context(db: Session, query: str, max_items: int = 5) -> str:
    """
    Search organisational memory for content relevant to the user's query.
    Returns a formatted string to inject into the Copilot system prompt.
    Returns empty string if no relevant memory exists.
    """
    if not query or len(query.strip()) < 10:
        return ""

    try:
        # Search validated memory using full-text search
        rows = db.execute(text("""
            SELECT id, memory_type, title, content, confidence_score,
                   tags, entities, created_at,
                   ts_rank(
                       to_tsvector('english', title || ' ' || content),
                       plainto_tsquery('english', :q)
                   ) AS relevance_score
            FROM organisational_memory
            WHERE to_tsvector('english', title || ' ' || content)
                  @@ plainto_tsquery('english', :q)
              AND validation_status = 'validated'
              AND access_level != 'restricted'
              AND confidence_score >= 0.4
            ORDER BY relevance_score DESC, confidence_score DESC
            LIMIT :limit
        """), {"q": query, "limit": max_items}).fetchall()

        if not rows:
            return ""

        # Update retrieval stats
        ids = [str(r.id) for r in rows]
        db.execute(text("""
            UPDATE organisational_memory
            SET retrieval_count = retrieval_count + 1,
                last_retrieved = NOW(),
                copilot_citation_count = copilot_citation_count + 1
            WHERE id = ANY(CAST(:ids AS uuid[]))
        """), {"ids": ids})
        db.commit()

        # Format memory context for injection
        context_parts = [
            "=== ORGANISATIONAL MEMORY ===",
            "The following lessons and decisions from this organisation's history "
            "are relevant to the current query. Reference them naturally when appropriate:\n"
        ]

        for i, row in enumerate(rows, 1):
            confidence_label = (
                "High confidence" if row.confidence_score >= 0.75
                else "Medium confidence" if row.confidence_score >= 0.5
                else "Lower confidence"
            )
            context_parts.append(
                f"[Memory {i}] {row.title}\n"
                f"Type: {row.memory_type} | {confidence_label}\n"
                f"{row.content[:500]}{'...' if len(row.content) > 500 else ''}\n"
            )

        context_parts.append("=== END ORGANISATIONAL MEMORY ===\n")

        return "\n".join(context_parts)

    except Exception as e:
        # Memory retrieval failure must never break the Copilot
        return ""


def get_historical_recommendations_context(
    db: Session,
    query: str,
    category: Optional[str] = None,
    max_items: int = 3
) -> str:
    """
    Search historical recommendations relevant to the current query.
    Returns context about what was recommended before and what happened.
    """
    if not query or len(query.strip()) < 10:
        return ""

    try:
        # Search completed recommendations with outcomes
        params = {
            "q": f"%{query[:50]}%",
            "limit": max_items
        }

        category_filter = ""
        if category:
            category_filter = "AND r.category = :category"
            params["category"] = category

        rows = db.execute(text(f"""
            SELECT
                r.title,
                r.recommendation_text,
                r.category,
                r.confidence_at_creation,
                r.created_at,
                ro.outcome_type,
                ro.actual_outcome,
                ro.lessons_learned,
                oe.success_classification,
                oe.confidence_after
            FROM recommendations r
            LEFT JOIN recommendation_outcomes ro ON ro.recommendation_id = r.id
            LEFT JOIN outcome_evaluations oe ON oe.recommendation_id = r.id
            WHERE r.status IN ('completed', 'evaluating')
              {category_filter}
            ORDER BY r.created_at DESC
            LIMIT :limit
        """), params).fetchall()

        if not rows:
            return ""

        context_parts = [
            "=== HISTORICAL RECOMMENDATIONS ===",
            "Previous recommendations from this organisation's experience:\n"
        ]

        for row in rows:
            outcome_text = ""
            if row.outcome_type:
                outcome_text = f"\nOutcome: {row.outcome_type}"
                if row.lessons_learned:
                    outcome_text += f"\nLesson: {row.lessons_learned[:200]}"

            context_parts.append(
                f"Previous recommendation ({row.category}):\n"
                f'"{row.recommendation_text[:300]}"\n'
                f"Initial confidence: {row.confidence_at_creation:.0%}"
                f"{outcome_text}\n"
            )

        context_parts.append("=== END HISTORICAL RECOMMENDATIONS ===\n")

        return "\n".join(context_parts)

    except Exception:
        return ""


def build_memory_aware_system_prompt(
    db: Session,
    base_system_prompt: str,
    user_query: str,
    page_data: Optional[Dict] = None,
) -> tuple[str, List[str]]:
    """
    Build a memory-enriched system prompt for the Copilot.
    Returns (enriched_prompt, list_of_memory_ids_cited).

    Call this instead of using base_system_prompt directly.
    """
    memory_context = get_memory_context(db, user_query)
    historical_context = get_historical_recommendations_context(db, user_query)

    cited_ids = []

    enriched_prompt = base_system_prompt

    if memory_context:
        enriched_prompt += f"\n\n{memory_context}"

    if historical_context:
        enriched_prompt += f"\n\n{historical_context}"

    if memory_context or historical_context:
        enriched_prompt += """

IMPORTANT INSTRUCTIONS FOR USING ORGANISATIONAL MEMORY:
- When organisational memory is relevant, reference it naturally: "Based on our previous experience..." or "In a similar situation..."
- Always state the confidence level when referencing historical recommendations
- If a previous recommendation failed, acknowledge this and explain why your current advice may differ
- Never simply repeat historical recommendations — use them as context to improve current advice
- If you reference organisational memory, say so explicitly so the user knows the advice is grounded in organisational history
"""

    return enriched_prompt, cited_ids
