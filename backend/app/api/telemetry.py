"""Telemetry router — backs the UI's live cost/latency/model-usage panel."""
from __future__ import annotations

from fastapi import APIRouter, Depends

from app.core.dependencies import narrative_cache_dependency, telemetry_log_dependency
from app.services.story.cache import NarrativeCache
from app.services.story.telemetry_log import TelemetryLog

router = APIRouter(prefix="/api/telemetry", tags=["telemetry"])


@router.get("")
def get_telemetry(
    telemetry_log: TelemetryLog = Depends(telemetry_log_dependency),
    cache: NarrativeCache = Depends(narrative_cache_dependency),
) -> dict:
    summary = telemetry_log.summary()
    summary["cache_size"] = cache.size
    summary["cache_lookup_hit_rate"] = cache.hit_rate
    return summary
