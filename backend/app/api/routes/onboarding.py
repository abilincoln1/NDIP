"""
NDIP V7 — Onboarding & User State API

Persists user onboarding progress, tour completion state, feature discovery,
and learning path advancement. All state is stored in the database.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import Column, Integer, String, Boolean, DateTime, JSON, Text
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime, timezone
import json

from app.db.database import get_db, Base
from app.core.security import get_current_user

router = APIRouter(prefix="/onboarding", tags=["onboarding"])


# ── ORM Models ────────────────────────────────────────────────────────────────

class UserOnboardingState(Base):
    __tablename__ = "user_onboarding_state"

    id = Column(Integer, primary_key=True, index=True)
    user_email = Column(String(255), unique=True, nullable=False, index=True)
    role = Column(String(50), default="executive")
    onboarding_complete = Column(Boolean, default=False)
    current_step = Column(Integer, default=0)
    completed_tours = Column(JSON, default=list)        # list of page routes toured
    completed_modules = Column(JSON, default=list)      # list of academy module IDs
    visited_pages = Column(JSON, default=list)          # list of visited routes
    dismissed_tooltips = Column(JSON, default=list)     # list of dismissed tooltip IDs
    certification_level = Column(String(50), default="none")  # none/foundation/practitioner/professional/expert
    help_overlay_enabled = Column(Boolean, default=True)
    first_login_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    last_active_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    total_sessions = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


# ── Learning modules registry ─────────────────────────────────────────────────

LEARNING_MODULES = [
    {
        "id": "foundation_1",
        "title": "What is NDIP?",
        "level": "foundation",
        "duration_min": 5,
        "description": "Understand what NDIP is, what problem it solves, and how it was built.",
        "exercise": "Navigate to the Leadership Pack and identify the top narrative.",
        "prerequisite": None,
    },
    {
        "id": "foundation_2",
        "title": "Platform Navigation",
        "level": "foundation",
        "duration_min": 10,
        "description": "Learn to navigate between all dashboards and understand the sidebar structure.",
        "exercise": "Visit five different dashboards without using the back button.",
        "prerequisite": "foundation_1",
    },
    {
        "id": "foundation_3",
        "title": "Reading Confidence Labels",
        "level": "foundation",
        "duration_min": 5,
        "description": "Understand what High / Medium / Low confidence means and when to act on each.",
        "exercise": "Find one Low confidence metric on any dashboard and explain what it means.",
        "prerequisite": "foundation_2",
    },
    {
        "id": "beginner_1",
        "title": "Understanding Share of Voice",
        "level": "beginner",
        "duration_min": 15,
        "description": "Learn to read narrative dominance and what share of voice means for strategy.",
        "exercise": "Identify the top three narratives by share of voice and note whether they are rising or falling.",
        "prerequisite": "foundation_3",
    },
    {
        "id": "beginner_2",
        "title": "Reading the Watchlist",
        "level": "beginner",
        "duration_min": 10,
        "description": "Understand priority tiers: Critical, High, and Monitor. Know when to act vs when to watch.",
        "exercise": "Review the Watchlist and identify one item that requires same-day action and one that can wait.",
        "prerequisite": "beginner_1",
    },
    {
        "id": "intermediate_1",
        "title": "Narrative Momentum Analysis",
        "level": "intermediate",
        "duration_min": 20,
        "description": "Distinguish between volume momentum and strategic significance. Avoid false alarms.",
        "exercise": "Open Situation Room. Identify the highest-momentum narrative and determine whether it requires escalation.",
        "prerequisite": "beginner_2",
    },
    {
        "id": "intermediate_2",
        "title": "Stakeholder Intelligence",
        "level": "intermediate",
        "duration_min": 20,
        "description": "Read influence scores, composite rankings, and stakeholder momentum. Identify who to engage.",
        "exercise": "Identify the top three stakeholders by composite influence and note whether their momentum is rising or falling.",
        "prerequisite": "intermediate_1",
    },
    {
        "id": "advanced_1",
        "title": "Opportunity Intelligence",
        "level": "advanced",
        "duration_min": 30,
        "description": "Use the SOI Dashboard to identify opportunities, read alignment and readiness scores.",
        "exercise": "Find the top opportunity with score above 60 and produce a one-page action note.",
        "prerequisite": "intermediate_2",
    },
]

GUIDED_TOURS = {
    "/leadership-pack": {
        "id": "tour_leadership_pack",
        "title": "Leadership Pack Tour",
        "steps": [
            {"step": 1, "element": "executive_summary", "title": "Executive Summary", "content": "This is your daily briefing in two paragraphs. The platform has read all monitored discourse and distilled what matters most into this summary. Start here every morning."},
            {"step": 2, "element": "narrative_share_of_voice", "title": "Narrative Share of Voice", "content": "These percentages show what proportion of all monitored conversations is about each topic. The largest slice = where public attention is concentrated today."},
            {"step": 3, "element": "watchlist", "title": "Leadership Watchlist", "content": "Items here require your attention. Critical = act today. High = act this week. Monitor = review in your weekly meeting. You do not need to act on everything — that is what priority tiers are for."},
            {"step": 4, "element": "risks", "title": "Strategic Risks", "content": "Risks detected from narrative patterns and sentiment signals. Red = Critical (escalate now). Orange = Warning (address this week). Each risk shows the evidence behind it."},
            {"step": 5, "element": "opportunities", "title": "Strategic Opportunities", "content": "Windows of action detected from discourse signals. Higher opportunity scores mean stronger evidence and better timing. Check alignment and readiness scores before committing resources."},
            {"step": 6, "element": "confidence_statement", "title": "Confidence Statement", "content": "This tells you how reliable today's intelligence is. It reflects data volume, source diversity, and NLP processing rate. Low confidence = treat as preliminary signals only."},
            {"step": 7, "element": "download_pdf", "title": "Download Briefing", "content": "Click here to download a PDF version suitable for sharing with leadership or printing for meetings. This is a live snapshot — data will change with the next ingest cycle."},
        ],
    },
    "/situation-room": {
        "id": "tour_situation_room",
        "title": "Situation Room Tour",
        "steps": [
            {"step": 1, "element": "narrative_momentum", "title": "Narrative Momentum", "content": "The velocity at which each narrative is growing or shrinking. High positive momentum does not always mean high importance — check the source count and sentiment before acting."},
            {"step": 2, "element": "emerging_topics", "title": "Emerging Topics", "content": "Topics appearing for the first time or spiking suddenly across multiple sources. These are early warning signals — not confirmed trends. Treat as intelligence, not conclusions."},
            {"step": 3, "element": "sentiment_shift", "title": "Sentiment Shift", "content": "How overall emotional tone has changed since the previous period. A falling sentiment score in a high-volume narrative is the most important signal to watch."},
            {"step": 4, "element": "key_findings", "title": "Key Findings", "content": "The platform's automated assessment of what the data means. Read these alongside the raw metrics — they synthesise multiple signals into readable conclusions."},
        ],
    },
    "/strategic-outcome": {
        "id": "tour_soi_dashboard",
        "title": "SOI Dashboard Tour",
        "steps": [
            {"step": 1, "element": "opportunity_pipeline", "title": "Opportunity Pipeline", "content": "Shows how many opportunities exist at each stage: Detected → Assessed → Engaged → In Progress → Advanced → Secured. This is your strategic action funnel."},
            {"step": 2, "element": "top_opportunities", "title": "Top Opportunities", "content": "Ranked by Opportunity Score. Higher score = stronger discourse signal + better stakeholder alignment + more favourable conditions. Score 60+ = consider acting. Score 80+ = act now."},
            {"step": 3, "element": "stakeholder_rankings", "title": "Stakeholder Rankings", "content": "Who is most influential in the current strategic landscape. Ranked by composite index combining mention count, source diversity, momentum, and opportunity alignment."},
        ],
    },
    "/watchlist": {
        "id": "tour_watchlist",
        "title": "Watchlist Tour",
        "steps": [
            {"step": 1, "element": "priority_tiers", "title": "Priority Tiers", "content": "Critical = act today, brief leadership within 4 hours. High = act this week. Monitor = review in weekly team meeting. Not all items need the same response speed."},
            {"step": 2, "element": "watchlist_items", "title": "Watchlist Items", "content": "Each item shows: what triggered the alert, the momentum and sentiment, and the recommended action type. Click any item to see the source dashboard for more detail."},
        ],
    },
    "/gnei": {
        "id": "tour_gnei",
        "title": "GNEI Tour",
        "steps": [
            {"step": 1, "element": "gnei_score", "title": "GNEI Score", "content": "The Global Nigerian Engagement Index. A composite score reflecting the intensity and sentiment of diaspora-related discourse globally. Higher = more active, more engaged diaspora conversation."},
            {"step": 2, "element": "gnei_trend", "title": "GNEI Trend", "content": "Whether diaspora engagement is rising or falling over time. A sustained decline may indicate diminishing community attention — consider targeted outreach. A sharp rise may indicate a community event or crisis."},
        ],
    },
}


# ── Pydantic schemas ──────────────────────────────────────────────────────────

class OnboardingStateResponse(BaseModel):
    user_email: str
    role: str
    onboarding_complete: bool
    current_step: int
    completed_tours: list
    completed_modules: list
    visited_pages: list
    certification_level: str
    help_overlay_enabled: bool
    first_login_at: Optional[str]
    last_active_at: Optional[str]
    total_sessions: int
    progress_percent: int
    next_module: Optional[dict]
    available_modules: list


class UpdateStateRequest(BaseModel):
    action: str   # "complete_tour" | "complete_module" | "visit_page" | "dismiss_tooltip" | "set_role" | "toggle_help_overlay" | "record_session"
    value: Optional[str] = None


# ── Helper ────────────────────────────────────────────────────────────────────

def _get_or_create_state(db: Session, user_email: str) -> UserOnboardingState:
    state = db.query(UserOnboardingState).filter(
        UserOnboardingState.user_email == user_email
    ).first()
    if not state:
        state = UserOnboardingState(user_email=user_email)
        db.add(state)
        db.commit()
        db.refresh(state)
    return state


def _compute_progress(state: UserOnboardingState) -> int:
    """Compute overall onboarding progress as a percentage."""
    total_modules = len(LEARNING_MODULES)
    total_tours = len(GUIDED_TOURS)
    completed_modules = len(state.completed_modules or [])
    completed_tours = len(state.completed_tours or [])
    total = total_modules + total_tours
    completed = completed_modules + completed_tours
    return int((completed / total) * 100) if total > 0 else 0


def _get_next_module(state: UserOnboardingState) -> Optional[dict]:
    """Find the next uncompleted module the user is eligible for."""
    completed = set(state.completed_modules or [])
    for module in LEARNING_MODULES:
        if module["id"] in completed:
            continue
        prereq = module.get("prerequisite")
        if prereq is None or prereq in completed:
            return module
    return None


def _get_available_modules(state: UserOnboardingState) -> list:
    """Return all modules the user is eligible to take."""
    completed = set(state.completed_modules or [])
    available = []
    for module in LEARNING_MODULES:
        prereq = module.get("prerequisite")
        eligible = prereq is None or prereq in completed
        available.append({
            **module,
            "status": "completed" if module["id"] in completed else ("available" if eligible else "locked"),
        })
    return available


# ── Routes ────────────────────────────────────────────────────────────────────

@router.get("/state", response_model=OnboardingStateResponse)
def get_onboarding_state(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Returns the current user's onboarding state and progress."""
    user_email = current_user.get("email", "unknown")
    state = _get_or_create_state(db, user_email)
    next_module = _get_next_module(state)
    available_modules = _get_available_modules(state)

    return OnboardingStateResponse(
        user_email=state.user_email,
        role=state.role,
        onboarding_complete=state.onboarding_complete,
        current_step=state.current_step,
        completed_tours=state.completed_tours or [],
        completed_modules=state.completed_modules or [],
        visited_pages=state.visited_pages or [],
        certification_level=state.certification_level,
        help_overlay_enabled=state.help_overlay_enabled,
        first_login_at=state.first_login_at.isoformat() if state.first_login_at else None,
        last_active_at=state.last_active_at.isoformat() if state.last_active_at else None,
        total_sessions=state.total_sessions,
        progress_percent=_compute_progress(state),
        next_module=next_module,
        available_modules=available_modules,
    )


