"""
NDIP V8 — AI Copilot API (Phase 1 Hardened)
Implements:

  # Phase C: Enrich with organisational memory
  if PHASE_C_ENABLED:
      try:
          import uuid as _uuid
          _session_id = str(_uuid.uuid4())
          _user_query = message if isinstance(message, str) else str(message)[:500]
          _user_id = str(current_user.id) if hasattr(current_user, 'id') else str(current_user.get('id', 'unknown'))
          # Search memory and build enriched context
          _mem_prompt, _mem_ids = build_memory_aware_system_prompt(
              db=db,
              base_system_prompt=system_prompt if 'system_prompt' in dir() else '',
              user_query=_user_query,
          )
          if _mem_prompt and 'system_prompt' in dir():
              system_prompt = _mem_prompt
          # Emit consultation event
          emit_copilot_consulted(
              db=db,
              user_id=_user_id,
              session_id=_session_id,
              query_summary=_user_query[:300],
              memory_items_cited=_mem_ids,
          )
          db.commit()
      except Exception as _pc_mem_err:
          pass  # Memory enrichment failure never blocks copilot

  EB-002: Async Anthropic API call (httpx.AsyncClient — no more blocking workers)
  EB-007: Role derived from authenticated user, not hardcoded
  EB-014: Context Builder — injects live metrics, delta, evidence into LLM context
  EB-015: Conversation history (last 5 turns stored in Redis)
  EB-020: Rate limiting (20 requests per user per hour)
"""
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
import httpx
import json
import hashlib
from datetime import datetime, timezone, timedelta, date

from app.db.database import get_db
from app.core.security import get_current_user
from app.core.config import get_settings

# PHASE_C_MEMORY — Adaptive Learning integration
try:
    from app.phase_c.services.copilot_memory import build_memory_aware_system_prompt
    from app.phase_c.services.recommendation_registry import register_recommendation_from_copilot
    from app.phase_c.services.event_service import emit_copilot_consulted
    PHASE_C_ENABLED = True
    print('[Phase C] Memory-aware Copilot: enabled')
except Exception as _pc_err:
    PHASE_C_ENABLED = False
    print(f'[Phase C] Memory-aware Copilot: disabled ({_pc_err})')


# Phase C - Adaptive Learning integration
try:
    from app.phase_c.services.recommendation_registry import register_recommendation_from_copilot
    from app.phase_c.services.copilot_memory import build_memory_aware_system_prompt
    PHASE_C_ENABLED = True
except ImportError:
    PHASE_C_ENABLED = False


router = APIRouter(prefix="/copilot", tags=["copilot"])
settings = get_settings()

# ── Page context registry ─────────────────────────────────────────────────
PAGE_CONTEXTS = {
    "/leadership-pack": {
        "name": "Leadership Pack",
        "description": "The daily executive intelligence briefing. Shows narrative share of voice, strategic risks, opportunities, key stakeholders, watchlist items, and a confidence statement.",
        "key_metrics": ["share_of_voice", "momentum", "sentiment", "confidence_label", "risk_level", "opportunity_score"],
        "who_uses": "Senior executives, Director General, Board members",
        "primary_purpose": "Situational awareness and daily priority-setting",
    },
    "/situation-room": {
        "name": "Situation Room",
        "description": "Deep real-time intelligence view. Shows narrative momentum acceleration, emerging topics, sentiment shifts, and early warning signals.",
        "key_metrics": ["momentum", "sentiment_shift", "emerging_topics", "share_of_voice"],
        "who_uses": "Senior analysts, Communications leads",
        "primary_purpose": "Crisis monitoring and narrative trend tracking",
    },
    "/national-pulse": {
        "name": "National Pulse Executive",
        "description": "Platform-wide sentiment and engagement health check. Shows the Engagement Index trend and national mood barometer.",
        "key_metrics": ["engagement_index", "sentiment_score", "growth_rate"],
        "who_uses": "National coordinators, Campaign directors",
        "primary_purpose": "Communications strategy calibration",
    },
    "/strategic-outcome": {
        "name": "SOI Dashboard",
        "description": "Strategic Opportunity Intelligence. Detects opportunities in policy and diaspora landscape, shows alignment scores, readiness scores, and opportunity pipeline.",
        "key_metrics": ["opportunity_score", "alignment_score", "readiness_score", "pipeline_status"],
        "who_uses": "Campaign directors, Strategy teams",
        "primary_purpose": "Opportunity identification and stakeholder prioritisation",
    },
    "/election-centre": {
        "name": "Election Intelligence",
        "description": "Real-time monitoring of election-relevant discourse, key dates, political dynamics, days-to-election countdown, and electoral risk factors.",
        "key_metrics": ["days_to_election", "electoral_risk", "swing_narratives"],
        "who_uses": "Election coordinators, Campaign directors",
        "primary_purpose": "Electoral strategy and risk monitoring",
    },
    "/watchlist": {
        "name": "Leadership Watchlist",
        "description": "Prioritised alert list of items requiring leadership attention. Items are tiered: Critical (act today), High (act this week), Monitor (weekly review).",
        "key_metrics": ["priority_tier", "momentum", "sentiment"],
        "who_uses": "All executive users",
        "primary_purpose": "Daily action prioritisation",
    },
    "/gnei": {
        "name": "GNEI",
        "description": "Global Nigerian Engagement Index. Composite metric measuring intensity and sentiment of diaspora-related discourse globally.",
        "key_metrics": ["gnei_score", "diaspora_sentiment", "engagement_trend"],
        "who_uses": "Diaspora coordinators, Campaign directors",
        "primary_purpose": "Diaspora intelligence and engagement monitoring",
    },
    "/": {
        "name": "Overview Dashboard",
        "description": "Platform analytics overview. Shows participant counts, engagement metrics, and platform-wide statistics.",
        "key_metrics": ["participant_count", "engagement_index", "activity_level"],
        "who_uses": "All users",
        "primary_purpose": "Platform-wide activity overview",
    },
}

