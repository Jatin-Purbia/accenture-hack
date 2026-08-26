"""Unit tests for the lag-correlation + causal-vs-correlated classifier."""
from __future__ import annotations

import numpy as np
import pandas as pd

from app.services.reasoning.correlation import CorrelationClassification, evaluate_lag_correlation


def _idx(n: int) -> pd.DatetimeIndex:
    return pd.date_range("2024-01-01", periods=n, freq="W-MON")


def test_insufficient_evidence_with_too_few_points():
    kpi = pd.Series([1.0, 2.0, 3.0], index=_idx(3))
    signal = pd.Series([1.0, 2.0, 3.0], index=_idx(3))
    finding = evaluate_lag_correlation(kpi, signal, "test_signal")
    assert finding.classification == CorrelationClassification.INSUFFICIENT_EVIDENCE


def test_weak_correlation_classified_insufficient_evidence():
    rng = np.random.default_rng(42)
    kpi = pd.Series(rng.normal(0, 1, 30).cumsum(), index=_idx(30))
    signal = pd.Series(rng.normal(0, 1, 30).cumsum(), index=_idx(30))  # unrelated random walk
    finding = evaluate_lag_correlation(kpi, signal, "unrelated_signal", lookback_weeks=30)
    assert finding.classification == CorrelationClassification.INSUFFICIENT_EVIDENCE


def test_strong_relationship_with_no_control_group_is_correlated_not_causal():
    """Without a comparison group, even a strong, clean relationship must be
    labeled 'correlated', never 'causally_supported' — the brief requires
    the causal label to depend on whether a control group was available."""
    n = 20
    kpi_changes = np.array([((-1) ** i) * (i % 5 + 1) for i in range(n)], dtype=float)
    signal_changes = kpi_changes * 2.0  # perfectly linearly related, same direction
    kpi = pd.Series(np.cumsum(kpi_changes), index=_idx(n))
    signal = pd.Series(np.cumsum(signal_changes), index=_idx(n))

    finding = evaluate_lag_correlation(kpi, signal, "strong_signal", control_kpi_series=None, lookback_weeks=n)
    assert abs(finding.correlation_coefficient) >= 0.35
    assert finding.classification == CorrelationClassification.CORRELATED


def test_relationship_present_in_control_group_stays_correlated():
    """If a comparison slice's KPI shows the SAME relationship with the
    signal, the movement is not distinctively tied to the treated slice —
    must stay 'correlated', not be promoted to 'causally_supported'."""
    n = 20
    rng = np.random.default_rng(1)
    signal_changes = rng.normal(0, 1, n)
    signal = pd.Series(np.cumsum(signal_changes), index=_idx(n))

    # Both the treated and control KPI move with the same signal similarly.
    treated_kpi = pd.Series(np.cumsum(signal_changes * 3 + rng.normal(0, 0.1, n)), index=_idx(n))
    control_kpi = pd.Series(np.cumsum(signal_changes * 3 + rng.normal(0, 0.1, n)), index=_idx(n))

    finding = evaluate_lag_correlation(
        treated_kpi, signal, "shared_signal", control_kpi_series=[control_kpi], lookback_weeks=n
    )
    assert finding.classification == CorrelationClassification.CORRELATED


def test_relationship_absent_in_control_group_is_causally_supported():
    """If the comparison slice does NOT show the relationship, the evidence
    is consistent with an effect specific to the treated slice."""
    n = 20
    rng = np.random.default_rng(7)
    signal_changes = rng.normal(0, 1, n)
    signal = pd.Series(np.cumsum(signal_changes), index=_idx(n))

    treated_kpi = pd.Series(np.cumsum(signal_changes * 3 + rng.normal(0, 0.1, n)), index=_idx(n))
    control_kpi = pd.Series(np.cumsum(rng.normal(0, 1, n)), index=_idx(n))  # unrelated to signal

    finding = evaluate_lag_correlation(
        treated_kpi, signal, "specific_signal", control_kpi_series=[control_kpi], lookback_weeks=n
    )
    assert finding.classification == CorrelationClassification.CAUSALLY_SUPPORTED
