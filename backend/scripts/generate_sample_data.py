"""Generate schema-accurate PLACEHOLDER data for the two Kaggle datasets.

*** THIS IS NOT SYNTHETIC-FOR-CONVENIENCE DATA. ***
It exists only because this environment does not yet have a Kaggle API
token to download the real files (see README.md "Data provenance"). The
column headers, value ranges, and categorical vocabularies below are copied
from the real "Superstore" sales-forecasting dataset
(kaggle.com/datasets/rohitsahoo/sales-forecasting) and the real customer
support ticket dataset (kaggle.com/datasets/suraj520/customer-support-ticket-dataset).

Once a real kaggle.json is available, run:
    kaggle datasets download -d rohitsahoo/sales-forecasting -p data/raw --unzip
    kaggle datasets download -d suraj520/customer-support-ticket-dataset -p data/raw --unzip
and DELETE the two files this script writes. Nothing downstream needs to
change: services/data/schema_normalization.py fuzzy-matches columns by
concept, not by exact header, so real Kaggle exports normalize identically.

This script deliberately engineers a small number of specific, labeled
scenarios into otherwise-random data so every item in the brief's minimum
prototype scenario list (README "Demo scenarios") is reproducibly present:
  - a multi-driver KPI movement (West / Technology, quantity + discount)
  - an ambiguous / contradictory movement (Central / Office Supplies)
  - a sparse-history emerging sub-category (3D Printers, 6 weeks of history)
  - a lagged, correlated-not-causal ticket-sentiment signal feeding the
    West / Technology movement
Every engineered value is commented at the point it's injected below.
"""
from __future__ import annotations

import random
from pathlib import Path

import numpy as np
import pandas as pd

SEED = 42
random.seed(SEED)
rng = np.random.default_rng(SEED)

REPO_ROOT = Path(__file__).resolve().parents[2]
RAW_DIR = REPO_ROOT / "data" / "raw"
RAW_DIR.mkdir(parents=True, exist_ok=True)

# 104 weeks (2 years), Monday-anchored weeks, ending recently.
N_WEEKS = 104
WEEK_START = pd.Timestamp("2024-01-01")
WEEKS = [WEEK_START + pd.Timedelta(weeks=i) for i in range(N_WEEKS)]

REGIONS = ["West", "East", "Central", "South"]
SEGMENTS = ["Consumer", "Corporate", "Home Office"]
STATES_BY_REGION = {
    "West": ["California", "Washington", "Oregon", "Nevada"],
    "East": ["New York", "Pennsylvania", "New Jersey", "Massachusetts"],
    "Central": ["Texas", "Illinois", "Ohio", "Michigan"],
    "South": ["Florida", "Georgia", "North Carolina", "Tennessee"],
}
CATEGORY_SUBCATS = {
    "Furniture": ["Bookcases", "Chairs", "Tables", "Furnishings"],
    "Office Supplies": ["Storage", "Supplies", "Paper", "Binders", "Art", "Labels", "Envelopes", "Fasteners"],
    "Technology": ["Phones", "Accessories", "Machines", "Copiers"],
}
# Emerging sub-category injected only in the final 6 weeks — sparse-history scenario.
EMERGING_SUBCAT = "3D Printers"
EMERGING_CATEGORY = "Technology"
EMERGING_WEEKS = WEEKS[-6:]

