"""FastAPI dependency wiring — every router depends on these instead of
constructing services itself, keeping routers thin and every dependency
swappable (e.g. for tests) via FastAPI's dependency_overrides."""
from __future__ import annotations

from functools import lru_cache

from fastapi import Header, HTTPException

from app.core.access_control import DEFAULT_PERSONA_ID, Persona, UnknownPersonaError, get_persona
from app.core.config import Settings, get_settings
from app.models.kpi import KpiContract
from app.services.data.feedback_store import FeedbackStore, get_feedback_store
from app.services.data.kpi_registry import load_kpi_contract
from app.services.reasoning.evidence_builder import DataStore, load_data_store
from app.services.story.cache import NarrativeCache, get_narrative_cache
from app.services.story.llm_client import LLMClient, build_llm_client
from app.services.story.telemetry_log import TelemetryLog, get_telemetry_log


def settings_dependency() -> Settings:
    return get_settings()


def data_store_dependency() -> DataStore:
    settings = get_settings()
    return load_data_store(settings.data_raw_path)


def kpi_contract_dependency() -> KpiContract:
    settings = get_settings()
    return load_kpi_contract(settings.docs_path)


@lru_cache
def _llm_client_singleton() -> LLMClient:
    return build_llm_client(get_settings())


def llm_client_dependency() -> LLMClient:
    return _llm_client_singleton()


def narrative_cache_dependency() -> NarrativeCache:
    return get_narrative_cache()


def telemetry_log_dependency() -> TelemetryLog:
    return get_telemetry_log()


def feedback_store_dependency() -> FeedbackStore:
    settings = get_settings()
    log_path = settings.repo_root / "backend" / "app" / "data_store" / "feedback_log.jsonl"
    return get_feedback_store(log_path)


def persona_dependency(x_persona_id: str | None = Header(default=None)) -> Persona:
    persona_id = x_persona_id or DEFAULT_PERSONA_ID
    try:
        return get_persona(persona_id)
    except UnknownPersonaError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
