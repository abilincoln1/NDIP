"""
NDIP V7 — AI Copilot API
Embedded intelligence assistant accessible from every dashboard page.
Understands current page context, user role, and platform data state.
Uses the Anthropic API with full platform context injected into the system prompt.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
import httpx
import json
from datetime import datetime, timezone

from app.db.database import get_db
from app.core.security import get_current_user
from app.core.config import get_settings

router = APIRouter(prefix="/copilot", tags=["copilot"])

settings = get_settings()

# ── Page context registry ─────────────────────────────────────────────────────
# Maps frontend routes to plain-English descriptions injected into the Copilot
# system prompt so it knows what the user is looking at.

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
    "/decision-quality": {
        "name": "Decision Support",
        "description": "Tracks the platform's own prediction accuracy. Shows which recommendations were acted on, which proved correct, and the platform learning score.",
        "key_metrics": ["decision_quality_score", "recommendation_accuracy", "platform_learning_score"],
        "who_uses": "Senior leadership, Analysts",
        "primary_purpose": "Trust calibration and recommendation validation",
    },
    "/watchlist": {
        "name": "Leadership Watchlist",
        "description": "Prioritised alert list of items requiring leadership attention — risks, accelerating narratives, stakeholder movements. Items are tiered: Critical, High, Monitor.",
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
    "/intelligence": {
        "name": "Entity Intelligence",
        "description": "Named entity analysis. Shows which people, organisations, and places are most mentioned across monitored discourse.",
        "key_metrics": ["entity_frequency", "entity_sentiment", "entity_trend"],
        "who_uses": "Research analysts",
        "primary_purpose": "Deep entity-level intelligence analysis",
    },
    "/social": {
        "name": "Source Monitor",
        "description": "Health monitoring for data connectors. Shows which sources are active, failing, or returning low-quality data.",
        "key_metrics": ["connector_health", "source_count", "processing_rate"],
        "who_uses": "Administrators",
        "primary_purpose": "Data source quality assurance",
    },
    "/data-health": {
        "name": "Data Health",
        "description": "System health dashboard. Shows ingest job status, NLP processing rates, normalisation statistics, and error logs.",
        "key_metrics": ["ingest_success_rate", "nlp_rate", "normalisation_count"],
        "who_uses": "Administrators",
        "primary_purpose": "Platform health monitoring",
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
    "analyst": "You are speaking to a professional intelligence analyst. Use precise language. Include metric values, data sources, and caveats. Explain methodology when relevant. You can use technical terms but should always define them in context.",
    "admin": "You are speaking to a platform administrator. You can reference technical components (Redis, ingest pipeline, database tables). Provide diagnostic precision. Focus on system health and operational concerns.",
    "campaign_director": "You are speaking to a Campaign Director. Focus on electoral intelligence, narrative strategy, stakeholder engagement priorities, and opportunity scoring. Connect intelligence to actionable campaign decisions.",
    "diaspora": "You are speaking to a Diaspora Coordinator. Focus on GNEI, diaspora sentiment, community signals, remittance narratives, and diaspora engagement opportunities. Connect intelligence to community mobilisation.",
}

GLOSSARY = {
    "share_of_voice": "The percentage of total monitored discourse that a specific topic or narrative represents. Higher = more dominant in public conversation.",
    "momentum": "The rate of change in discourse volume. +300% means 3x more discussion than the previous equivalent period. Positive = growing, negative = declining.",
    "sentiment_score": "Emotional tone of discourse. Ranges from -1 (strongly negative) to +1 (strongly positive). 0 = neutral.",
    "engagement_index": "A composite score (0–5+) reflecting overall platform intelligence intensity. Combines volume, source diversity, sentiment intensity, and growth rate.",
    "influence_score": "How prominently a stakeholder appears in monitored discourse. Combines mention count, source count, and momentum.",
    "opportunity_score": "How strong the discourse signal is for a strategic opportunity. Higher = stronger evidence, better timing.",
    "alignment_score": "How closely a stakeholder's activities align with a specific opportunity. High = they are already engaged in the relevant space.",
    "readiness_score": "How ready conditions are for an opportunity to be acted on. Combines political environment, stakeholder availability, and discourse momentum.",
    "confidence_label": "High / Medium / Low reliability assessment based on data volume, source diversity, and recency.",
    "materialised_intelligence": "Pre-computed intelligence stored in the database after each ingest run, enabling fast dashboard loading.",
    "ingest": "The automated daily process of fetching new content from monitored sources and processing it for analysis.",
    "narrative": "A recurring theme or story in public discourse. NDIP monitors 11 strategic narratives including Security, Economy, Governance, and Diaspora Engagement.",
    "gnei": "Global Nigerian Engagement Index. Measures intensity and sentiment of diaspora-related discourse globally.",
    "watchlist": "A prioritised list of intelligence items automatically populated when thresholds are crossed: Critical (act today), High (act this week), Monitor (weekly review).",
}

SYSTEM_PROMPT_BASE = """You are the NDIP AI Copilot — an intelligent assistant embedded in the National & Diaspora Intelligence Platform built by RTIFN.

