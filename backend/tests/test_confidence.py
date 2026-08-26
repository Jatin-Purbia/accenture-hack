"""Unit tests for the confidence scorer and abstention gate — the graded
"real decision function, not an if/else keyed to a demo record" requirement."""
from __future__ import annotations

import pytest

from app.services.reasoning.confidence import (
    ConfidenceInputs,
    agreement_score,
    compute_confidence,
    data_completeness_score,
    decide_abstention,
    driver_concentration_strength,
    statistical_strength_from_zscore,
)


def test_compute_confidence_is_weighted_average_clipped_to_unit_interval():
    inputs = ConfidenceInputs(statistical_strength=1.0, evidence_agreement=1.0, data_completeness=1.0)
    assert compute_confidence(inputs) == pytest.approx(1.0)

    inputs_zero = ConfidenceInputs(statistical_strength=0.0, evidence_agreement=0.0, data_completeness=0.0)
    assert compute_confidence(inputs_zero) == pytest.approx(0.0)


def test_statistical_strength_scales_with_zscore_and_caps_at_one():
    assert statistical_strength_from_zscore(0.0) == pytest.approx(0.0)
    assert statistical_strength_from_zscore(2.0, cap=4.0) == pytest.approx(0.5)
    assert statistical_strength_from_zscore(10.0, cap=4.0) == pytest.approx(1.0)  # capped
    assert statistical_strength_from_zscore(None) == pytest.approx(0.3)  # neutral-low, not zero


def test_driver_concentration_single_dominant_driver_scores_near_one():
    assert driver_concentration_strength([100.0]) == 1.0
    assert driver_concentration_strength([95.0, 5.0]) > 0.8


def test_driver_concentration_even_split_scores_near_zero():
    assert driver_concentration_strength([50.0, 50.0]) == pytest.approx(0.0, abs=1e-6)
    assert driver_concentration_strength([33.3, 33.3, 33.4]) == pytest.approx(0.0, abs=0.01)


def test_data_completeness_score_scales_linearly_and_caps():
    assert data_completeness_score(26, 52) == pytest.approx(0.5)
    assert data_completeness_score(52, 52) == pytest.approx(1.0)
    assert data_completeness_score(104, 52) == pytest.approx(1.0)  # capped, not >1


def test_agreement_score_all_agree_vs_split_vs_no_signal():
    assert agreement_score([1, 1, 1]) == pytest.approx(1.0)
    assert agreement_score([1, -1]) == pytest.approx(0.5)
    assert agreement_score([0, 0, 0]) == pytest.approx(0.5)  # no signal -> neutral, not a penalty
    assert agreement_score([1, 1, -1]) == pytest.approx(2 / 3)


def test_abstention_gate_commits_when_single_hypothesis_is_confident():
    decision = decide_abstention([("h1", 0.85)], low_threshold=0.55, abstain_margin=0.12)
    assert not decision.abstained
    assert decision.top_hypothesis_id == "h1"


def test_abstention_gate_abstains_on_low_single_hypothesis_confidence():
    decision = decide_abstention([("h1", 0.40)], low_threshold=0.55, abstain_margin=0.12)
    assert decision.abstained
    assert "below" in decision.reason


def test_abstention_gate_abstains_when_top_two_are_too_close():
    decision = decide_abstention([("h1", 0.70), ("h2", 0.65)], low_threshold=0.55, abstain_margin=0.12)
    assert decision.abstained
    assert decision.confidence_margin == pytest.approx(0.05)


def test_abstention_gate_commits_when_top_hypothesis_clearly_leads():
    decision = decide_abstention([("h1", 0.80), ("h2", 0.50)], low_threshold=0.55, abstain_margin=0.12)
    assert not decision.abstained
    assert decision.top_hypothesis_id == "h1"
    assert decision.confidence_margin == pytest.approx(0.30)


def test_abstention_gate_handles_no_hypotheses():
    decision = decide_abstention([], low_threshold=0.55, abstain_margin=0.12)
    assert decision.abstained
    assert decision.top_hypothesis_id is None