# Base unit price ranges per sub-category (min, max) — loosely realistic.
PRICE_RANGES = {
    "Bookcases": (150, 450), "Chairs": (80, 400), "Tables": (120, 600), "Furnishings": (20, 150),
    "Storage": (15, 120), "Supplies": (5, 60), "Paper": (5, 40), "Binders": (5, 50),
    "Art": (5, 45), "Labels": (3, 25), "Envelopes": (3, 30), "Fasteners": (3, 20),
    "Phones": (100, 900), "Accessories": (15, 200), "Machines": (200, 2500), "Copiers": (300, 3500),
    "3D Printers": (350, 1800),
}
BASE_WEEKLY_ORDERS = {
    "Furniture": 150, "Office Supplies": 320, "Technology": 480,
}
# Structural per-sub-category margin offset (real retail sub-categories have
# systematically different characteristic margins — thin-margin commodity
# items like Labels/Fasteners vs richer-margin organizer items like Storage).
# This is what gives a genuine "composition shifted toward lower-margin
# items" (cost_mix_effect) an actual mechanism to act through — without a
# structural margin difference between sub-categories, no amount of
# share-shifting changes the category-level margin.
SUBCATEGORY_MARGIN_OFFSET = {
    "Labels": -0.07, "Envelopes": -0.06, "Fasteners": -0.07,
    "Storage": 0.05, "Paper": 0.0, "Binders": 0.02, "Art": 0.01, "Supplies": 0.0,
}

CUSTOMER_FIRST = ["James", "Maria", "Robert", "Linda", "Michael", "Patricia", "David", "Jennifer",
                  "William", "Elizabeth", "Richard", "Susan", "Joseph", "Jessica", "Thomas", "Sarah"]
CUSTOMER_LAST = ["Anderson", "Clark", "Rodriguez", "Lewis", "Walker", "Young", "Allen", "King",
                 "Wright", "Scott", "Torres", "Nguyen", "Hill", "Flores", "Green", "Adams"]


def _customer_pool(n: int = 250) -> list[tuple[str, str]]:
    pool = []
    for i in range(n):
        first = CUSTOMER_FIRST[i % len(CUSTOMER_FIRST)]
        last = CUSTOMER_LAST[(i * 7) % len(CUSTOMER_LAST)]
        pool.append((f"CU-{10000 + i}", f"{first} {last}"))
    return pool


CUSTOMERS = _customer_pool()


def _seasonal_factor(week_idx: int) -> float:
    """Mild yearly seasonality (Q4 bump) plus a gentle upward trend."""
    week_of_year = week_idx % 52
    seasonal = 1.0 + 0.18 * np.sin(2 * np.pi * (week_of_year - 40) / 52) ** 2 if week_of_year >= 40 else 1.0
    trend = 1.0 + 0.002 * week_idx
    return seasonal * trend