ROLE_CONTEXTS = {
    "executive": "You are speaking to a senior executive (Director General, Minister, or Board Member). Use plain, confident language. Lead with what matters and what action is needed. Never use technical jargon. Keep responses to 3–5 sentences maximum unless the user asks for more detail.",
    "analyst": "You are speaking to a professional intelligence analyst. Use precise language. Include metric values, data sources, and caveats. Explain methodology when relevant.",
    "admin": "You are speaking to a platform administrator. You can reference technical components. Provide diagnostic precision. Focus on system health and operational concerns.",
    "campaign_director": "You are speaking to a Campaign Director. Focus on electoral intelligence, narrative strategy, stakeholder engagement priorities, and opportunity scoring.",
    "diaspora": "You are speaking to a Diaspora Coordinator. Focus on GNEI, diaspora sentiment, community signals, and diaspora engagement opportunities.",
}

GLOSSARY = {
    "share_of_voice": "The percentage of total monitored conversations that a specific topic represents.",
    "momentum": "The rate of change in discourse volume compared to the previous equivalent period.",
    "sentiment_score": "Emotional tone of discourse. Ranges from -1 (very negative) to +1 (very positive).",
    "engagement_index": "A composite score (0–5+) reflecting overall platform intelligence intensity.",
    "influence_score": "How prominently a stakeholder appears in monitored discourse.",
    "opportunity_score": "How strong the discourse signal is for a strategic opportunity.",
    "confidence_label": "High / Medium / Low reliability assessment of intelligence quality.",
    "gnei": "Global Nigerian Engagement Index. Measures diaspora discourse intensity and sentiment.",
    "watchlist": "Prioritised intelligence items: Critical (act today), High (act this week), Monitor (weekly review).",
    "materialised_intelligence": "Pre-computed intelligence stored in the database after each ingest run.",
    "narrative": "A recurring theme in public discourse. NDIP monitors 11 strategic narratives.",
    "alignment_score": "How closely a stakeholder's activities align with a specific opportunity.",
    "readiness_score": "How ready conditions are for an opportunity to be acted on.",
    "composite_index": "Overall stakeholder ranking combining influence, momentum, and opportunity alignment.",
    "ingest": "The automated process of fetching new content from monitored sources for analysis.",
}

