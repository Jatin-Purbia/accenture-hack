"""Reasoning layer — deterministic driver-tree decomposition.

Two decomposition techniques, both exact (contributions always sum to the
total observed change — no residual "unexplained" bucket hiding a bad fit):

1. `decompose_sales_drivers` — LMDI (Log-Mean Divisia Index) decomposition of
   Sales = Quantity x Gross Unit Price x (1 - Discount). LMDI is the standard
   method (used widely in energy/economics decomposition analysis) for
   splitting a change in a MULTIPLICATIVE aggregate into additive factor
   contributions with zero residual, which is exactly the brief's
   "Sales = Quantity x Avg Price, Discount ... contribution analysis" ask.

2. `decompose_margin_mix_and_rate` — a share-based mix/rate decomposition for
   a RATIO metric (profit margin %), splitting the change into a
   "composition shifted toward higher/lower-margin sub-categories" effect
   (cost_mix_effect) and a "margin rate changed within sub-categories,
   typically via discounting" effect (margin_rate_effect).

Both reuse `anomaly.forecast_expected_value` as the baseline/"expected"
value for each underlying factor series, so the driver tree's baseline is
consistent with the same forecasting method the anomaly detector used.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

import pandas as pd

from app.services.signal.anomaly import forecast_expected_value


@dataclass
class DriverEffect:
    driver: str
    description: str
    contribution_value: float
    contribution_pct: float  # share of the TOTAL change this driver explains
    direction: str  # "increase" | "decrease"


def _lmdi_weight(v1: float, v0: float) -> float:
    """Logarithmic mean of v1, v0 — the LMDI weighting factor. Falls back to
    v1 when v1 == v0 (the logarithmic mean's limit as the ratio -> 1)."""
    if v1 == v0:
        return v1
    return (v1 - v0) / (math.log(v1) - math.log(v0))


def decompose_sales_drivers(
    quantity_series: pd.Series,
    discount_series: pd.Series,
    sales_series: pd.Series,
) -> tuple[list[DriverEffect], float]:
    """Decompose the latest-period Sales deviation into quantity, gross unit
    price, and discount contributions.

    Returns (effects, reconciliation_gap) where reconciliation_gap is the
    (typically small) difference between the driver tree's own multiplicative
    baseline (Q0 x G0 x R0) and the anomaly detector's independently-forecast
    baseline for the raw Sales series — surfaced so the evidence packet is
    honest about the two models not being forced to agree exactly.
    """
    q1 = float(quantity_series.iloc[-1])
    d1 = float(discount_series.iloc[-1])
    s1 = float(sales_series.iloc[-1])
    r1 = 1 - d1

    if q1 <= 0 or r1 <= 0:
        return [], 0.0

    gross_price_series = sales_series / (quantity_series * (1 - discount_series)).replace(0, pd.NA)
    g1 = float(gross_price_series.iloc[-1])

    q0, _, _ = forecast_expected_value(quantity_series)
    d0, _, _ = forecast_expected_value(discount_series)
    r0 = 1 - d0
    g0, _, _ = forecast_expected_value(gross_price_series.dropna())

    if q0 <= 0 or r0 <= 0 or g0 <= 0 or g1 <= 0:
        return [], 0.0

    s0_reconstructed = q0 * g0 * r0
    sales_forecast_baseline, _, _ = forecast_expected_value(sales_series)
    reconciliation_gap = s0_reconstructed - sales_forecast_baseline

    if s1 <= 0:
        return [], reconciliation_gap

    total_delta = s1 - s0_reconstructed
    weight = _lmdi_weight(s1, s0_reconstructed)

    quantity_effect = weight * math.log(q1 / q0)
    price_effect = weight * math.log(g1 / g0)
    discount_effect = weight * math.log(r1 / r0)

    def _pct(effect: float) -> float:
        return (effect / total_delta * 100) if abs(total_delta) > 1e-9 else 0.0

    effects = [
        DriverEffect(
            driver="quantity_effect",
            description=(
                f"Units sold moved from an expected {q0:,.0f} to an actual {q1:,.0f} "
                f"({(q1 / q0 - 1) * 100:+.1f}%)."
            ),
            contribution_value=quantity_effect,
            contribution_pct=_pct(quantity_effect),
            direction="increase" if quantity_effect >= 0 else "decrease",
        ),
        DriverEffect(
            driver="avg_price_effect",
            description=(
                f"Average gross unit price moved from an expected ${g0:,.2f} to "
                f"an actual ${g1:,.2f} ({(g1 / g0 - 1) * 100:+.1f}%)."
            ),
            contribution_value=price_effect,
            contribution_pct=_pct(price_effect),
            direction="increase" if price_effect >= 0 else "decrease",
        ),
        DriverEffect(
            driver="discount_effect",
            description=(
                f"Average discount rate moved from an expected {d0 * 100:.1f}% to "
                f"an actual {d1 * 100:.1f}% ({(d1 - d0) * 100:+.1f}pp)."
            ),
            contribution_value=discount_effect,
            contribution_pct=_pct(discount_effect),
            direction="increase" if discount_effect >= 0 else "decrease",
        ),
    ]
    return effects, reconciliation_gap


def decompose_margin_mix_and_rate(
    subcategory_period_df: pd.DataFrame,
    baseline_weeks: int = 8,
) -> list[DriverEffect]:
    """Decompose a category's profit-margin change into a mix effect
    (composition shifted toward higher/lower-margin sub-categories) and a
    margin-rate effect (within-sub-category margin changed, typically via
    discounting).

    `subcategory_period_df` must have columns: week_start, sub_category,
    sales, profit — i.e. ingestion.build_weekly_subcategory_mix() output
    extended with profit. The LATEST week_start is treated as the evaluated
    period; the `baseline_weeks` immediately preceding it form the baseline.
    """
    weeks = sorted(subcategory_period_df["week_start"].unique())
    if len(weeks) < baseline_weeks + 1:
        return []

    current_week = weeks[-1]
    baseline_window = weeks[-(baseline_weeks + 1):-1]

    current = subcategory_period_df[subcategory_period_df["week_start"] == current_week]
    baseline = subcategory_period_df[subcategory_period_df["week_start"].isin(baseline_window)]

    baseline_agg = baseline.groupby("sub_category").agg(sales=("sales", "sum"), profit=("profit", "sum"))
    current_agg = current.groupby("sub_category").agg(sales=("sales", "sum"), profit=("profit", "sum"))

    all_subcats = set(baseline_agg.index) | set(current_agg.index)
    baseline_total_sales = baseline_agg["sales"].sum()
    current_total_sales = current_agg["sales"].sum()
    if baseline_total_sales <= 0 or current_total_sales <= 0:
        return []

    mix_effect = 0.0
    rate_effect = 0.0
    for sc in all_subcats:
        b_sales = float(baseline_agg["sales"].get(sc, 0.0))
        b_profit = float(baseline_agg["profit"].get(sc, 0.0))
        c_sales = float(current_agg["sales"].get(sc, 0.0))
        c_profit = float(current_agg["profit"].get(sc, 0.0))

        share_b = b_sales / baseline_total_sales
        share_c = c_sales / current_total_sales
        margin_b = (b_profit / b_sales) if b_sales > 0 else 0.0
        margin_c = (c_profit / c_sales) if c_sales > 0 else margin_b

        mix_effect += (share_c - share_b) * margin_b
        rate_effect += share_c * (margin_c - margin_b)

    # Convert from fraction to percentage points to match the KPI's own units.
    mix_effect_pp = mix_effect * 100
    rate_effect_pp = rate_effect * 100
    total_pp = mix_effect_pp + rate_effect_pp

    def _pct(effect: float) -> float:
        return (effect / total_pp * 100) if abs(total_pp) > 1e-9 else 0.0

    return [
        DriverEffect(
            driver="cost_mix_effect",
            description=(
                "Sales composition shifted toward sub-categories with a different "
                "baseline margin than the category average."
            ),
            contribution_value=mix_effect_pp,
            contribution_pct=_pct(mix_effect_pp),
            direction="increase" if mix_effect_pp >= 0 else "decrease",
        ),
        DriverEffect(
            driver="margin_rate_effect",
            description=(
                "Margin rate within sub-categories changed versus baseline "
                "(commonly a discounting shift)."
            ),
            contribution_value=rate_effect_pp,
            contribution_pct=_pct(rate_effect_pp),
            direction="increase" if rate_effect_pp >= 0 else "decrease",
        ),
    ]