@router.post("/update")
def update_onboarding_state(
    update: UpdateStateRequest,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Update a specific aspect of the user's onboarding state."""
    user_email = current_user.get("email", "unknown")
    state = _get_or_create_state(db, user_email)

    now = datetime.now(timezone.utc)
    state.last_active_at = now

    if update.action == "complete_tour":
        tours = list(state.completed_tours or [])
        if update.value and update.value not in tours:
            tours.append(update.value)
        state.completed_tours = tours

    elif update.action == "complete_module":
        modules = list(state.completed_modules or [])
        if update.value and update.value not in modules:
            modules.append(update.value)
        state.completed_modules = modules
        # Check if foundation certification is earned
        foundation_ids = {m["id"] for m in LEARNING_MODULES if m["level"] == "foundation"}
        if foundation_ids.issubset(set(modules)) and state.certification_level == "none":
            state.certification_level = "foundation"

    elif update.action == "visit_page":
        pages = list(state.visited_pages or [])
        if update.value and update.value not in pages:
            pages.append(update.value)
        state.visited_pages = pages

    elif update.action == "dismiss_tooltip":
        tooltips = list(state.dismissed_tooltips or [])
        if update.value and update.value not in tooltips:
            tooltips.append(update.value)
        state.dismissed_tooltips = tooltips

    elif update.action == "set_role":
        if update.value in ("executive", "analyst", "admin", "campaign_director", "diaspora"):
            state.role = update.value

    elif update.action == "toggle_help_overlay":
        state.help_overlay_enabled = not state.help_overlay_enabled

    elif update.action == "record_session":
        state.total_sessions = (state.total_sessions or 0) + 1

    elif update.action == "complete_onboarding":
        state.onboarding_complete = True

    db.commit()
    return {"status": "ok", "action": update.action}


@router.get("/tours/{route:path}")
def get_tour(
    route: str,
    _: dict = Depends(get_current_user),
):
    """Returns the guided tour steps for a specific page route."""
    route_key = "/" + route if not route.startswith("/") else route
    tour = GUIDED_TOURS.get(route_key)
    if not tour:
        return {"route": route_key, "tour": None, "message": "No guided tour available for this page."}
    return {"route": route_key, "tour": tour}


@router.get("/modules")
def get_modules(_: dict = Depends(get_current_user)):
    """Returns all learning modules in the curriculum."""
    return {"modules": LEARNING_MODULES}


@router.get("/progress-summary")
def get_progress_summary(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Returns a summary of unused features and recommendations for the Platform Health Dashboard."""
    user_email = current_user.get("email", "unknown")
    state = _get_or_create_state(db, user_email)

    all_pages = list(PAGE_CONTEXTS_SIMPLE.keys())
    visited = set(state.visited_pages or [])
    unvisited = [p for p in all_pages if p not in visited]

    return {
        "progress_percent": _compute_progress(state),
        "completed_tours": len(state.completed_tours or []),
        "total_tours": len(GUIDED_TOURS),
        "completed_modules": len(state.completed_modules or []),
        "total_modules": len(LEARNING_MODULES),
        "certification_level": state.certification_level,
        "unused_pages": unvisited,
        "total_sessions": state.total_sessions,
        "days_since_first_login": (
            (datetime.now(timezone.utc) - state.first_login_at).days
            if state.first_login_at else 0
        ),
        "next_module": _get_next_module(state),
        "recommendations": _get_recommendations(state),
    }


def _get_recommendations(state: UserOnboardingState) -> list:
    """Generate personalised next-step recommendations."""
    recs = []
    completed_tours = set(state.completed_tours or [])
    completed_modules = set(state.completed_modules or [])

    if "/leadership-pack" not in completed_tours:
        recs.append({"type": "tour", "title": "Take the Leadership Pack tour", "route": "/leadership-pack", "reason": "It is your most important daily dashboard."})

    if "/watchlist" not in completed_tours:
        recs.append({"type": "tour", "title": "Take the Watchlist tour", "route": "/watchlist", "reason": "The Watchlist tells you what requires action today."})

    if "foundation_1" not in completed_modules:
        recs.append({"type": "module", "title": "Complete Foundation Module 1", "module_id": "foundation_1", "reason": "Start your NDIP certification journey."})

    next_module = _get_next_module(state)
    if next_module and next_module["id"] not in (r.get("module_id") for r in recs):
        recs.append({
            "type": "module",
            "title": f"Continue learning: {next_module['title']}",
            "module_id": next_module["id"],
            "reason": f"Next in your learning path ({next_module['duration_min']} min).",
        })

    return recs[:3]  # Max 3 recommendations


PAGE_CONTEXTS_SIMPLE = {
    "/": "Overview",
    "/leadership-pack": "Leadership Pack",
    "/situation-room": "Situation Room",
    "/watchlist": "Watchlist",
    "/national-pulse": "National Pulse",
    "/gnei": "GNEI",
    "/strategic-outcome": "SOI Dashboard",
    "/election-centre": "Election Intelligence",
    "/decision-quality": "Decision Support",
    "/intelligence": "Entity Intelligence",
    "/social": "Source Monitor",
    "/data-health": "Data Health",
    "/historical": "Historical Trends",
    "/intelligence-performance": "Intelligence Performance",
    "/participants": "Participants",
}
