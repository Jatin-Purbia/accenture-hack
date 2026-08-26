"""Generic, fuzzy schema normalization.

Kaggle mirrors of "Superstore" and "customer support ticket" datasets vary in
exact header naming (e.g. "Order Date" vs "order_date" vs "OrderDate", or
"Ticket Description" vs "Body" vs "Description"). Rather than hardcoding one
mirror's exact column names, this module matches columns to a set of
*expected business concepts* using case/punctuation-insensitive exact and
substring matching, with a small alias table per concept covering the known
mirrors. If a REQUIRED concept cannot be matched, it fails loudly and
specifically (naming the missing concept), instead of silently proceeding
with missing/misaligned data — a corrupted KPI computed from a
misidentified column is worse than a startup error.
"""
from __future__ import annotations

import difflib
import re
from dataclasses import dataclass

import pandas as pd


def _canonical(s: str) -> str:
    """Lowercase, strip punctuation/whitespace for robust comparison."""
    return re.sub(r"[^a-z0-9]", "", s.lower())


@dataclass(frozen=True)
class ConceptSpec:
    concept: str
    aliases: tuple[str, ...]
    required: bool = True


class SchemaNormalizationError(ValueError):
    """Raised when a required business concept cannot be matched to any column."""


def _best_match(canonical_aliases: list[str], canonical_columns: dict[str, str]) -> str | None:
    """Return the *original* column name best matching any alias, or None.

    Tries exact canonical match first, then substring containment, then a
    fuzzy ratio cutoff as a last resort (handles typos / minor renames).
    """
    # 1. Exact canonical match
    for alias in canonical_aliases:
        if alias in canonical_columns:
            return canonical_columns[alias]

    # 2. Substring containment either direction
    for alias in canonical_aliases:
        for canon_col, original in canonical_columns.items():
            if alias in canon_col or canon_col in alias:
                return original

    # 3. Fuzzy ratio fallback
    best_ratio = 0.0
    best_original: str | None = None
    for alias in canonical_aliases:
        for canon_col, original in canonical_columns.items():
            ratio = difflib.SequenceMatcher(None, alias, canon_col).ratio()
            if ratio > best_ratio:
                best_ratio = ratio
                best_original = original
    if best_ratio >= 0.82:
        return best_original
    return None


def match_schema(
    df: pd.DataFrame,
    concepts: list[ConceptSpec],
    dataset_name: str,
) -> dict[str, str]:
    """Return a mapping of {concept_name: original_column_name}.

    Raises SchemaNormalizationError naming the specific concept(s) that could
    not be matched if any REQUIRED concept has no match.
    """
    canonical_columns = {_canonical(c): c for c in df.columns}

    mapping: dict[str, str] = {}
    unmatched_required: list[str] = []

    for spec in concepts:
        canonical_aliases = [_canonical(a) for a in spec.aliases]
        match = _best_match(canonical_aliases, canonical_columns)
        if match is not None:
            mapping[spec.concept] = match
        elif spec.required:
            unmatched_required.append(spec.concept)

    if unmatched_required:
        raise SchemaNormalizationError(
            f"Could not match required concept(s) {unmatched_required} while "
            f"normalizing dataset '{dataset_name}'. Available columns were: "
            f"{list(df.columns)}. Update the alias table in "
            f"schema_normalization.py if this is a new Kaggle mirror with "
            f"different header names."
        )
    return mapping


def apply_mapping(df: pd.DataFrame, mapping: dict[str, str]) -> pd.DataFrame:
    """Rename matched columns to their canonical concept name, drop the rest
    only where explicitly requested by the caller — here we keep all original
    columns *plus* canonical aliases so nothing already-consumable is lost."""
    rename = {original: concept for concept, original in mapping.items()}
    out = df.rename(columns=rename)
    return out


# ---------------------------------------------------------------------------
# Concept tables for the two datasets used in this project
# ---------------------------------------------------------------------------

SUPERSTORE_CONCEPTS: list[ConceptSpec] = [
    ConceptSpec("order_id", ("order id", "orderid")),
    ConceptSpec("order_date", ("order date", "orderdate", "date of order")),
    ConceptSpec("ship_date", ("ship date", "shipdate"), required=False),
    ConceptSpec("ship_mode", ("ship mode", "shipmode"), required=False),
    ConceptSpec("customer_id", ("customer id", "customerid"), required=False),
    ConceptSpec("customer_name", ("customer name", "customername"), required=False),
    ConceptSpec("segment", ("segment",)),
    ConceptSpec("region", ("region",)),
    ConceptSpec("state", ("state",), required=False),
    ConceptSpec("city", ("city",), required=False),
    ConceptSpec("category", ("category",)),
    ConceptSpec("sub_category", ("sub-category", "subcategory", "sub category")),
    ConceptSpec("product_name", ("product name", "productname"), required=False),
    ConceptSpec("sales", ("sales", "revenue")),
    ConceptSpec("quantity", ("quantity", "qty")),
    ConceptSpec("discount", ("discount",)),
    ConceptSpec("profit", ("profit",)),
]

SUPPORT_TICKET_CONCEPTS: list[ConceptSpec] = [
    ConceptSpec("ticket_id", ("ticket id", "ticketid", "id")),
    ConceptSpec(
        "ticket_subject",
        ("ticket subject", "subject", "title"),
    ),
    ConceptSpec(
        "ticket_description",
        ("ticket description", "description", "body", "ticket body", "text"),
    ),
    ConceptSpec(
        "product",
        ("product purchased", "product", "productpurchased", "category"),
    ),
    ConceptSpec(
        "created_date",
        ("date of purchase", "created date", "createddate", "ticket created", "date"),
    ),
    ConceptSpec(
        "priority",
        ("ticket priority", "priority"),
        required=False,
    ),
    ConceptSpec(
        "status",
        ("ticket status", "status"),
        required=False,
    ),
    ConceptSpec(
        "satisfaction_rating",
        ("customer satisfaction rating", "satisfaction rating", "csat"),
        required=False,
    ),
    ConceptSpec("customer_id", ("customer id", "customerid", "customer email"), required=False),
]


def normalize_superstore(df: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, str]]:
    mapping = match_schema(df, SUPERSTORE_CONCEPTS, dataset_name="superstore_sales")
    return apply_mapping(df, mapping), mapping


def normalize_support_tickets(df: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, str]]:
    mapping = match_schema(df, SUPPORT_TICKET_CONCEPTS, dataset_name="support_tickets")
    return apply_mapping(df, mapping), mapping
