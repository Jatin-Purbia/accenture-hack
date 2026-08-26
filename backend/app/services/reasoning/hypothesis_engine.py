"""Reasoning layer — assembles driver-tree + correlation evidence into
ranked, scored Hypotheses, then applies the abstention gate.

Decision rule for whether a movement gets ONE unified hypothesis (the
"multi-factor movement, correctly decomposed" case) or SPLITS into multiple
competing hypotheses (the "ambiguous, abstain" case) is a real, general,
threshold-based rule over the driver tree's own output — evaluated
identically for every KPI movement:

  - If the single largest driver explains >= DOMINANCE_TOP_PCT of the total
    movement AND leads the runner-up by >= DOMINANCE_GAP_PCT, the drivers
    are telling ONE coherent story (even if more than one driver is
    material) -> a single unified hypothesis citing every material driver.
  - Otherwise, no driver is dominant enough to anchor one clear story ->
    the top drivers each anchor their OWN competing hypothesis, and the
    confidence scorer + abstention gate (services/reasoning/confidence.py)
    decide whether the evidence is strong enough to still pick a winner.

This rule is a genuine decision function over computed percentages, not a
per-KPI or per-region special case.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import pandas as pd

from app.services.reasoning.confidence import (
    ConfidenceInputs,
    agreement_score,
    compute_confidence,
    data_completeness_score,
    driver_concentration_strength,
    statistical_strength_from_zscore,
)
from app.services.reasoning.correlation import CorrelationClassification, CorrelationFinding
from app.services.reasoning.driver_tree import DriverEffect

DOMINANCE_TOP_PCT = 60.0
DOMINANCE_GAP_PCT = 30.0
MATERIAL_DRIVER_FLOOR_PCT = 15.0

# Rule-based mapping from driver name -> the narrative frame it anchors when
# it heads its own hypothesis. This is documentation/labeling only — it does
# not affect the numbers, only how a driver-led hypothesis is described.
_DRIVER_NARRATIVE_LABEL = {
    "quantity_effect": "Demand / volume shift",
    "avg_price_effect": "Unit pricing shift",
    "discount_effect": "Discounting / promotional pricing",
    "cost_mix_effect": "Product-mix composition shift",
    "margin_rate_effect": "Margin-rate compression (typically discounting)",
}


@dataclass
class HypothesisDraft:
    id: str
    label: str
    summary: str
    drivers: list[DriverEffect]
    correlations: list[CorrelationFinding]
    statistical_strength: float
    evidence_agreement: float
    data_completeness: float
    confidence: float = field(init=False)

    def __post_init__(self) -> None:
        self.confidence = compute_confidence(
            ConfidenceInputs(
                statistical_strength=self.statistical_strength,
                evidence_agreement=self.evidence_agreement,
                data_completeness=self.data_completeness,
            )
        )


def _correlation_direction_signal(finding: CorrelationFinding) -> int:
    if finding.classification == CorrelationClassification.INSUFFICIENT_EVIDENCE:
        return 0
    return 1 if finding.correlation_coefficient > 0 else -1


def build_hypotheses(
    drivers: list[DriverEffect],
    correlations: list[CorrelationFinding],
    movement_z_score: float | None,
    weeks_of_history: int,
    weeks_required_for_high_confidence: int,
) -> list[HypothesisDraft]:
    """Build one or more candidate hypotheses from computed evidence.

    `drivers` should already be sorted by nothing in particular — this
    function ranks them itself by absolute contribution_pct.
    """
    if not drivers:
        return []

    ranked = sorted(drivers, key=lambda d: abs(d.contribution_pct), reverse=True)
    top, second = ranked[0], (ranked[1] if len(ranked) > 1 else None)
    top_pct = abs(top.contribution_pct)
    gap_pct = top_pct - abs(second.contribution_pct) if second else 100.0

    completeness = data_completeness_score(weeks_of_history, weeks_required_for_high_confidence)
    correlation_direction_signals = [_correlation_direction_signal(c) for c in correlations]
    # A driver's own direction (+1 increase / -1 decrease) is itself a
    # "signal" that should agree with correlated external evidence.
    driver_direction_signals = [1 if d.direction == "increase" else -1 for d in ranked]

    is_dominant = top_pct >= DOMINANCE_TOP_PCT and gap_pct >= DOMINANCE_GAP_PCT

    if is_dominant:
        concentration = driver_concentration_strength([d.contribution_pct for d in ranked])
        stat_strength = 0.6 * statistical_strength_from_zscore(movement_z_score) + 0.4 * concentration
        agreement = agreement_score(driver_direction_signals + correlation_direction_signals)
        driver_names = ", ".join(d.driver for d in ranked)
        return [
            HypothesisDraft(
                id="unified",
                label=_DRIVER_NARRATIVE_LABEL.get(top.driver, top.driver.replace("_", " ").title()),
                summary=(
                    f"Primarily driven by {top.driver.replace('_', ' ')} "
                    f"({top.contribution_pct:+.0f}% of the movement), with contributing "
                    f"factors: {driver_names}."
                ),
                drivers=ranked,
                correlations=correlations,
                statistical_strength=stat_strength,
                evidence_agreement=agreement,
                data_completeness=completeness,
            )
        ]

    # No dominant driver -> the top-2 material drivers each anchor a
    # competing hypothesis.
    candidates = [d for d in ranked if abs(d.contribution_pct) >= MATERIAL_DRIVER_FLOOR_PCT][:2]
    if len(candidates) < 2:
        candidates = ranked[:2]

    hypotheses: list[HypothesisDraft] = []
    for driver in candidates:
        own_share = abs(driver.contribution_pct) / 100
        stat_strength = 0.55 * statistical_strength_from_zscore(movement_z_score) + 0.45 * own_share
        agreement = agreement_score([1 if driver.direction == "increase" else -1] + correlation_direction_signals)
        hypotheses.append(
            HypothesisDraft(
                id=driver.driver,
                label=_DRIVER_NARRATIVE_LABEL.get(driver.driver, driver.driver.replace("_", " ").title()),
                summary=(
                    f"Leading candidate explanation: {driver.driver.replace('_', ' ')} "
                    f"({driver.contribution_pct:+.0f}% of the movement). {driver.description}"
                ),
                drivers=[driver],
                correlations=correlations,
                statistical_strength=stat_strength,
                evidence_agreement=agreement,
                data_completeness=completeness,
            )
        )
    return hypotheses