SYSTEM_PROMPT = """You are the NDIP AI Copilot — an intelligent assistant embedded in the National & Diaspora Intelligence Platform built by RTIFN.

YOUR ROLE:
- Help users understand what they are looking at
- Explain metrics and scores in plain English
- Recommend next best actions based on current intelligence
- Answer "why is this happening?" and "what should I do?" questions
- When you have data deltas (today vs yesterday), use them precisely

CRITICAL RULES:
1. Never mention technical internals: no table names, no Python functions, no API routes
2. Always qualify uncertain intelligence using confidence labels
3. Never make political judgements — describe what data shows
4. Be honest about data gaps — do NOT fabricate comparisons you cannot support with data
5. If yesterday's snapshot is provided in context, use it. If not, say so clearly.
6. Adapt language to the user's role (set in context below)

PLATFORM GLOSSARY:
{glossary}

CURRENT PAGE:
{page_context}

USER ROLE:
{role_context}

CURRENT PLATFORM DATA:
{data_summary}

{delta_section}

{evidence_section}
"""


# ── Context Builder ────────────────────────────────────────────────────────

def _build_data_summary(data_context: Optional[dict]) -> str:
    if not data_context:
        return "No live data passed from the current page. Respond based on page context above."
    lines = []
    if "narratives" in data_context:
        narratives = data_context.get("narratives", [])
        if narratives:
            top = narratives[0]
            lines.append(f"Top narrative: {top.get('narrative','?')} at {top.get('share_of_voice',0):.1f}% share of voice, {top.get('sentiment_label','neutral')} sentiment, {top.get('momentum_direction','stable')} momentum.")
    if "engagement_index" in data_context:
        lines.append(f"Engagement Index: {data_context['engagement_index']}.")
    if "sentiment_score" in data_context:
        lines.append(f"Overall sentiment: {data_context['sentiment_score']}.")
    if "watchlist_critical_count" in data_context:
        c = data_context.get("watchlist_critical_count", 0)
        h = data_context.get("watchlist_high_count", 0)
        lines.append(f"Watchlist: {c} Critical, {h} High items.")
    if "confidence" in data_context:
        lines.append(f"Intelligence confidence: {data_context['confidence']}.")
    if "gnei_score" in data_context:
        lines.append(f"GNEI: {data_context['gnei_score']}.")
    if "top_opportunities" in data_context:
        opps = data_context.get("top_opportunities", [])
        if opps:
            lines.append(f"Top opportunity: {opps[0].get('title','?')} (score: {opps[0].get('opportunity_score','?')}).")
    return " ".join(lines) if lines else "Page loaded with partial data context."


def _build_delta_section(db: Session) -> str:
    """Query yesterday's snapshot and build a delta string for the LLM."""
    try:
        from sqlalchemy import text
        today = date.today()
        yesterday = today - timedelta(days=1)
        result = db.execute(text("""
            SELECT narrative_data, engagement_index, sentiment_score,
                   watchlist_critical_count, watchlist_high_count,
                   top_stakeholders, snapshot_date
            FROM daily_intelligence_snapshots
            WHERE snapshot_date = :yesterday
            ORDER BY created_at DESC LIMIT 1
        """), {"yesterday": yesterday}).fetchone()

        if not result:
            return "HISTORICAL CONTEXT: No snapshot exists for yesterday. You cannot make today-vs-yesterday comparisons from data — say so clearly if asked."

        delta_lines = [f"YESTERDAY'S SNAPSHOT ({result.snapshot_date}):"]
        if result.engagement_index:
            delta_lines.append(f"  Yesterday's Engagement Index: {result.engagement_index:.2f}")
        if result.sentiment_score:
            delta_lines.append(f"  Yesterday's sentiment score: {result.sentiment_score:.3f}")
        delta_lines.append(f"  Yesterday's watchlist: {result.watchlist_critical_count} Critical, {result.watchlist_high_count} High")
        if result.narrative_data:
            try:
                narratives = json.loads(result.narrative_data) if isinstance(result.narrative_data, str) else result.narrative_data
                if narratives:
                    top = narratives[0]
                    delta_lines.append(f"  Yesterday's top narrative: {top.get('narrative','?')} at {top.get('share_of_voice',0):.1f}%")
            except Exception:
                pass
        delta_lines.append("Use this data to answer today-vs-yesterday questions precisely.")
        return "\n".join(delta_lines)

    except Exception:
        return "HISTORICAL CONTEXT: Historical snapshot data not yet available. If asked about today vs yesterday, explain that daily snapshots are building up and will be available after the next ingest cycle."


