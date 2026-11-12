"""
HMT backend -- FastAPI app.

This is a disaster information analysis and misinformation tracking
system, not a live real-time tracker. Any automated ingestion it does
(see app/external_feeds/) is periodic/near-real-time polling, never a
live stream -- see ARCHITECTURE.md.
"""
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.db.base import Base
from app.db.session import engine
from app.db import models  # noqa: F401 -- import registers all tables on Base.metadata before create_all runs
from app.external_feeds.scheduler import start_scheduler, stop_scheduler
from app.routers import admin, alerts, claims, feeds, health, map as map_router, stats
logging.basicConfig(level=logging.INFO)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # create_all, not Alembic -- see the docstring in app/db/models.py for why.
    Base.metadata.create_all(bind=engine)
    if settings.enable_feed_scheduler:
        start_scheduler()
    yield
    if settings.enable_feed_scheduler:
        stop_scheduler()


app = FastAPI(
    title="HMT -- Hyperlocal Misinformation Tracker for Disaster Relief",
    description="A disaster information analysis and misinformation tracking system. "
    "Research/capstone prototype -- see /docs for the API and the project README "
    "for what is real vs. Future Enhancement.",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(claims.router)
app.include_router(feeds.router)
app.include_router(alerts.router)
app.include_router(stats.router)
app.include_router(map_router.router)


app.include_router(admin.router)
