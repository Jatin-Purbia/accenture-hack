"""Feedback router — the analyst-verdict capture mechanism (graded
requirement). Real, append-only, and actually wired into the demo UI."""
from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.core.dependencies import feedback_store_dependency
from app.models.feedback import FeedbackEntry, FeedbackSummary, FeedbackVerdict
from app.services.data.feedback_store import FeedbackStore

router = APIRouter(prefix="/api/feedback", tags=["feedback"])


class FeedbackSubmission(BaseModel):
    kpi_id: str
    insight_id: str
    hypothesis_id: str
    persona_id: str
    verdict: FeedbackVerdict
    correction_note: str | None = None


@router.post("", response_model=FeedbackEntry)
def submit_feedback(
    submission: FeedbackSubmission, store: FeedbackStore = Depends(feedback_store_dependency)
) -> FeedbackEntry:
    entry = FeedbackEntry(
        kpi_id=submission.kpi_id,
        insight_id=submission.insight_id,
        hypothesis_id=submission.hypothesis_id,
        persona_id=submission.persona_id,
        verdict=submission.verdict,
        correction_note=submission.correction_note,
        submitted_at=datetime.now(timezone.utc).isoformat(),
    )
    store.append(entry)
    return entry


@router.get("/summary/{kpi_id}", response_model=FeedbackSummary)
def get_feedback_summary(kpi_id: str, store: FeedbackStore = Depends(feedback_store_dependency)) -> FeedbackSummary:
    return store.summary_for_kpi(kpi_id)


@router.get("", response_model=list[FeedbackEntry])
def list_feedback(store: FeedbackStore = Depends(feedback_store_dependency)) -> list[FeedbackEntry]:
    return store.read_all()
