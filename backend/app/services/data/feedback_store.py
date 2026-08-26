"""Feedback loop — an append-only JSONL log of analyst verdicts on insights.

This is the graded "mechanism to learn from analyst feedback" requirement.
The capture mechanism is real and runs in the demo (POST /api/feedback
appends a line; GET /api/feedback/summary/{kpi_id} aggregates it). How this
would feed BACK into confidence calibration (e.g. adjusting a KPI's
materiality thresholds or a driver's prior weight based on historical
agreement rates) is a v2 roadmap item — see README "Roadmap" — deliberately
not built here, since doing it honestly needs enough real feedback volume
to calibrate against, which a hackathon demo cannot generate.
"""
from __future__ import annotations

import json
from pathlib import Path

from app.models.feedback import FeedbackEntry, FeedbackSummary


class FeedbackStore:
    def __init__(self, log_path: Path):
        self._log_path = log_path
        self._log_path.parent.mkdir(parents=True, exist_ok=True)

    def append(self, entry: FeedbackEntry) -> None:
        with self._log_path.open("a", encoding="utf-8") as f:
            f.write(entry.model_dump_json() + "\n")

    def read_all(self) -> list[FeedbackEntry]:
        if not self._log_path.exists():
            return []
        entries = []
        with self._log_path.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    entries.append(FeedbackEntry.model_validate(json.loads(line)))
        return entries

    def summary_for_kpi(self, kpi_id: str) -> FeedbackSummary:
        entries = [e for e in self.read_all() if e.kpi_id == kpi_id]
        total = len(entries)
        agree = sum(1 for e in entries if e.verdict.value == "agree")
        disagree = sum(1 for e in entries if e.verdict.value == "disagree")
        partial = sum(1 for e in entries if e.verdict.value == "partially_agree")
        return FeedbackSummary(
            kpi_id=kpi_id,
            total_entries=total,
            agree_count=agree,
            disagree_count=disagree,
            partially_agree_count=partial,
            agreement_rate=(agree / total) if total else 0.0,
        )


_singleton: FeedbackStore | None = None


def get_feedback_store(log_path: Path) -> FeedbackStore:
    global _singleton
    if _singleton is None:
        _singleton = FeedbackStore(log_path)
    return _singleton
