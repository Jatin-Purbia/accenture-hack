"""Signal layer — deterministic anomaly / materiality detection.

Per the brief: a movement must clear BOTH a statistical bar (it falls
outside a trend+seasonality-aware forecast band) AND a business-impact
threshold (the KPI contract's materiality floor) to be flagged as material.
Neither alone is sufficient — a statistically "significant" 0.3% wobble on a
huge-base metric is not business-material, and a huge percent swing on a
near-zero base is not statistically distinguishable from noise.

Decomposition method is chosen based on how much history is available:
  - >= MIN_POINTS_FOR_STL points: STL (trend + seasonality + residual),
    robust=True to reduce sensitivity to the very anomaly we're detecting.
  - Fewer points but >= MIN_POINTS_FOR_TREND: a simple OLS linear-trend
    fallback (no seasonality term — not enough cycles to estimate one).
  - Fewer than MIN_POINTS_FOR_TREND: no reliable forecast band can be built
    at all; the function reports this explicitly (`method="insufficient_history"`)
    rather than fabricating a band from noise. This is the sparse-history
    path exercised by the emerging-sub-category demo scenario.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
from statsmodels.tsa.seasonal import STL

from app.models.kpi import MaterialityThresholds

MIN_POINTS_FOR_STL = 24  # need at least ~2 quarterly cycles for a stable STL fit
MIN_POINTS_FOR_TREND = 6
DEFAULT_SEASONAL_PERIOD = 13  # quarterly-ish cycle at weekly grain; see docstring
BAND_Z = 1.96  # ~95% forecast band


class AnomalyMethod:
    STL_DECOMPOSITION = "stl_trend_seasonality_decomposition"
    LINEAR_TREND = "linear_trend_fallback"
    INSUFFICIENT_HISTORY = "insufficient_history"


@dataclass
class AnomalyResult:
    period_start: pd.Timestamp
    period_end: pd.Timestamp
    actual_value: float
    expected_value: float
    band_low: float
    band_high: float
    absolute_change: float
    relative_change_pct: float
    z_score: float | None
    is_statistically_unusual: bool
    is_material: bool
    method: str
    data_points_used: int
    weeks_of_history: int


def forecast_expected_value(series: pd.Series) -> tuple[float, float, str]:
    """Return (expected_value_for_last_point, residual_std, method) using the
    richest method the available history supports.

    Critically, the point being evaluated (the LAST point in `series`) is
    excluded from every fit below — this must be a genuine one-step-ahead
    forecast, not an in-sample smooth that includes the very point we're
    testing (which would let a real anomaly leak into its own baseline and
    silently shrink the deviation we're trying to detect).
    """
    n = len(series)
    values = series.to_numpy(dtype=float)
    history = series.iloc[:-1]  # excludes the point under test
    n_prior = len(history)

    if n_prior >= MIN_POINTS_FOR_STL:
        period = min(DEFAULT_SEASONAL_PERIOD, n_prior // 2)
        try:
            stl = STL(history, period=period, robust=True).fit()
            resid_std = float(np.std(stl.resid.to_numpy()))
            trend = stl.trend.to_numpy()
            seasonal = stl.seasonal.to_numpy()

            # One-step-ahead trend extrapolation: robust linear slope over
            # the trailing window of the trend component (not just the last
            # two points, which would be noise-sensitive).
            tail = min(8, n_prior - 1)
            trend_slope = float(np.polyfit(np.arange(tail + 1), trend[-(tail + 1):], 1)[0])
            trend_next = trend[-1] + trend_slope

            # STL seasonal is periodic with period `period`; the seasonal
            # value one step ahead repeats the value from exactly one full
            # cycle back.
            seasonal_next = seasonal[-period] if n_prior >= period else seasonal[-1]

            expected = float(trend_next + seasonal_next)
            return expected, resid_std, AnomalyMethod.STL_DECOMPOSITION
        except Exception:
            pass  # fall through to linear trend

    if n >= MIN_POINTS_FOR_TREND:
        x = np.arange(n - 1)
        y = values[:-1]
        slope, intercept = np.polyfit(x, y, 1)
        fitted = slope * x + intercept
        resid_std = float(np.std(y - fitted))
        expected = float(slope * (n - 1) + intercept)
        return expected, resid_std, AnomalyMethod.LINEAR_TREND

    return float(values[:-1].mean()) if n > 1 else float(values[0]), 0.0, AnomalyMethod.INSUFFICIENT_HISTORY


def _clears_materiality(
    absolute_change: float, relative_change_pct: float, materiality: MaterialityThresholds
) -> bool:
    abs_floor = (
        materiality.min_absolute_change_usd
        or materiality.min_absolute_change_pp
        or materiality.min_absolute_change_count
        or materiality.min_absolute_change
        or 0.0
    )
    return abs(absolute_change) >= abs_floor and abs(relative_change_pct) >= materiality.min_relative_change_pct


def detect_anomaly(
    series: pd.Series,
    materiality: MaterialityThresholds,
) -> AnomalyResult:
    """`series` must be indexed by week_start (ascending), values = KPI value.
    Evaluates the LAST point in the series against a band fit from the rest.
    """
    if len(series) < 2:
        raise ValueError("Need at least 2 observations to evaluate an anomaly")

    series = series.sort_index()
    actual = float(series.iloc[-1])
    period_start = series.index[-1]
    # Weekly grain: period covers 7 days from week_start
    period_end = period_start + pd.Timedelta(days=6)

    expected, resid_std, method = forecast_expected_value(series)

    if method == AnomalyMethod.INSUFFICIENT_HISTORY:
        band_low = band_high = expected
        z_score = None
        is_unusual = False
    else:
        band_low = expected - BAND_Z * resid_std
        band_high = expected + BAND_Z * resid_std
        # A near-zero residual std (a genuinely flat or near-flat series)
        # makes both the z-score AND the band comparison numerically
        # meaningless — floating-point noise on the order of 1e-12 would
        # otherwise get compared against an equally microscopic band width
        # and spuriously flagged "unusual". Below this floor we make no
        # statistical claim at all (materiality's absolute floor still
        # applies via is_material below).
        if resid_std <= 1e-9:
            z_score = None
            is_unusual = False
        else:
            z_score = (actual - expected) / resid_std
            is_unusual = actual < band_low or actual > band_high

    absolute_change = actual - expected
    relative_change_pct = (absolute_change / expected * 100) if abs(expected) > 1e-9 else 0.0

    is_material = is_unusual and _clears_materiality(absolute_change, relative_change_pct, materiality)

    return AnomalyResult(
        period_start=period_start,
        period_end=period_end,
        actual_value=actual,
        expected_value=expected,
        band_low=band_low,
        band_high=band_high,
        absolute_change=absolute_change,
        relative_change_pct=relative_change_pct,
        z_score=z_score,
        is_statistically_unusual=is_unusual,
        is_material=is_material,
        method=method,
        data_points_used=len(series) - 1,
        weeks_of_history=len(series),
    )


def series_with_forecast_band(series: pd.Series, materiality: MaterialityThresholds) -> pd.DataFrame:
    """Evaluate every point from MIN_POINTS_FOR_TREND onward against a band
    fit from all *prior* points — used to render the full trend+band chart
    in the UI, not just the latest-period anomaly check."""
    series = series.sort_index()
    rows = []
    for i in range(MIN_POINTS_FOR_TREND, len(series) + 1):
        window = series.iloc[:i]
        result = detect_anomaly(window, materiality)
        rows.append(
            {
                "week_start": result.period_start,
                "actual": result.actual_value,
                "expected": result.expected_value,
                "band_low": result.band_low,
                "band_high": result.band_high,
                "is_material": result.is_material,
                "method": result.method,
            }
        )
    return pd.DataFrame(rows)
