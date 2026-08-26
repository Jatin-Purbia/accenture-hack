"""Data layer: raw file discovery, schema normalization, type cleaning, and
weekly aggregation. Everything here is deterministic pandas/NumPy — no
statistics beyond simple sums/means, no ML, no LLM calls.

File discovery is pattern-based (not a hardcoded exact filename) because the
real Kaggle download's filename varies by mirror (e.g. "train.csv",
"Sample - Superstore.csv", "customer_support_tickets.csv"). We look for the
placeholder files this repo ships with data/raw/, or the first CSV whose
name loosely matches a keyword, and fail with a specific, actionable error
if nothing matches.
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd

from app.core.logging import get_logger
from app.services.data.schema_normalization import (
    normalize_superstore,
    normalize_support_tickets,
)

logger = get_logger(__name__)


class RawDataNotFoundError(FileNotFoundError):
    pass


def _find_raw_file(raw_dir: Path, keywords: list[str], dataset_label: str) -> Path:
    if not raw_dir.exists():
        raise RawDataNotFoundError(
            f"Raw data directory {raw_dir} does not exist. Expected the "
            f"{dataset_label} CSV to live there — see README.md 'Data provenance'."
        )
    csvs = list(raw_dir.glob("*.csv"))
    if not csvs:
        raise RawDataNotFoundError(
            f"No CSV files found in {raw_dir}. Expected a {dataset_label} export "
            f"(e.g. downloaded via the Kaggle CLI, or the placeholder generator "
            f"in backend/scripts/generate_sample_data.py) — see README.md 'Data provenance'."
        )
    for csv_path in csvs:
        name_lower = csv_path.name.lower()
        if any(kw in name_lower for kw in keywords):
            return csv_path
    raise RawDataNotFoundError(
        f"Found {len(csvs)} CSV(s) in {raw_dir} ({[c.name for c in csvs]}) but none "
        f"matched expected {dataset_label} filename keywords {keywords}. Rename the "
        f"file or add a keyword to ingestion.py's _find_raw_file call."
    )


def load_raw_superstore(raw_dir: Path) -> pd.DataFrame:
    path = _find_raw_file(raw_dir, ["superstore", "sales", "sample"], "Superstore sales")
    logger.info("loading_superstore_raw", path=str(path))
    df = pd.read_csv(path, encoding="latin-1")
    normalized, mapping = normalize_superstore(df)
    logger.info("superstore_schema_matched", mapping=mapping)

    normalized["order_date"] = pd.to_datetime(normalized["order_date"], errors="raise")
    for col in ("sales", "quantity", "discount", "profit"):
        normalized[col] = pd.to_numeric(normalized[col], errors="coerce")
    before = len(normalized)
    normalized = normalized.dropna(subset=["order_date", "sales", "quantity", "discount", "profit"])
    dropped = before - len(normalized)
    if dropped:
        logger.warning("superstore_rows_dropped_invalid", dropped=dropped)

    normalized["week_start"] = (
        normalized["order_date"].dt.to_period("W-SUN").apply(lambda p: p.start_time)
    )
    return normalized


def load_raw_support_tickets(raw_dir: Path) -> pd.DataFrame:
    path = _find_raw_file(raw_dir, ["ticket", "support"], "customer support tickets")
    logger.info("loading_tickets_raw", path=str(path))
    df = pd.read_csv(path, encoding="latin-1")
    normalized, mapping = normalize_support_tickets(df)
    logger.info("ticket_schema_matched", mapping=mapping)

    normalized["created_date"] = pd.to_datetime(normalized["created_date"], errors="coerce")
    before = len(normalized)
    normalized = normalized.dropna(subset=["created_date"])
    dropped = before - len(normalized)
    if dropped:
        logger.warning("ticket_rows_dropped_invalid_date", dropped=dropped)

    normalized["ticket_subject"] = normalized["ticket_subject"].fillna("")
    normalized["ticket_description"] = normalized["ticket_description"].fillna("")
    normalized["full_text"] = (
        normalized["ticket_subject"] + ". " + normalized["ticket_description"]
    )
    normalized["week_start"] = (
        normalized["created_date"].dt.to_period("W-SUN").apply(lambda p: p.start_time)
    )
    return normalized


# ---------------------------------------------------------------------------
# Weekly aggregations (pure deterministic reshaping — one function per KPI)
# ---------------------------------------------------------------------------


def build_weekly_region_sales(
    df: pd.DataFrame,
    region: str | None = None,
    sub_category: str | None = None,
) -> pd.DataFrame:
    """Weekly Sales by Region — supports an optional sub_category filter,
    used for the emerging-sub-category (sparse-history) scenario."""
    working = df
    if region is not None:
        working = working[working["region"] == region]
    if sub_category is not None:
        working = working[working["sub_category"] == sub_category]

    grouped = (
        working.groupby(["week_start", "region"])
        .agg(
            sales=("sales", "sum"),
            quantity=("quantity", "sum"),
            discount=("discount", "mean"),
            profit=("profit", "sum"),
            order_lines=("sales", "count"),
        )
        .reset_index()
        .sort_values(["region", "week_start"])
    )
    grouped["avg_unit_price"] = grouped["sales"] / grouped["quantity"].replace(0, pd.NA)
    return grouped


def build_weekly_category_margin(df: pd.DataFrame, region: str | None = None) -> pd.DataFrame:
    """Weekly Profit Margin by Category — derived/aggregated grain."""
    working = df if region is None else df[df["region"] == region]
    grouped = (
        working.groupby(["week_start", "category"])
        .agg(
            sales=("sales", "sum"),
            profit=("profit", "sum"),
            discount=("discount", "mean"),
            quantity=("quantity", "sum"),
        )
        .reset_index()
        .sort_values(["category", "week_start"])
    )
    grouped["profit_margin_pct"] = (grouped["profit"] / grouped["sales"].replace(0, pd.NA)) * 100
    return grouped


def build_weekly_subcategory_mix(df: pd.DataFrame, category: str, region: str | None = None) -> pd.DataFrame:
    """Weekly sales split by sub-category within a category — used by the
    driver-tree's mix-effect calculation."""
    working = df[df["category"] == category]
    if region is not None:
        working = working[working["region"] == region]
    grouped = (
        working.groupby(["week_start", "sub_category"])
        .agg(sales=("sales", "sum"), quantity=("quantity", "sum"), profit=("profit", "sum"))
        .reset_index()
    )
    return grouped
