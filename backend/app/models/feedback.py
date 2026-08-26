"""Feedback-loop schemas — the append-only analyst verdict log."""
from __future__ import annotations

from enum import Enum

from pydantic import BaseModel


class FeedbackVerdict(str, Enum):
    AGREE = "agree"
    DISAGREE = "disagree"
    PARTIALLY_AGREE = "partially_agree"


class FeedbackEntry(BaseModel):
    kpi_id: str
    insight_id: str
    hypothesis_id: str
    persona_id: str
    verdict: FeedbackVerdict
    correction_note: str | None = None
    submitted_at: str


class FeedbackSummary(BaseModel):
    kpi_id: str
    total_entries: int
    agree_count: int
    disagree_count: int
    partially_agree_count: int
    agreement_rate: float
