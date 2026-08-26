"""Insight, narrative, and action-recommendation schemas — the API's
top-level response shape for "explain this KPI movement"."""
from __future__ import annotations

from pydantic import BaseModel

from app.models.evidence import EvidencePacket


class ActionRecommendation(BaseModel):
    driver: str
    controllable_lever: str
    action: str
    expected_impact: str
    owner: str
    confidence: float
    monitoring_plan: str
    llm_phrased_summary: str | None = None


class GroundingCheckResult(BaseModel):
    passed: bool
    checked_numbers: list[str]
    ungrounded_numbers: list[str]


class LlmTelemetry(BaseModel):
    provider: str
    model: str
    tier: str  # "cheap" | "strong"
    tokens_in: int
    tokens_out: int
    latency_ms: float
    estimated_cost_usd: float
    cache_hit: bool
    called_at: str


class PersonaNarrative(BaseModel):
    persona_id: str
    persona_role: str
    headline: str
    narrative: str
    recommended_actions: list[ActionRecommendation]
    grounding: GroundingCheckResult
    llm_telemetry: LlmTelemetry | None


class Insight(BaseModel):
    insight_id: str
    kpi_id: str
    evidence: EvidencePacket
    narratives: dict[str, PersonaNarrative]  # keyed by persona_id
