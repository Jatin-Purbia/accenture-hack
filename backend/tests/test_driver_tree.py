"""Unit tests for the LMDI sales driver decomposition and the margin
mix/rate decomposition — both checked against hand-computed examples."""
from __future__ import annotations

import math

import pandas as pd
import pytest

from app.services.reasoning.driver_tree import decompose_margin_mix_and_rate, decompose_sales_drivers


def _idx(n: int) -> pd.DatetimeIndex:
    return pd.date_range("2024-01-01", periods=n, freq="W-MON")


def test_lmdi_decomposition_matches_hand_computation_quantity_and_discount_only():
    """Fixture: gross unit price held FIXED at $50 across all periods, so
    the entire ~$1300 sales drop must be explained by quantity + discount
    alone, with price_effect == 0 exactly (hand-verified below).

    Period 1-2 (baseline): 100 units, 10% discount -> $4500/wk
    Period 3 (actual):      80 units, 20% discount -> $3200
    """
    quantity = pd.Series([100.0, 100.0, 80.0], index=_idx(3))
    discount = pd.Series([0.10, 0.10, 0.20], index=_idx(3))
    sales = pd.Series([4500.0, 4500.0, 3200.0], index=_idx(3))

    effects, gap = decompose_sales_drivers(quantity, discount, sales)
    by_name = {e.driver: e for e in effects}

    assert by_name["avg_price_effect"].contribution_value == pytest.approx(0.0, abs=1e-6)
    assert by_name["quantity_effect"].contribution_value == pytest.approx(-850.877, abs=0.01)
    assert by_name["discount_effect"].contribution_value == pytest.approx(-449.123, abs=0.01)
    assert by_name["quantity_effect"].direction == "decrease"
    assert by_name["discount_effect"].direction == "decrease"

    # LMDI's defining property: contributions sum EXACTLY to the total
    # change with zero unexplained residual.
    total_delta = sales.iloc[-1] - 4500.0  # S0 reconstructed == 4500 here (Q0=G0=R0 match baseline)
    assert sum(e.contribution_value for e in effects) == pytest.approx(total_delta, abs=0.01)
    assert gap == pytest.approx(0.0, abs=1e-6)


def test_lmdi_decomposition_isolates_pure_price_change():
    """Fixture: quantity and discount held constant, gross price rises from
    $40 to $50 (+25%). The entire change must land on avg_price_effect."""
    quantity = pd.Series([100.0, 100.0, 100.0], index=_idx(3))
    discount = pd.Series([0.0, 0.0, 0.0], index=_idx(3))
    sales = pd.Series([4000.0, 4000.0, 5000.0], index=_idx(3))

    effects, _ = decompose_sales_drivers(quantity, discount, sales)
    by_name = {e.driver: e for e in effects}

    assert by_name["quantity_effect"].contribution_value == pytest.approx(0.0, abs=1e-6)
    assert by_name["discount_effect"].contribution_value == pytest.approx(0.0, abs=1e-6)
    assert by_name["avg_price_effect"].contribution_value == pytest.approx(1000.0, abs=0.01)
    assert by_name["avg_price_effect"].direction == "increase"


def test_lmdi_handles_no_change_without_division_errors():
    quantity = pd.Series([100.0, 100.0, 100.0], index=_idx(3))
    discount = pd.Series([0.1, 0.1, 0.1], index=_idx(3))
    sales = pd.Series([4500.0, 4500.0, 4500.0], index=_idx(3))
    effects, _ = decompose_sales_drivers(quantity, discount, sales)
    for e in effects:
        assert e.contribution_value == pytest.approx(0.0, abs=1e-6)


def test_margin_mix_and_rate_decomposition_sums_to_total_margin_change():
    """Two sub-categories, A (higher baseline margin) and B (lower baseline
    margin). Composition shifts entirely toward B between baseline and the
    evaluated week, with no within-sub-category margin change — the ENTIRE
    category margin change must land on cost_mix_effect, with
    margin_rate_effect == 0.
    """
    weeks = list(_idx(9))  # 8 baseline weeks + 1 evaluated week
    rows = []
    for w in weeks[:-1]:
        rows.append({"week_start": w, "sub_category": "A", "sales": 100.0, "profit": 30.0})  # 30% margin
        rows.append({"week_start": w, "sub_category": "B", "sales": 100.0, "profit": 10.0})  # 10% margin
    # Evaluated week: composition shifts fully to B (0/200 -> A, 200/200 -> B), same per-line margins
    rows.append({"week_start": weeks[-1], "sub_category": "A", "sales": 0.0, "profit": 0.0})
    rows.append({"week_start": weeks[-1], "sub_category": "B", "sales": 200.0, "profit": 20.0})  # still 10% margin
    df = pd.DataFrame(rows)

    effects = decompose_margin_mix_and_rate(df, baseline_weeks=8)
    by_name = {e.driver: e for e in effects}

    # Baseline category margin = (30+10)/(100+100) = 20%. Evaluated margin = 20/200 = 10%.
    # Total change = -10pp, entirely from composition (rate is unchanged for B).
    assert by_name["margin_rate_effect"].contribution_value == pytest.approx(0.0, abs=1e-6)
    assert by_name["cost_mix_effect"].contribution_value == pytest.approx(-10.0, abs=0.01)
    assert by_name["cost_mix_effect"].direction == "decrease"


def test_margin_decomposition_returns_empty_with_insufficient_baseline_weeks():
    df = pd.DataFrame(
        [
            {"week_start": _idx(2)[0], "sub_category": "A", "sales": 100.0, "profit": 20.0},
            {"week_start": _idx(2)[1], "sub_category": "A", "sales": 100.0, "profit": 10.0},
        ]
    )
    assert decompose_margin_mix_and_rate(df, baseline_weeks=8) == []