def generate_superstore_rows() -> pd.DataFrame:
    rows = []
    row_id = 1
    order_id_counter = 1

    for week_idx, week_start in enumerate(WEEKS):
        for region in REGIONS:
            for category, subcats in CATEGORY_SUBCATS.items():
                base = BASE_WEEKLY_ORDERS[category] / len(REGIONS)
                seasonal = _seasonal_factor(week_idx)

                for sub_category in subcats:
                    expected_orders = base / len(subcats) * seasonal

                    # --- Engineered scenario 1: multi-driver drop -----------
                    # West + Technology, final 4 weeks: quantity down ~18%
                    # AND discount up +12pp. Two independent, real drivers
                    # co-occurring in the same window (driver-tree must find
                    # both, not just the larger one).
                    quantity_multiplier = 1.0
                    discount_bump = 0.0
                    if (
                        region == "West"
                        and category == "Technology"
                        and week_start >= WEEKS[-4]
                    ):
                        quantity_multiplier = 0.82
                        discount_bump = 0.12

                    # --- Engineered scenario 2: ambiguous / contradictory ---
                    # Central + Office Supplies, final 3 weeks: two candidate
                    # drivers engineered to comparable magnitude (a genuine
                    # cost-mix shift toward cheap sub-categories, AND a
                    # modest discount bump) so the driver tree does not
                    # cleanly favor one story over the other -> low
                    # confidence margin -> abstain with competing hypotheses.
                    mix_shift_toward_cheap = False
                    volume_mix_multiplier = 1.0
                    if (
                        region == "Central"
                        and category == "Office Supplies"
                        and week_start >= WEEKS[-3]
                    ):
                        discount_bump = 0.04
                        cheap_subcats = ("Labels", "Envelopes", "Fasteners")
                        expensive_subcats = ("Storage", "Paper", "Binders", "Art")
                        if sub_category in cheap_subcats:
                            mix_shift_toward_cheap = True
                            volume_mix_multiplier = 2.2  # these gain share
                        elif sub_category in expensive_subcats:
                            volume_mix_multiplier = 0.65  # these lose share

                    expected_orders *= volume_mix_multiplier

                    # NOTE: quantity_multiplier is applied per-order-line below
                    # (not to the Poisson order-count mean) so the engineered
                    # effect survives order-count noise at realistic volumes
                    # instead of being swamped by it.
                    n_orders = rng.poisson(max(expected_orders, 0.15))

                    for _ in range(n_orders):
                        price_lo, price_hi = PRICE_RANGES[sub_category]
                        unit_price = rng.uniform(price_lo, price_hi)
                        quantity = max(1, round(int(rng.integers(2, 6)) * quantity_multiplier))
                        base_discount = rng.choice([0.0, 0.1, 0.15, 0.2, 0.3], p=[0.45, 0.2, 0.15, 0.12, 0.08])
                        discount = min(base_discount + discount_bump, 0.6)

                        if mix_shift_toward_cheap:
                            unit_price *= 0.85  # cheaper mix within the category

                        sales = round(unit_price * quantity * (1 - discount), 2)
                        margin_rate = (
                            rng.uniform(0.10, 0.30) - discount * 0.35
                            + SUBCATEGORY_MARGIN_OFFSET.get(sub_category, 0.0)
                        )
                        profit = round(sales * margin_rate, 2)

                        order_date = week_start + pd.Timedelta(days=int(rng.integers(0, 7)))
                        ship_date = order_date + pd.Timedelta(days=int(rng.integers(2, 7)))
                        cust_id, cust_name = CUSTOMERS[rng.integers(0, len(CUSTOMERS))]

                        rows.append({
                            "Row ID": row_id,
                            "Order ID": f"US-{2024 + order_id_counter // 5000}-{100000 + order_id_counter}",
                            "Order Date": order_date.strftime("%m/%d/%Y"),
                            "Ship Date": ship_date.strftime("%m/%d/%Y"),
                            "Ship Mode": rng.choice(["Standard Class", "Second Class", "First Class", "Same Day"]),
                            "Customer ID": cust_id,
                            "Customer Name": cust_name,
                            "Segment": rng.choice(SEGMENTS, p=[0.55, 0.3, 0.15]),
                            "Country": "United States",
                            "City": rng.choice(["Springfield", "Franklin", "Greenville", "Fairview", "Salem"]),
                            "State": rng.choice(STATES_BY_REGION[region]),
                            "Postal Code": int(rng.integers(10000, 99999)),
                            "Region": region,
                            "Product ID": f"{category[:3].upper()}-{sub_category[:2].upper()}-{rng.integers(1000,9999)}",
                            "Category": category,
                            "Sub-Category": sub_category,
                            "Product Name": f"{sub_category} Model {rng.integers(100, 999)}",
                            "Sales": sales,
                            "Quantity": int(quantity),
                            "Discount": round(discount, 2),
                            "Profit": profit,
                        })
                        row_id += 1
                        order_id_counter += 1

                # --- Emerging sub-category: sparse history scenario --------
                if category == EMERGING_CATEGORY and week_start in EMERGING_WEEKS:
                    n_orders = rng.poisson(3)
                    # Deliberate soft dip in the final emerging week to give
                    # the sparse-history scenario an actual (uncertain) signal.
                    qty_mult = 0.6 if week_start == EMERGING_WEEKS[-1] else 1.0
                    for _ in range(max(n_orders, 1)):
                        price_lo, price_hi = PRICE_RANGES[EMERGING_SUBCAT]
                        unit_price = rng.uniform(price_lo, price_hi)
                        quantity = max(1, int(rng.integers(1, 4) * qty_mult))
                        discount = rng.choice([0.0, 0.1, 0.15])
                        sales = round(unit_price * quantity * (1 - discount), 2)
                        profit = round(sales * rng.uniform(0.12, 0.22), 2)
                        order_date = week_start + pd.Timedelta(days=int(rng.integers(0, 7)))
                        ship_date = order_date + pd.Timedelta(days=int(rng.integers(2, 7)))
                        cust_id, cust_name = CUSTOMERS[rng.integers(0, len(CUSTOMERS))]
                        rows.append({
                            "Row ID": row_id,
                            "Order ID": f"US-2025-{200000 + order_id_counter}",
                            "Order Date": order_date.strftime("%m/%d/%Y"),
                            "Ship Date": ship_date.strftime("%m/%d/%Y"),
                            "Ship Mode": rng.choice(["Standard Class", "Second Class", "First Class"]),
                            "Customer ID": cust_id,
                            "Customer Name": cust_name,
                            "Segment": rng.choice(SEGMENTS),
                            "Country": "United States",
                            "City": "Fairview",
                            "State": rng.choice(STATES_BY_REGION[region]),
                            "Postal Code": int(rng.integers(10000, 99999)),
                            "Region": region,
                            "Product ID": f"TEC-3D-{rng.integers(1000,9999)}",
                            "Category": EMERGING_CATEGORY,
                            "Sub-Category": EMERGING_SUBCAT,
                            "Product Name": f"3D Printer Model {rng.integers(100, 999)}",
                            "Sales": sales,
                            "Quantity": int(quantity),
                            "Discount": round(discount, 2),
                            "Profit": profit,
                        })
                        row_id += 1
                        order_id_counter += 1

    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# Support tickets
