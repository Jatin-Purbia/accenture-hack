"""FastAPI application entry point. Routers are thin (app/api/*) — all
business logic lives in app/services/*; this module only wires them together."""
from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import feedback, insights, kpis, personas, scenarios, telemetry
from app.core.config import get_settings
from app.core.dependencies import data_store_dependency
from app.core.logging import configure_logging, get_logger

configure_logging()
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    logger.info("app_starting", env=settings.app_env, llm_provider=settings.llm_provider)
    # Preload the data store at startup rather than on the first request —
    # keeps first-request latency predictable for the demo.
    data_store_dependency()
    logger.info("app_ready")
    yield
    logger.info("app_shutdown")


app = FastAPI(
    title="KPI Storytelling Engine",
    description="A KPI intelligence-to-action engine — deterministic Signal/Reasoning layers, LLM only at the Story layer.",
    version="1.0.0",
    lifespan=lifespan,
)

settings = get_settings()
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(personas.router)
app.include_router(kpis.router)
app.include_router(scenarios.router)
app.include_router(insights.router)
app.include_router(feedback.router)
app.include_router(telemetry.router)


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok"}
