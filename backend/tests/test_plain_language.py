"""Unit tests for the regional-leader jargon guardrail — a deterministic
safety net for when a small local model ignores the "no jargon" prompt rule."""
from __future__ import annotations

from datetime import date

from app.models.evidence import (
    DataCompleteness,
    DriverContribution,
    EvidenceMethod,
    EvidencePacket,
    Hypothesis,
    KpiMovement,
)
from app.services.story.plain_language import build_plain_fallback_narrative, contains_jargon


def test_contains_jargon_detects_statistics_terms():
    assert contains_jargon("This has a correlation coefficient of 0.60 and a p-value of 0.05.")
    assert contains_jargon("The relationship is causally supported at a 4-week lag.")
    assert contains_jargon("Average discount rose by 13.1 percentage points.")


def test_contains_jargon_detects_raw_identifiers():
    assert contains_jargon("The drop was driven by quantity_effect and discount_effect.")
    assert contains_jargon("Correlated with technology_negative_share at a 4-week lead.")


def test_contains_jargon_false_for_clean_prose():
    assert not contains_jargon(
        "Sales dropped 35% this week, mainly because fewer units sold. "
        "We recommend checking with the regional sales team."
    )


def _movement(relative_change_pct: float) -> KpiMovement:
    return KpiMovement(
        kpi_id="weekly_sales_by_region",
        kpi_name="Weekly Sales by Region",
        dimension_label="West / Technology",
        period_start=date(2025, 12, 8),
        period_end=date(2025, 12, 14),
        actual_value=315029.31,
        expected_value=483607.06,
        forecast_band_low=384994.62,
        forecast_band_high=582219.51,
        absolute_change=-168577.75,
        relative_change_pct=relative_change_pct,
        is_material=True,
        method=EvidenceMethod.FORECAST_BAND_DEVIATION,
    )


def _completeness() -> DataCompleteness:
    return DataCompleteness(weeks_of_history=104, weeks_required_for_high_confidence=26, missing_periods=0, source_freshness_days=1)


def test_fallback_narrative_is_never_jargon():
    driver = DriverContribution(
        driver="quantity_effect",
        description="Units sold dropped.",
        contribution_value=-114739.2,
        contribution_pct=70.2,
        direction="decrease",
    )
    hyp = Hypothesis(
        id="unified",
        label="Demand / volume shift",
        summary="Driven by quantity effect.",
        drivers=[driver],
        correlations=[],
        statistical_strength=0.6,
        evidence_agreement=0.5,
        data_completeness_score=1.0,
        confidence=0.67,
    )
    evidence = EvidencePacket(
        insight_id="test",
        movement=_movement(-34.9),
        hypotheses=[hyp],
        top_hypothesis_id="unified",
        confidence_margin=None,
        abstained=False,
        abstention_reason=None,
        data_completeness=_completeness(),
        lineage=["raw -> processed"],
        generated_at="2026-01-01T00:00:00Z",
    )
    narrative = build_plain_fallback_narrative(evidence)
    assert not contains_jargon(narrative)
    assert "35%" in narrative or "34.9%" in narrative or "down 35%" in narrative or "down 34%" in narrative
    assert "West / Technology" in narrative


def test_fallback_narrative_for_abstained_movement_is_never_jargon():
    evidence = EvidencePacket(
        insight_id="test",
        movement=_movement(-26.3),
        hypotheses=[],
        top_hypothesis_id=None,
        confidence_margin=0.01,
        abstained=True,
        abstention_reason="Top hypothesis leads the runner-up by only 0.01.",
        data_completeness=_completeness(),
        lineage=["raw -> processed"],
        generated_at="2026-01-01T00:00:00Z",
    )
    narrative = build_plain_fallback_narrative(evidence)
    assert not contains_jargon(narrative)
    assert "analyst" in narrative.lower()
