"""Unit tests for the deterministic Signal-layer anomaly detector.

These use hand-constructed synthetic series with KNOWN properties (not the
project's placeholder Kaggle-shaped data) so each assertion checks a
specific, understandable edge case.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from app.models.kpi import MaterialityThresholds
from app.services.signal.anomaly import AnomalyMethod, detect_anomaly


def _weekly_index(n: int, start: str = "2024-01-01") -> pd.DatetimeIndex:
    return pd.date_range(start=start, periods=n, freq="W-MON")


LOOSE_MATERIALITY = MaterialityThresholds(min_absolute_change_usd=1.0, min_relative_change_pct=1.0)
STRICT_MATERIALITY = MaterialityThresholds(min_absolute_change_usd=100_000.0, min_relative_change_pct=50.0)


def test_flat_series_no_anomaly():
    """A perfectly flat series should never flag its own next point as unusual."""
    values = [1000.0] * 30
    series = pd.Series(values, index=_weekly_index(30))
    result = detect_anomaly(series, LOOSE_MATERIALITY)
    assert not result.is_statistically_unusual
    assert not result.is_material


def test_sudden_drop_is_flagged_material_with_loose_materiality():
    """A sharp, sustained level break after stable history must be flagged."""
    rng = np.random.default_rng(0)
    stable = 1000 + rng.normal(0, 10, size=29)
    dropped = np.append(stable, 400.0)  # 60% drop on the final week
    series = pd.Series(dropped, index=_weekly_index(30))
    result = detect_anomaly(series, LOOSE_MATERIALITY)
    assert result.is_statistically_unusual
    assert result.is_material
    assert result.actual_value == pytest.approx(400.0)
    assert result.relative_change_pct < -30


def test_statistically_unusual_but_not_business_material():
    """A movement outside the forecast band that fails the business-impact
    floor must NOT be flagged material — this is the brief's explicit
    requirement that statistical significance alone is insufficient."""
    rng = np.random.default_rng(1)
    stable = 100 + rng.normal(0, 1, size=29)  # tiny absolute scale
    bumped = np.append(stable, 130.0)  # statistically unusual at this scale
    series = pd.Series(bumped, index=_weekly_index(30))
    result = detect_anomaly(series, STRICT_MATERIALITY)
    assert result.is_statistically_unusual  # clears the statistical bar
    assert not result.is_material  # but fails the $100k / 50% business floor


def test_insufficient_history_uses_documented_fallback_method():
    """Fewer than MIN_POINTS_FOR_TREND points must not fabricate a
    confident forecast band — it should be flagged as insufficient history."""
    series = pd.Series([500.0, 520.0, 510.0], index=_weekly_index(3))
    result = detect_anomaly(series, LOOSE_MATERIALITY)
    assert result.method == AnomalyMethod.INSUFFICIENT_HISTORY
    assert not result.is_statistically_unusual
    assert result.weeks_of_history == 3


def test_forecast_does_not_leak_the_tested_point_into_its_own_baseline():
    """Regression test for a real bug caught during development: the
    expected-value fit must exclude the point being evaluated. If it
    leaked in, a sustained anomaly would partially "explain itself away"
    even on the FIRST anomalous point, which should not happen here since
    all prior history is genuinely flat."""
    rng = np.random.default_rng(2)
    stable = 1000 + rng.normal(0, 5, size=39)
    dropped = np.append(stable, 500.0)
    series = pd.Series(dropped, index=_weekly_index(40))
    result = detect_anomaly(series, LOOSE_MATERIALITY)
    # If the last point leaked into the baseline fit, expected_value would
    # be pulled toward 500 and the deviation would be understated well
    # below the true ~50% drop.
    assert result.relative_change_pct < -35


def test_requires_at_least_two_points():
    with pytest.raises(ValueError):
        detect_anomaly(pd.Series([100.0], index=_weekly_index(1)), LOOSE_MATERIALITY)


def test_materiality_requires_both_absolute_and_relative_floor():
    """A huge relative swing on a near-zero base must not be material if the
    absolute dollar floor isn't cleared (and vice versa)."""
    materiality = MaterialityThresholds(min_absolute_change_usd=5000.0, min_relative_change_pct=5.0)
    # Large relative change (300%), tiny absolute change ($6) -> not material
    series = pd.Series([2.0] * 29 + [8.0], index=_weekly_index(30))
    result = detect_anomaly(series, materiality)
    assert result.relative_change_pct > 100
    assert not result.is_material
