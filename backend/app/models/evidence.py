"""Evidence-packet schemas.

The Evidence Packet is the ONLY thing the Story layer (LLM) is ever given.
It is fully structured, fully numeric/typed, and never contains raw
transaction rows or raw ticket text — every field here is something a
deterministic upstream computation produced and can be traced back to a
lineage step. This is what makes the grounding check in
services/story/grounding.py possible: every number the LLM outputs must
appear somewhere in the packet it was given.
"""
from __future__ import annotations

from datetime import date
from enum import Enum

from pydantic import BaseModel, Field


class EvidenceMethod(str, Enum):
    """Tags every piece of evidence with which analytical method produced it
    — this is what powers the UI's "LLM vs non-LLM" breakdown panel."""

    TREND_SEASONALITY_DECOMPOSITION = "trend_seasonality_decomposition"
    FORECAST_BAND_DEVIATION = "forecast_band_deviation"
    DRIVER_TREE_DECOMPOSITION = "driver_tree_decomposition"
    LAG_CORRELATION_TEST = "lag_correlation_test"
    LEXICON_SENTIMENT_SCORING = "lexicon_sentiment_scoring"
    RULE_BASED_NLP_EVENT_EXTRACTION = "rule_based_nlp_event_extraction"
    CONFIDENCE_SCORING = "confidence_scoring"
    RULE_BASED_ACTION_LOOKUP = "rule_based_action_lookup"
    LLM_NARRATIVE_PHRASING = "llm_narrative_phrasing"


class CorrelationClass(str, Enum):
    CAUSALLY_SUPPORTED = "causally_supported"
    CORRELATED = "correlated"
    INSUFFICIENT_EVIDENCE = "insufficient_evidence"


class DriverContribution(BaseModel):
    driver: str
    description: str
    contribution_value: float
    contribution_pct: float
    direction: str  # "increase" | "decrease"
    method: EvidenceMethod = EvidenceMethod.DRIVER_TREE_DECOMPOSITION


class CorrelationSignal(BaseModel):
    signal_name: str
    source_kpi_id: str
    lag_weeks: int
    correlation_coefficient: float
    p_value: float
    classification: CorrelationClass
    rationale: str
    method: EvidenceMethod = EvidenceMethod.LAG_CORRELATION_TEST


class DataCompleteness(BaseModel):
    weeks_of_history: int
    weeks_required_for_high_confidence: int
    missing_periods: int
    source_freshness_days: int = Field(
        description="Days since the underlying source was last refreshed"
    )

    @property
    def is_sparse(self) -> bool:
        return self.weeks_of_history < self.weeks_required_for_high_confidence


class Hypothesis(BaseModel):
    id: str
    label: str
    summary: str
    drivers: list[DriverContribution]
    correlations: list[CorrelationSignal]
    statistical_strength: float = Field(ge=0.0, le=1.0)
    evidence_agreement: float = Field(ge=0.0, le=1.0)
    data_completeness_score: float = Field(ge=0.0, le=1.0)
    confidence: float = Field(ge=0.0, le=1.0)


class TrendPoint(BaseModel):
    week_start: date
    actual: float
    expected: float
    band_low: float
    band_high: float
    is_material: bool


class KpiMovement(BaseModel):
    kpi_id: str
    kpi_name: str
    dimension_label: str
    period_start: date
    period_end: date
    actual_value: float
    expected_value: float
    forecast_band_low: float
    forecast_band_high: float
    absolute_change: float
    relative_change_pct: float
    is_material: bool
    method: EvidenceMethod = EvidenceMethod.FORECAST_BAND_DEVIATION


class EvidencePacket(BaseModel):
    """The complete, structured bundle handed to the Story layer LLM call."""

    insight_id: str
    movement: KpiMovement
    trend: list[TrendPoint] = Field(default_factory=list)
    hypotheses: list[Hypothesis]
    top_hypothesis_id: str | None
    confidence_margin: float | None = Field(
        default=None,
        description="Confidence gap between top-2 hypotheses; None if only one hypothesis exists",
    )
    abstained: bool
    abstention_reason: str | None
    data_completeness: DataCompleteness
    lineage: list[str]
    generated_at: str
