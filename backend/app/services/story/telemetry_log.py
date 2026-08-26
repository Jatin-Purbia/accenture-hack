"""In-memory telemetry log — every LLM call (or cache hit) made through
narrative_service.py is appended here, and the /api/telemetry route
summarizes it for the UI's telemetry panel. Process-lifetime only, same
scaling note as cache.py applies (swap for a real metrics backend in
production)."""
from __future__ import annotations

from dataclasses import dataclass, field

from app.models.insight import LlmTelemetry


@dataclass
class TelemetryLog:
    entries: list[LlmTelemetry] = field(default_factory=list)

    def record(self, telemetry: LlmTelemetry) -> None:
        self.entries.append(telemetry)

    def summary(self) -> dict:
        if not self.entries:
            return {
                "total_calls": 0, "cache_hits": 0, "cache_hit_rate": 0.0,
                "total_tokens_in": 0, "total_tokens_out": 0,
                "total_estimated_cost_usd": 0.0, "avg_latency_ms": 0.0,
                "tier_breakdown": {}, "model_breakdown": {},
            }
        cache_hits = sum(1 for e in self.entries if e.cache_hit)
        tier_breakdown: dict[str, int] = {}
        model_breakdown: dict[str, int] = {}
        for e in self.entries:
            tier_breakdown[e.tier] = tier_breakdown.get(e.tier, 0) + 1
            model_breakdown[e.model] = model_breakdown.get(e.model, 0) + 1
        non_cached = [e for e in self.entries if not e.cache_hit]
        return {
            "total_calls": len(self.entries),
            "cache_hits": cache_hits,
            "cache_hit_rate": cache_hits / len(self.entries),
            "total_tokens_in": sum(e.tokens_in for e in self.entries),
            "total_tokens_out": sum(e.tokens_out for e in self.entries),
            "total_estimated_cost_usd": sum(e.estimated_cost_usd for e in self.entries),
            "avg_latency_ms": (sum(e.latency_ms for e in non_cached) / len(non_cached)) if non_cached else 0.0,
            "tier_breakdown": tier_breakdown,
            "model_breakdown": model_breakdown,
        }


_singleton: TelemetryLog | None = None


def get_telemetry_log() -> TelemetryLog:
    global _singleton
    if _singleton is None:
        _singleton = TelemetryLog()
    return _singleton