YOUR ROLE:
- Help users understand what they are looking at
- Explain metrics and scores in plain English
- Recommend next best actions based on current intelligence
- Guide users through the platform
- Answer "why is this happening?" and "what should I do?" questions

CRITICAL RULES:
1. Never mention technical internals: no table names, no Python functions, no API routes, no database queries
2. Always qualify uncertain intelligence using confidence labels
3. Never make political judgements — describe what data shows, not what it means politically
4. Be honest about data gaps and low-confidence findings
5. Adapt your language to the user's role (set in context below)
6. Keep responses focused and practical — executives want 3 sentences, analysts want detail

PLATFORM GLOSSARY (use these definitions when explaining concepts):
{glossary}

CURRENT PAGE CONTEXT:
{page_context}

USER ROLE CONTEXT:
{role_context}

CURRENT PLATFORM DATA SUMMARY:
{data_summary}

When the user asks "What should I look at first?", "What changed?", "Explain this dashboard", "What action should I take?" — answer based on the current page and data context above.
"""


class CopilotRequest(BaseModel):
    message: str
    page_route: str
    role: Optional[str] = "executive"
    data_context: Optional[dict] = None  # Key metrics from the current page, passed by the frontend


class CopilotResponse(BaseModel):
    response: str
    suggested_actions: list[str]
    related_pages: list[str]


def _build_data_summary(data_context: Optional[dict], page_route: str) -> str:
    """Build a plain-English summary of current page data for the Copilot system prompt."""
    if not data_context:
        return "No current page data available. Respond based on the page context above."

    lines = []

    # Leadership Pack data
    if "narratives" in data_context:
        narratives = data_context.get("narratives", [])
        if narratives:
            top = narratives[0]
            lines.append(f"Top narrative: {top.get('narrative', 'unknown')} at {top.get('share_of_voice', 0)}% share of voice, {top.get('sentiment_label', 'neutral')} sentiment, {top.get('momentum_direction', 'stable')} momentum.")

    if "risks" in data_context:
        risks = data_context.get("risks", [])
        critical = [r for r in risks if r.get("level") in ("Critical", "High")]
        if critical:
            lines.append(f"Active risks: {len(critical)} high/critical items including: {critical[0].get('title', 'unknown')}.")

    if "opportunities" in data_context:
        opps = data_context.get("opportunities", [])
        if opps:
            lines.append(f"Top opportunity: {opps[0].get('title', 'unknown')} (score: {opps[0].get('opportunity_score', 'N/A')}).")

    if "engagement_index" in data_context:
        lines.append(f"Engagement Index: {data_context['engagement_index']} (platform activity level).")

    if "sentiment_score" in data_context:
        lines.append(f"Overall sentiment score: {data_context['sentiment_score']}.")

    if "watchlist_count" in data_context:
        lines.append(f"Watchlist: {data_context['watchlist_count']} items requiring attention.")

    if "confidence" in data_context:
        lines.append(f"Intelligence confidence: {data_context['confidence']}.")

    if "gnei_score" in data_context:
        lines.append(f"GNEI (diaspora engagement index): {data_context['gnei_score']}.")

    if "stakeholders" in data_context:
        stakeholders = data_context.get("stakeholders", [])
        if stakeholders:
            lines.append(f"Top stakeholder: {stakeholders[0].get('name', 'unknown')} (influence score: {stakeholders[0].get('composite_index', 'N/A')}).")

    if not lines:
        lines.append("Current page is loaded. Respond based on the page description above.")

    return " ".join(lines)


def _get_related_pages(page_route: str, message: str) -> list[str]:
    """Suggest related pages based on current context and question."""
    related_map = {
        "/leadership-pack": ["/situation-room", "/watchlist", "/decision-quality"],
        "/situation-room": ["/leadership-pack", "/national-pulse", "/intelligence"],
        "/strategic-outcome": ["/leadership-pack", "/watchlist", "/intelligence"],
        "/election-centre": ["/strategic-outcome", "/national-pulse", "/watchlist"],
        "/gnei": ["/national-pulse", "/strategic-outcome", "/leadership-pack"],
        "/watchlist": ["/leadership-pack", "/situation-room", "/strategic-outcome"],
    }
    return related_map.get(page_route, ["/leadership-pack", "/situation-room"])


def _get_suggested_actions(page_route: str, data_context: Optional[dict]) -> list[str]:
    """Generate contextual next-action suggestions."""
    actions = {
        "/leadership-pack": [
            "Review the Watchlist for items requiring action today",
            "Download the PDF briefing to share with leadership",
            "Navigate to Situation Room for deeper narrative analysis",
        ],
        "/situation-room": [
            "Check the Watchlist for escalation items",
            "Review National Pulse for sentiment trend context",
            "Navigate to Entity Intelligence for named actor analysis",
        ],
        "/strategic-outcome": [
            "Review Alignment Scores for top opportunities",
            "Check Stakeholder Intelligence for engagement priorities",
            "Navigate to Leadership Pack for narrative context",
        ],
        "/watchlist": [
            "Acknowledge Critical items within 4 hours",
            "Navigate to Situation Room for item detail",
            "Download leadership briefing for context",
        ],
        "/gnei": [
            "Check National Pulse for broader sentiment context",
            "Review SOI Dashboard for diaspora opportunities",
            "Navigate to Leadership Pack for diaspora narrative assessment",
        ],
    }
    default = [
        "Start with the Leadership Pack for your daily briefing",
        "Check the Watchlist for priority items",
        "Review the Situation Room for current narrative momentum",
    ]
    return actions.get(page_route, default)


@router.post("/ask", response_model=CopilotResponse)
async def ask_copilot(
    request: CopilotRequest,
    db: Session = Depends(get_db),
    _: dict = Depends(get_current_user),
):
    """
    Main Copilot endpoint. Accepts a user question, current page route,
    user role, and optional page data context. Returns an AI-generated
    response with suggested next actions and related pages.
    """
    # Build page context
    page_info = PAGE_CONTEXTS.get(request.page_route, PAGE_CONTEXTS["/"])
    page_context_str = f"""