# ---------------------------------------------------------------------------

TICKET_TYPES = ["Technical issue", "Billing inquiry", "Refund request", "Product inquiry", "Cancellation request"]
CHANNELS = ["Email", "Chat", "Phone", "Social media"]

NEGATIVE_TEMPLATES = [
    "This {product} stopped working after only a few days, I am extremely disappointed and frustrated.",
    "Terrible experience with my {product}. It arrived broken and support has been unhelpful.",
    "I am furious — my {product} keeps failing and nobody has resolved the issue after multiple attempts.",
    "Very poor quality {product}. Requesting a refund immediately, this is unacceptable.",
    "The {product} is defective and customer service response has been slow and dismissive.",
]
NEUTRAL_TEMPLATES = [
    "I have a question about how to set up my {product}, could you send instructions.",
    "Requesting an update on the delivery status of my recent {product} order.",
    "Can you clarify the warranty terms for the {product} I purchased last month.",
    "Following up on my previous ticket about the {product} configuration options.",
    "Would like to know if the {product} is compatible with my existing setup.",
]
POSITIVE_TEMPLATES = [
    "Just wanted to say the {product} works great and support resolved my question quickly, thanks!",
    "Excellent experience — my {product} issue was fixed fast and the team was very helpful.",
    "Really happy with the {product}, exceeded expectations and arrived on time.",
    "Great service, the {product} replacement was processed smoothly and I appreciate the help.",
]

CATEGORY_TO_PRODUCT = {
    "Furniture": ["office chair", "bookcase", "conference table", "desk furnishing"],
    "Office Supplies": ["binder set", "storage bin", "label maker", "paper supply kit"],
    "Technology": ["smartphone", "laptop accessory", "office copier", "phone system"],
}


def _sample_ticket_text(category: str, sentiment_bucket: str) -> tuple[str, str]:
    product = random.choice(CATEGORY_TO_PRODUCT[category])
    templates = {"negative": NEGATIVE_TEMPLATES, "neutral": NEUTRAL_TEMPLATES, "positive": POSITIVE_TEMPLATES}[sentiment_bucket]
    body = random.choice(templates).format(product=product)
    subject = body.split(",")[0][:60]
    return subject, body


