"""Reasoning layer — lag-aware correlation between a KPI movement and an
independent signal series (ticket volume / sentiment), with a lightweight
causal-inference check.

The brief requires labeling findings "correlated" vs "causally supported"
based on whether a natural control/comparison group exists. This module
implements that literally: since support tickets have no region field, a
ticket-sentiment signal can only be linked to a KPI movement in a specific
region by *inference*, not a join key. We treat the OTHER regions in the
same category as a natural quasi-control group (a simple difference-in-
differences intuition, not a randomized experiment):

  - If the treated region/category shows both the KPI movement AND a
    distinctive version of the signal that other regions in the same
    category do NOT show to the same degree, that's stronger (but still not
    proof-positive) evidence the signal is specific to what happened there
    -> classified "causally_supported" (with the caveat spelled out in the
    rationale that this is quasi-experimental, not a randomized trial).
  - If the signal moves similarly across ALL regions in the category (i.e.
    it's a category-wide phenomenon, not one this region experienced
    distinctly), the movement and the signal are still related in time but
    the region-specific attribution is not supported -> "correlated" only.
  - If there isn't enough history to compute a stable correlation at all,
    or the correlation is weak/non-significant -> "insufficient_evidence".
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
from scipy import stats as scipy_stats

MIN_POINTS_FOR_CORRELATION = 10
SIGNIFICANCE_ALPHA = 0.10
MIN_ABS_CORRELATION = 0.35


class CorrelationClassification:
    CAUSALLY_SUPPORTED = "causally_supported"
    CORRELATED = "correlated"
    INSUFFICIENT_EVIDENCE = "insufficient_evidence"


@dataclass
class CorrelationFinding:
    signal_name: str
    lag_weeks: int
    correlation_coefficient: float
    p_value: float
    classification: str
    rationale: str


def _best_lag_correlation(
    kpi_series: pd.Series, signal_series: pd.Series, max_lag: int
) -> tuple[int, float, float]:
    """Try lags 0..max_lag (signal LEADS the kpi by `lag` weeks) and return
    the lag with the strongest absolute correlation.

    Both series are first-differenced (week-over-week change) before
    correlating. We care about whether MOVEMENTS in the signal line up with
    MOVEMENTS in the KPI — correlating raw levels would let shared trend or
    seasonality (both series drifting upward over two years, say) produce a
    spurious high correlation that has nothing to do with the actual
    co-movement we're testing for.
    """
    best = (0, 0.0, 1.0)
    aligned = pd.DataFrame({"kpi": kpi_series, "signal": signal_series}).dropna()
    kpi_diff = aligned["kpi"].diff()
    signal_diff = aligned["signal"].diff()
    for lag in range(0, max_lag + 1):
        shifted_signal = signal_diff.shift(lag)
        paired = pd.DataFrame({"kpi": kpi_diff, "signal": shifted_signal}).dropna()
        if len(paired) < MIN_POINTS_FOR_CORRELATION:
            continue
        if paired["kpi"].std() < 1e-9 or paired["signal"].std() < 1e-9:
            continue
        corr, p_value = scipy_stats.pearsonr(paired["kpi"], paired["signal"])
        if abs(corr) > abs(best[1]):
            best = (lag, float(corr), float(p_value))
    return best


def evaluate_lag_correlation(
    kpi_series: pd.Series,
    signal_series: pd.Series,
    signal_name: str,
    control_kpi_series: list[pd.Series] | None = None,
    max_lag: int = 4,
    lookback_weeks: int = 26,
) -> CorrelationFinding:
    """kpi_series / signal_series indexed by week_start, ascending.

    `control_kpi_series` is an optional list of the SAME KPI computed for
    comparison slices that were NOT plausibly affected (e.g. other regions'
    weekly sales, when `signal_series` is a category-level ticket signal
    that has no region field of its own and is therefore identical across
    regions). We test the SAME signal against each control KPI series to see
    whether the signal-KPI relationship is specific to the treated slice or
    a shared/category-wide pattern. Pass None (e.g. no comparison slice
    exists) to get an honest "insufficient_evidence"/"correlated" ceiling
    rather than a fabricated causal claim.

    `lookback_weeks` restricts the correlation test to the most recent N
    weeks rather than the entire available history. This is deliberate: we
    are asking "did this signal recently start moving with this KPI?", not
    "has this signal been correlated with this KPI on average across the
    last two years?" — a brief real co-movement gets diluted into
    insignificance by a long history of unrelated noise if evaluated over
    the full window.
    """
    kpi_series = kpi_series.tail(lookback_weeks)
    signal_series = signal_series.tail(lookback_weeks)
    if control_kpi_series:
        control_kpi_series = [s.tail(lookback_weeks) for s in control_kpi_series]

    if len(kpi_series.dropna()) < MIN_POINTS_FOR_CORRELATION or len(signal_series.dropna()) < MIN_POINTS_FOR_CORRELATION:
        return CorrelationFinding(
            signal_name=signal_name,
            lag_weeks=0,
            correlation_coefficient=0.0,
            p_value=1.0,
            classification=CorrelationClassification.INSUFFICIENT_EVIDENCE,
            rationale=(
                f"Fewer than {MIN_POINTS_FOR_CORRELATION} overlapping weeks of history "
                f"available for '{signal_name}' — too little data for a reliable "
                f"correlation test."
            ),
        )

    lag, corr, p_value = _best_lag_correlation(kpi_series, signal_series, max_lag)

    if abs(corr) < MIN_ABS_CORRELATION or p_value > SIGNIFICANCE_ALPHA:
        return CorrelationFinding(
            signal_name=signal_name,
            lag_weeks=lag,
            correlation_coefficient=corr,
            p_value=p_value,
            classification=CorrelationClassification.INSUFFICIENT_EVIDENCE,
            rationale=(
                f"Best lag correlation with '{signal_name}' at {lag} week(s) lead was "
                f"r={corr:.2f}, p={p_value:.2f} — below the r >= {MIN_ABS_CORRELATION} "
                f"and p <= {SIGNIFICANCE_ALPHA} bar used to treat a relationship as evidence."
            ),
        )

    if not control_kpi_series:
        return CorrelationFinding(
            signal_name=signal_name,
            lag_weeks=lag,
            correlation_coefficient=corr,
            p_value=p_value,
            classification=CorrelationClassification.CORRELATED,
            rationale=(
                f"'{signal_name}' correlates with the KPI (r={corr:.2f}, p={p_value:.2f}) at "
                f"a {lag}-week lead, but no comparison group was available to test whether "
                f"this relationship is specific to this slice — labeled correlated, not causal."
            ),
        )

    # Quasi-control comparison: does the SAME signal correlate similarly
    # with a comparison slice's KPI (e.g. another region's sales)? If yes,
    # it's likely a shared/global confound (e.g. category-wide sentiment or
    # seasonality) rather than something specific to the treated slice.
    control_corrs = []
    for control_kpi in control_kpi_series:
        _, c_corr, c_p = _best_lag_correlation(control_kpi, signal_series, max_lag)
        control_corrs.append(c_corr)

    max_control_corr = max((abs(c) for c in control_corrs), default=0.0)

    if max_control_corr >= abs(corr) * 0.7:
        return CorrelationFinding(
            signal_name=signal_name,
            lag_weeks=lag,
            correlation_coefficient=corr,
            p_value=p_value,
            classification=CorrelationClassification.CORRELATED,
            rationale=(
                f"'{signal_name}' correlates with the KPI (r={corr:.2f}, p={p_value:.2f}), "
                f"but the comparison group shows a similarly strong relationship "
                f"(max |r|={max_control_corr:.2f}) — this looks like a shared/category-wide "
                f"pattern rather than something distinct to this slice, so it is labeled "
                f"correlated, not causally supported."
            ),
        )

    return CorrelationFinding(
        signal_name=signal_name,
        lag_weeks=lag,
        correlation_coefficient=corr,
        p_value=p_value,
        classification=CorrelationClassification.CAUSALLY_SUPPORTED,
        rationale=(
            f"'{signal_name}' correlates with the KPI (r={corr:.2f}, p={p_value:.2f}) at a "
            f"{lag}-week lead, AND the comparison group does not show the same relationship "
            f"(max |r|={max_control_corr:.2f}) — consistent with (though not proof of) an "
            f"effect specific to this slice. This is a quasi-experimental comparison, not a "
            f"randomized trial, so 'causally supported' here means 'the evidence is "
            f"consistent with causality', not 'causality is proven'."
        ),
    )