def _get_related_pages(page_route: str) -> list:
    related_map = {
        "/leadership-pack": ["/situation-room", "/watchlist", "/strategic-outcome"],
        "/situation-room": ["/leadership-pack", "/national-pulse", "/intelligence"],
        "/strategic-outcome": ["/leadership-pack", "/watchlist", "/intelligence"],
        "/watchlist": ["/leadership-pack", "/situation-room", "/strategic-outcome"],
        "/gnei": ["/national-pulse", "/strategic-outcome", "/leadership-pack"],
    }
    return related_map.get(page_route, ["/leadership-pack", "/situation-room"])


def _get_suggested_actions(page_route: str) -> list:
    actions = {
        "/leadership-pack": ["Review Watchlist for items requiring action today", "Navigate to Situation Room for deeper narrative analysis", "Download PDF briefing"],
        "/situation-room": ["Check Watchlist for escalation items", "Review National Pulse for sentiment context", "Navigate to Entity Intelligence for named actor analysis"],
        "/strategic-outcome": ["Review alignment scores for top opportunities", "Check stakeholder intelligence for engagement priorities"],
        "/watchlist": ["Acknowledge Critical items within 4 hours", "Navigate to Situation Room for item detail"],
        "/gnei": ["Check National Pulse for broader sentiment context", "Review SOI Dashboard for diaspora opportunities"],
    }
    return actions.get(page_route, ["Start with Leadership Pack for daily briefing", "Check Watchlist for priority items"])


# ── Rate limiting (simple Redis-based) ───────────────────────────────────

async def _check_rate_limit(user_email: str, db: Session) -> bool:
    """Returns True if request is allowed, False if rate limited."""
    try:
        import redis as redis_module
        from app.core.config import get_settings
        r = redis_module.from_url(get_settings().redis_url, decode_responses=True)
        key = f"copilot_ratelimit:{user_email}"
        count = r.get(key)
        if count and int(count) >= 20:
            return False
        pipe = r.pipeline()
        pipe.incr(key)
        pipe.expire(key, 3600)
        pipe.execute()
        return True
    except Exception:
        return True  # If Redis unavailable, allow through


# ── Conversation history ─────────────────────────────────────────────────

def _get_conversation_history(user_email: str) -> list:
    """Get last 5 conversation turns from Redis."""
    try:
        import redis as redis_module
        r = redis_module.from_url(get_settings().redis_url, decode_responses=True)
        key = f"copilot_history:{user_email}"
        history_json = r.get(key)
        if history_json:
            return json.loads(history_json)[-10:]  # Last 10 messages = 5 turns
        return []
    except Exception:
        return []


def _save_conversation_history(user_email: str, history: list):
    """Save conversation history to Redis with 2-hour TTL."""
    try:
        import redis as redis_module
        r = redis_module.from_url(get_settings().redis_url, decode_responses=True)
        key = f"copilot_history:{user_email}"
        r.set(key, json.dumps(history[-10:]), ex=7200)
    except Exception:
        pass


# ── Pydantic models ───────────────────────────────────────────────────────

class CopilotRequest(BaseModel):
    message: str
    page_route: str
    role: Optional[str] = None      # If None, derived from auth user's actual role
    data_context: Optional[dict] = None
    clear_history: Optional[bool] = False


class CopilotResponse(BaseModel):
    response: str
    suggested_actions: list[str]
    related_pages: list[str]
    had_historical_data: bool = False


# ── Routes ────────────────────────────────────────────────────────────────

