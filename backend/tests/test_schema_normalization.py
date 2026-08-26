"""Unit tests for fuzzy schema normalization — this must correctly handle
header-naming variation across Kaggle mirrors and fail loudly (naming the
specific missing concept) when a required concept truly cannot be matched."""
from __future__ import annotations

import pandas as pd
import pytest

from app.services.data.schema_normalization import (
    ConceptSpec,
    SchemaNormalizationError,
    match_schema,
    normalize_superstore,
    normalize_support_tickets,
)


def test_normalize_superstore_matches_canonical_headers():
    df = pd.DataFrame(
        {
            "Order ID": ["1"], "Order Date": ["01/01/2024"], "Region": ["West"],
            "Segment": ["Consumer"], "Category": ["Technology"], "Sub-Category": ["Phones"],
            "Sales": [100.0], "Quantity": [1], "Discount": [0.1], "Profit": [10.0],
        }
    )
    normalized, mapping = normalize_superstore(df)
    assert mapping["sales"] == "Sales"
    assert mapping["sub_category"] == "Sub-Category"
    assert "sales" in normalized.columns
    assert "sub_category" in normalized.columns


def test_normalize_superstore_matches_alternate_mirror_headers():
    """A different mirror using snake_case / reordered words must still match."""
    df = pd.DataFrame(
        {
            "order_id": ["1"], "order_date": ["01/01/2024"], "region": ["West"],
            "segment": ["Consumer"], "category": ["Technology"], "subcategory": ["Phones"],
            "sales": [100.0], "qty": [1], "discount": [0.1], "profit": [10.0],
        }
    )
    normalized, mapping = normalize_superstore(df)
    assert mapping["quantity"] == "qty"
    assert mapping["sub_category"] == "subcategory"


def test_missing_required_concept_raises_specific_error():
    df = pd.DataFrame({"Order ID": ["1"], "Region": ["West"]})  # missing many required concepts
    with pytest.raises(SchemaNormalizationError) as exc_info:
        match_schema(
            df,
            [ConceptSpec("order_id", ("order id",)), ConceptSpec("sales", ("sales", "revenue"))],
            dataset_name="test_dataset",
        )
    assert "sales" in str(exc_info.value)


def test_optional_concept_missing_does_not_raise():
    df = pd.DataFrame({"Order ID": ["1"]})
    mapping = match_schema(
        df,
        [ConceptSpec("order_id", ("order id",)), ConceptSpec("ship_date", ("ship date",), required=False)],
        dataset_name="test_dataset",
    )
    assert "order_id" in mapping
    assert "ship_date" not in mapping


def test_normalize_support_tickets_matches_real_mirror_headers():
    df = pd.DataFrame(
        {
            "Ticket ID": [1], "Ticket Subject": ["Broken item"], "Ticket Description": ["It broke."],
            "Product Purchased": ["office chair"], "Date of Purchase": ["01/01/2024"],
            "Ticket Priority": ["High"], "Ticket Status": ["Open"],
        }
    )
    normalized, mapping = normalize_support_tickets(df)
    assert mapping["ticket_description"] == "Ticket Description"
    assert mapping["created_date"] == "Date of Purchase"
