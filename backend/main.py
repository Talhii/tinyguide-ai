"""TinyGuide AI — FastAPI entry point.

Boots an async FastAPI application on port 8000 with CORS enabled for the
localhost Next.js frontend, and mounts every Phase 1 router.

Run locally:
    uvicorn main:app --reload --port 8000
or simply:
    python main.py
"""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import __version__
from app.api import (
    analytics,
    dashboard,
    infants,
    milestones,
    rag,
    vaccinations,
)
from app.core.config import settings
from app.core.security import HealthStatus


@asynccontextmanager
async def lifespan(_: FastAPI):
    """Application lifespan hook — startup/shutdown wiring lives here."""
    # Startup: place warm-up (DB pools, vector store load) here.
    yield
    # Shutdown: place graceful cleanup here.


app = FastAPI(
    title=settings.app_name,
    version=__version__,
    description="AI Parenting Companion — backend microservice.",
    lifespan=lifespan,
)

# CORS: allow the localhost frontend to call the API during development.
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    # Accept any localhost/127.0.0.1 port so the app still works when the
    # Next.js dev server falls back from :3000 to :3001, :3002, etc.
    allow_origin_regex=r"https?://(localhost|127\.0\.0\.1)(:\d+)?",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount routers.
app.include_router(infants.router)
app.include_router(analytics.router)
app.include_router(milestones.router)
app.include_router(dashboard.router)
app.include_router(vaccinations.router)
app.include_router(rag.router)


@app.get("/", response_model=HealthStatus, tags=["health"])
async def root() -> HealthStatus:
    """Root health check."""
    return HealthStatus(version=__version__)


@app.get("/health", response_model=HealthStatus, tags=["health"])
async def health() -> HealthStatus:
    """Liveness probe."""
    return HealthStatus(version=__version__)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
    )