@router.post("/ask", response_model=CopilotResponse)
async def ask_copilot(
    request: CopilotRequest,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """
    V8 Copilot endpoint.
    - Async Anthropic call (no worker blocking)
    - Role derived from auth user
    - Context Builder injects live data + historical delta
    - Conversation history maintained across turns
    - Rate limited to 20 requests/user/hour
    """
    user_email = current_user.get("email", "unknown")

    # EB-020: Rate limiting
    allowed = await _check_rate_limit(user_email, db)
    if not allowed:
        raise HTTPException(status_code=429, detail="Copilot rate limit reached (20 requests/hour). Please try again later.")

    # EB-007: Role from auth, not hardcoded
    user_role = request.role
    if not user_role:
        # Query user's actual role from database
        try:
            from sqlalchemy import text
            role_result = db.execute(text("""
                SELECT r.name FROM user_roles ur
                JOIN roles r ON r.id = ur.role_id
                JOIN admin_users u ON u.id = ur.user_id
                WHERE u.email = :email
                LIMIT 1
            """), {"email": user_email}).fetchone()
            user_role = role_result[0] if role_result else "executive"
        except Exception:
            user_role = "executive"

    # Build page context
    page_info = PAGE_CONTEXTS.get(request.page_route, PAGE_CONTEXTS["/"])
    page_context_str = f"Page: {page_info['name']}\nDescription: {page_info['description']}\nKey metrics: {', '.join(page_info['key_metrics'])}"
    role_context_str = ROLE_CONTEXTS.get(user_role, ROLE_CONTEXTS["executive"])

    # EB-014: Context Builder — data summary + historical delta
    data_summary = _build_data_summary(request.data_context)
    delta_section = _build_delta_section(db)
    had_historical = "Yesterday's Snapshot" in delta_section

    evidence_section = ""
    if request.data_context and "evidence" in request.data_context:
        ev = request.data_context["evidence"]
        evidence_section = f"EVIDENCE CONTEXT:\n{ev}"

    glossary_str = "\n".join([f"- {k}: {v}" for k, v in GLOSSARY.items()])

    system_prompt = SYSTEM_PROMPT.format(
        glossary=glossary_str,
        page_context=page_context_str,
        role_context=role_context_str,
        data_summary=data_summary,
        delta_section=delta_section,
        evidence_section=evidence_section,
    )

    # EB-015: Conversation history
    if request.clear_history:
        history = []
    else:
        history = _get_conversation_history(user_email)

    history.append({"role": "user", "content": request.message})

    api_key = getattr(settings, "anthropic_api_key", None)
    if not api_key:
        response_text = f"I can see you're on the {page_info['name']}. {page_info['description']} To enable full AI responses, configure ANTHROPIC_API_KEY."
    else:
        try:
            # EB-002: ASYNC httpx call — no more blocking workers
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.post(
                    "https://api.anthropic.com/v1/messages",
                    headers={
                        "x-api-key": api_key,
                        "anthropic-version": "2023-06-01",
                        "content-type": "application/json",
                    },
                    json={
                        "model": getattr(settings, "copilot_model", "claude-sonnet-4-6"),
                        "max_tokens": 700,
                        "system": system_prompt,
                        "messages": history,
                    },
                )
                resp.raise_for_status()
                result = resp.json()
                response_text = result["content"][0]["text"]

        except httpx.TimeoutException:
            response_text = "The AI service is taking longer than expected. Please try again in a moment."
        except httpx.HTTPStatusError as e:
            raise HTTPException(status_code=502, detail=f"AI service error: {e.response.status_code}")
        except Exception:
            response_text = f"I can see you're on the {page_info['name']}. I'm having trouble connecting right now. Please try again."

    # Save updated history
    history.append({"role": "assistant", "content": response_text})
    _save_conversation_history(user_email, history)

    return CopilotResponse(
        response=response_text,
        suggested_actions=_get_suggested_actions(request.page_route),
        related_pages=_get_related_pages(request.page_route),
        had_historical_data=had_historical,
    )


@router.post("/clear-history")
async def clear_history(current_user: dict = Depends(get_current_user)):
    """Clear the user's Copilot conversation history."""
    user_email = current_user.get("email", "unknown")
    try:
        import redis as redis_module
        r = redis_module.from_url(settings.redis_url, decode_responses=True)
        r.delete(f"copilot_history:{user_email}")
    except Exception:
        pass
    return {"status": "ok"}


@router.get("/page-context/{route:path}")
def get_page_context(route: str, _: dict = Depends(get_current_user)):
    route_key = "/" + route if not route.startswith("/") else route
    context = PAGE_CONTEXTS.get(route_key, PAGE_CONTEXTS["/"])
    return {"route": route_key, **context}


@router.get("/glossary")
def get_glossary(_: dict = Depends(get_current_user)):
    return {"terms": [{"term": k, "definition": v} for k, v in GLOSSARY.items()]}


@router.get("/glossary/{term}")
def get_term(term: str, _: dict = Depends(get_current_user)):
    definition = GLOSSARY.get(term.lower().replace(" ", "_"))
    if not definition:
        for key, val in GLOSSARY.items():
            if term.lower() in key:
                return {"term": key, "definition": val}
        raise HTTPException(status_code=404, detail=f"Term '{term}' not found")
    return {"term": term, "definition": definition}
