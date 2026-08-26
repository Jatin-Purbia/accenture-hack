"""Signal layer — classical NLP event extraction from ticket text.

Deliberately NOT the narrative LLM. Two things happen here, both
deterministic/classical:

1. Topic/category tagging: a rule-based keyword lookup mapping the ticket's
   free-text `product` field to one of the Superstore categories (Furniture /
   Office Supplies / Technology). This is the join key that lets ticket
   signals be compared against sales KPIs despite the two source systems
   having no shared foreign key (see docs/architecture.md "Fragmented
   sources").
2. Sentiment scoring: a small lexicon-based polarity scorer (bag-of-words,
   weighted term lookup) over ticket subject + description. This is
   intentionally simple and auditable — not a black-box model — so every
   sentiment score can be explained by which words in the text matched the
   lexicon. A production system would likely swap in a small fine-tuned
   classifier here; the interface (`score_sentiment`) is what matters, not
   the specific technique.
"""
from __future__ import annotations

import re

import pandas as pd

from app.core.logging import get_logger

logger = get_logger(__name__)

# Rule-based product -> category keyword lookup. Order matters: more
# specific keywords are checked before generic fallbacks.
_CATEGORY_KEYWORDS: list[tuple[str, list[str]]] = [
    ("Furniture", ["chair", "bookcase", "table", "furnishing", "desk", "cabinet"]),
    ("Office Supplies", ["binder", "storage", "label", "paper", "supply", "supplies", "envelope", "fastener", "art "]),
    ("Technology", ["phone", "smartphone", "laptop", "copier", "printer", "machine", "accessory", "accessories"]),
]


def tag_category(product_text: str) -> str | None:
    text = product_text.lower()
    for category, keywords in _CATEGORY_KEYWORDS:
        if any(kw in text for kw in keywords):
            return category
    return None


# Lexicon-based sentiment scorer. Weights are hand-set polarity strengths;
# this is a transparent, inspectable alternative to a black-box model,
# consistent with the brief's requirement that non-LLM methods be used
# wherever the LLM is not the appropriate tool.
_POSITIVE_TERMS = {
    "great": 1.0, "excellent": 1.2, "happy": 0.9, "thanks": 0.6, "thank": 0.6,
    "helpful": 0.8, "fast": 0.5, "smooth": 0.7, "appreciate": 0.8, "quickly": 0.5,
    "resolved": 0.6, "works": 0.4, "exceeded": 0.9, "love": 1.0, "good": 0.5,
}
_NEGATIVE_TERMS = {
    "terrible": -1.2, "disappointed": -1.0, "frustrated": -0.9, "furious": -1.3,
    "broken": -0.9, "defective": -1.0, "unhelpful": -0.9, "poor": -0.8,
    "unacceptable": -1.1, "failing": -0.9, "failed": -0.8, "slow": -0.5,
    "dismissive": -0.9, "refund": -0.4, "issue": -0.3, "problem": -0.4,
    "stopped working": -1.0, "not working": -1.0,
}

_WORD_RE = re.compile(r"[a-z']+")


def score_sentiment(text: str) -> float:
    """Return a polarity score clipped to [-1, 1].

    Simple average of matched-term weights over the token count, scaled and
    clipped — not a normalized probability, just a consistent relative scale
    used for time-series comparison (the reasoning layer only ever looks at
    *changes* in this score, not its absolute value).
    """
    lowered = text.lower()
    score = 0.0
    matches = 0
    for phrase, weight in {**_POSITIVE_TERMS, **_NEGATIVE_TERMS}.items():
        if phrase in lowered:
            score += weight
            matches += 1
    if matches == 0:
        return 0.0
    normalized = score / max(matches, 1)
    return max(-1.0, min(1.0, normalized))


def extract_ticket_events(tickets_df: pd.DataFrame) -> pd.DataFrame:
    """Attach `event_category` and `sentiment_score` columns to a normalized
    ticket DataFrame (as produced by ingestion.load_raw_support_tickets)."""
    working = tickets_df.copy()
    working["event_category"] = working["product"].fillna("").apply(tag_category)
    working["sentiment_score"] = working["full_text"].fillna("").apply(score_sentiment)

    unmatched = working["event_category"].isna().sum()
    if unmatched:
        logger.warning(
            "ticket_category_unmatched",
            unmatched_count=int(unmatched),
            total=len(working),
            note="Tickets whose product text didn't match any category keyword are excluded from category-level KPIs.",
        )
    return working


def build_weekly_ticket_signals(events_df: pd.DataFrame) -> pd.DataFrame:
    """Weekly x category ticket volume + mean sentiment — the two
    independent-cadence signal KPIs fed into the Reasoning layer's
    correlation tests."""
    working = events_df.dropna(subset=["event_category"])
    grouped = (
        working.groupby(["week_start", "event_category"])
        .agg(
            ticket_count=("ticket_id", "count"),
            mean_sentiment=("sentiment_score", "mean"),
            negative_share=("sentiment_score", lambda s: float((s < -0.2).mean())),
        )
        .reset_index()
        .rename(columns={"event_category": "category"})
        .sort_values(["category", "week_start"])
    )
    return grouped