def generate_ticket_rows() -> pd.DataFrame:
    rows = []
    ticket_id = 1

    for week_idx, week_start in enumerate(WEEKS):
        for category in CATEGORY_SUBCATS:
            base_volume = {"Furniture": 12, "Office Supplies": 22, "Technology": 16}[category]
            neg_p, neu_p, pos_p = 0.20, 0.55, 0.25

            # --- Engineered lagged signal for scenario 1 --------------------
            # Technology tickets: negative-sentiment spike 1-2 weeks BEFORE
            # the West/Technology sales drop (final 4 weeks), modelling a
            # plausible "customers already reporting problems before the
            # regional sales figure moves" lead indicator. Single time
            # series, no control group -> reasoning layer must label this
            # "correlated", never "causally supported".
            if category == "Technology" and week_start in WEEKS[-6:-2]:
                base_volume = int(base_volume * 1.6)
                neg_p, neu_p, pos_p = 0.55, 0.30, 0.15

            # --- Engineered contradictory signal for scenario 2 -------------
            # Office Supplies: ticket VOLUME rises in the final 3 weeks
            # (suggesting a problem) but sentiment stays essentially neutral
            # (not corroborating a negative-experience story) — the
            # contradiction that should push the ambiguous Central/Office
            # Supplies movement toward abstention rather than a confident
            # single narrative.
            if category == "Office Supplies" and week_start in WEEKS[-3:]:
                base_volume = int(base_volume * 1.35)
                neg_p, neu_p, pos_p = 0.22, 0.60, 0.18

            n_tickets = rng.poisson(base_volume)
            for _ in range(n_tickets):
                sentiment_bucket = random.choices(
                    ["negative", "neutral", "positive"], weights=[neg_p, neu_p, pos_p]
                )[0]
                subject, body = _sample_ticket_text(category, sentiment_bucket)
                created = week_start + pd.Timedelta(days=int(rng.integers(0, 7)))
                cust_id, cust_name = CUSTOMERS[rng.integers(0, len(CUSTOMERS))]
                # NOTE: the real suraj520 ticket dataset has no distinct
                # "ticket created" timestamp — "Date of Purchase" is the only
                # date field available. We treat it as the ticket-anchor date
                # (documented data limitation, see README "Data provenance"),
                # rather than inventing a field the real download won't have.
                priority = {"negative": "High", "neutral": "Medium", "positive": "Low"}[sentiment_bucket]
                if random.random() < 0.15:
                    priority = random.choice(["Low", "Medium", "High", "Critical"])

                rows.append({
                    "Ticket ID": ticket_id,
                    "Customer Name": cust_name,
                    "Customer Email": f"{cust_name.lower().replace(' ', '.')}@example.com",
                    "Customer Age": int(rng.integers(19, 70)),
                    "Customer Gender": random.choice(["Male", "Female", "Other"]),
                    "Product Purchased": random.choice(CATEGORY_TO_PRODUCT[category]),
                    "Date of Purchase": created.strftime("%m/%d/%Y"),
                    "Ticket Type": random.choice(TICKET_TYPES),
                    "Ticket Subject": subject,
                    "Ticket Description": body,
                    "Ticket Status": random.choice(["Open", "Pending Customer Response", "Closed"]),
                    "Resolution": "" if sentiment_bucket == "negative" and random.random() < 0.4 else "Resolved after investigation.",
                    "Ticket Priority": priority,
                    "Ticket Channel": random.choice(CHANNELS),
                    "_generated_category": category,  # internal only, dropped before write
                })
                ticket_id += 1

    df = pd.DataFrame(rows)
    return df


def main() -> None:
    superstore = generate_superstore_rows()
    superstore_path = RAW_DIR / "superstore_sales_placeholder.csv"
    superstore.to_csv(superstore_path, index=False)
    print(f"Wrote {len(superstore):,} rows to {superstore_path}")

    tickets = generate_ticket_rows()
    tickets_path = RAW_DIR / "customer_support_tickets_placeholder.csv"
    tickets.drop(columns=["_generated_category"]).to_csv(tickets_path, index=False)
    print(f"Wrote {len(tickets):,} rows to {tickets_path}")


if __name__ == "__main__":
    main()
