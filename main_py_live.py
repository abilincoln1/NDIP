from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.core.config import get_settings
from app.db.database import engine, Base
from app.models import models  # noqa
from app.api.routes import (
    auth, participants, events, engagement,
    social, analytics, reports, intelligence,
    data_health, briefing, situation_room,
    historical, leadership_pack, national_pulse, pdf_export, entity_intelligence,
    watchlist, gnei, strategic_outcome,
)

settings = get_settings()

@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    yield

app = FastAPI(title="RTIFN National & Diaspora Intelligence Platform (NDIP) API", version="5.3.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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

@app.get("/", tags=["health"])
def root():
    return {"service": "RTIFN National & Diaspora Intelligence Platform (NDIP)", "version": "5.3.0", "status": "operational"}

@app.get("/health", tags=["health"])
def health():
    return {"status": "ok"}
