from fastapi import FastAPI
from app.api.routes.learning_router import router as learning_router
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from app.core.config import get_settings
from app.db.database import engine, Base
from app.models import models  # noqa
from app.models import chapter, member, member_profile, member_session  # noqa — Phase D.2: register ORM tables
from app.api.routes import copilot_v8 as copilot_router, onboarding as onboarding_router
from app.api.routes import (
    auth, participants, events, engagement,
    social, analytics, reports, intelligence,
    data_health, briefing, situation_room,
    historical, leadership_pack, national_pulse, pdf_export, entity_intelligence,
    watchlist, gnei, strategic_outcome, content_generation,
    geography, members,
)
# Phase D.3 additions
from app.api.middleware.observability import ObservabilityMiddleware
from app.api.routes.health_v2 import health_router, RateLimitMiddleware
from app.api.routes.auth_v2 import router as auth_v2_router
from app.api.routes.reports_v2 import router as reports_v2_router
from app.api.routes.platform_routes import (
    projects_router, sponsorships_router, ward_exec_router,
    verification_router, impact_router, admin_router,
)

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    yield


from app.api.middleware.audit import AuditLogMiddleware

app = FastAPI(
    title="RTIFN National & Diaspora Intelligence Platform (NDIP) API",
    version="5.3.0",
    lifespan=lifespan,
    description="NDIP — Phase D.3 Platform Readiness",
)

# Middleware stack (outermost = first to receive request, last to send response)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(ObservabilityMiddleware)   # D3.8 — request ID + structured logging + identity
app.add_middleware(RateLimitMiddleware)        # D3.9 — rate limiting (60/20/10 req/min tiers)
app.add_middleware(AuditLogMiddleware)         # D3.8 — persistent audit trail

# Phase A–C routers (unchanged — full backward compatibility maintained)
app.include_router(auth.router)
app.include_router(participants.router)
app.include_router(events.router)
app.include_router(engagement.router)
app.include_router(social.router)
app.include_router(analytics.router)
app.include_router(reports.router)
app.include_router(intelligence.router)
app.include_router(data_health.router)
app.include_router(briefing.router)
app.include_router(situation_room.router)
app.include_router(historical.router)
app.include_router(leadership_pack.router)
app.include_router(national_pulse.router)
app.include_router(pdf_export.router)
app.include_router(entity_intelligence.router)
app.include_router(watchlist.router)
app.include_router(gnei.router)
app.include_router(strategic_outcome.router)
app.include_router(content_generation.router)
app.include_router(copilot_router.router)
app.include_router(onboarding_router.router)
app.include_router(learning_router)
app.include_router(geography.router)    # /api/v2/geography — Phase D.1
app.include_router(members.router)      # /api/v2/members   — Phase D.2

# Phase D.3 routers
app.include_router(auth_v2_router)          # /api/v2/auth
app.include_router(reports_v2_router)       # /api/v2/reports
app.include_router(projects_router)         # /api/v2/projects
app.include_router(sponsorships_router)     # /api/v2/sponsorships
app.include_router(ward_exec_router)        # /api/v2/ward-executives
app.include_router(verification_router)     # /api/v2/verification
app.include_router(impact_router)           # /api/v2/impact
app.include_router(admin_router)            # /api/v2/admin
app.include_router(health_router)           # /readiness, /api/v2/metrics


@app.get("/", tags=["health"])
def root():
    return {
        "service": "RTIFN National & Diaspora Intelligence Platform (NDIP)",
        "version": "5.3.0",
        "phase": "D.3 Platform Readiness",
        "status": "operational",
    }


@app.get("/health", tags=["health"])
def health():
    return {"status": "ok"}
