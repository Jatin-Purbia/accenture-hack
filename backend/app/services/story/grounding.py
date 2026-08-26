"""Story layer — automated grounding check.

This is the concrete enforcement of "the LLM is not the source of
quantitative truth": after every narrative call, we regex-extract every
number the LLM wrote and verify each one traces back to a number that was
actually present in the evidence packet text handed to it. Numbers that
don't match are logged as warnings and surfaced in the API response/UI —
this makes hallucinated figures visible to the user rather than silently
trusted, which is the actual point of the check (a hackathon-scale checker
cannot rewrite the LLM's prose, but it CAN make ungrounded claims visible).

Matching allows for reasonable rounding (the LLM writing "$315,000" for an
evidence value of 314638.31, or "35%" for 34.9) via a small relative/
absolute tolerance and a few standard rounding granularities — exact
string matching would flag almost every real sentence as "ungrounded"
purely from prose rounding, which would make the check useless.
"""
from __future__ import annotations

import re

from app.core.logging import get_logger
from app.models.insight import GroundingCheckResult

logger = get_logger(__name__)

_NUMBER_RE = re.compile(r"-?\d[\d,]*\.?\d*")

RELATIVE_TOLERANCE = 0.03  # 3%
ABSOLUTE_TOLERANCE = 0.5


def _parse_numbers(text: str) -> list[float]:
    out = []
    for match in _NUMBER_RE.findall(text):
        cleaned = match.replace(",", "")
        try:
            out.append(float(cleaned))
        except ValueError:
            continue
    return out


def _rounding_variants(value: float) -> set[float]:
    variants = {value, abs(value), round(value, 0), round(value, 1)}
    if abs(value) >= 100:
        variants.add(round(value, -1))
    if abs(value) >= 1000:
        variants.add(round(value, -2))
        variants.add(round(value, -3))
    return variants


def _matches_any(candidate: float, known_variant_sets: list[set[float]]) -> bool:
    for variants in known_variant_sets:
        for known in variants:
            if abs(candidate - known) <= ABSOLUTE_TOLERANCE:
                return True
            if known != 0 and abs(candidate - known) / abs(known) <= RELATIVE_TOLERANCE:
                return True
    return False


def check_grounding(llm_text: str, evidence_summary_text: str) -> GroundingCheckResult:
    evidence_numbers = _parse_numbers(evidence_summary_text)
    known_variant_sets = [_rounding_variants(n) for n in evidence_numbers]

    llm_numbers_raw = _NUMBER_RE.findall(llm_text)
    checked: list[str] = []
    ungrounded: list[str] = []

    for raw in llm_numbers_raw:
        try:
            value = float(raw.replace(",", ""))
        except ValueError:
            continue
        if -9 <= value <= 9 and value == int(value):
            continue  # bare single digits are almost always prose ("one action"), not evidentiary figures
        checked.append(raw)
        if not _matches_any(value, known_variant_sets):
            ungrounded.append(raw)

    if ungrounded:
        logger.warning(
            "narrative_contains_ungrounded_numbers",
            ungrounded_numbers=ungrounded,
            total_checked=len(checked),
        )

    return GroundingCheckResult(
        passed=len(ungrounded) == 0,
        checked_numbers=checked,
        ungrounded_numbers=ungrounded,
    )