Page: {page_info['name']}
Description: {page_info['description']}
Who uses this page: {page_info['who_uses']}
Primary purpose: {page_info['primary_purpose']}
Key metrics on this page: {', '.join(page_info['key_metrics'])}
"""

    # Build role context
    role_context_str = ROLE_CONTEXTS.get(request.role or "executive", ROLE_CONTEXTS["executive"])

    # Build data summary
    data_summary = _build_data_summary(request.data_context, request.page_route)

    # Build glossary string
    glossary_str = "\n".join([f"- {k}: {v}" for k, v in GLOSSARY.items()])

    # Build system prompt
    system_prompt = SYSTEM_PROMPT_BASE.format(
        glossary=glossary_str,
        page_context=page_context_str,
        role_context=role_context_str,
        data_summary=data_summary,
    )

    # Call Anthropic API
    anthropic_api_key = getattr(settings, "anthropic_api_key", None)
    if not anthropic_api_key:
        # Graceful fallback if no API key configured
        return CopilotResponse(
            response=f"I can see you're on the {page_info['name']}. {page_info['description']} To configure the AI Copilot with full capabilities, set ANTHROPIC_API_KEY in your environment.",
            suggested_actions=_get_suggested_actions(request.page_route, request.data_context),
            related_pages=_get_related_pages(request.page_route, request.message),
        )

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                "https://api.anthropic.com/v1/messages",
                headers={
                    "x-api-key": anthropic_api_key,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json",
                },
                json={
                    "model": "claude-sonnet-4-6",
                    "max_tokens": 600,
                    "system": system_prompt,
                    "messages": [
                        {"role": "user", "content": request.message}
                    ],
                },
            )
            response.raise_for_status()
            result = response.json()
            ai_response = result["content"][0]["text"]

    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=502, detail=f"AI service error: {e.response.status_code}")
    except Exception as e:
        # Return useful fallback rather than crashing
        ai_response = f"I can see you're on the {page_info['name']}. {page_info['description']} Your question was: '{request.message}'. Please check that the ANTHROPIC_API_KEY is configured correctly."

    return CopilotResponse(
        response=ai_response,
        suggested_actions=_get_suggested_actions(request.page_route, request.data_context),
        related_pages=_get_related_pages(request.page_route, request.message),
    )


@router.get("/page-context/{route:path}")
def get_page_context(
    route: str,
    _: dict = Depends(get_current_user),
):
    """
    Returns the plain-English context for a given page route.
    Used by the frontend Help Overlay and guided tours.
    """
    route_key = "/" + route if not route.startswith("/") else route
    context = PAGE_CONTEXTS.get(route_key, PAGE_CONTEXTS["/"])
    return {
        "route": route_key,
        "name": context["name"],
        "description": context["description"],
        "who_uses": context["who_uses"],
        "primary_purpose": context["primary_purpose"],
        "key_metrics": context["key_metrics"],
    }


@router.get("/glossary")
def get_glossary(_: dict = Depends(get_current_user)):
    """Returns the full platform glossary for the Knowledge Base and Help Overlay."""
    return {"terms": [{"term": k, "definition": v} for k, v in GLOSSARY.items()]}


@router.get("/glossary/{term}")
def get_term(term: str, _: dict = Depends(get_current_user)):
    """Returns the definition of a specific term."""
    definition = GLOSSARY.get(term.lower().replace(" ", "_"))
    if not definition:
        # Try partial match
        for key, val in GLOSSARY.items():
            if term.lower() in key:
                return {"term": key, "definition": val}
        raise HTTPException(status_code=404, detail=f"Term '{term}' not found in glossary")
    return {"term": term, "definition": definition}
