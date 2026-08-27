"""Story layer — a deterministic safety net for the regional-leader
persona's plain-language requirement.

The prompt tells the model not to use statistics jargon, but small local
models (the free Ollama fallback) don't reliably comply — during testing,
the local model wrote sentences like "a correlation coefficient of 0.60 and
a p-value of 0.05" straight into a business-leader briefing anyway. Because
"no jargon for this persona" is a hard requirement (not a nice-to-have), we
don't just hope the LLM complies: we scan its output for jargon leakage
and, if found, replace the narrative with a template built directly from
the evidence packet's own fields. This keeps the SAME "never fabricate a
number" guarantee (the fallback only ever states numbers/labels already in
the evidence), while guaranteeing the persona's tone contract even when the
LLM does not comply — a deterministic guardrail on STYLE, consistent with
the project's broader rule that facts are never LLM-only.
"""
from __future__ import annotations

import re

from app.models.evidence import DriverContribution, EvidencePacket

_JARGON_PATTERN = re.compile(
    r"p-value|p\s*=\s*0|correlation coefficient|percentage point|forecast band|"
    r"causally supported|quasi-experimental|z-score|standard deviation|"
    r"statistical strength|evidence agreement|data completeness|confidence score|"
    r"\bhypothesis\b|\bcorrelat\w*\b|\br\s*=\s*-?0\.\d+|\b\w+_\w+\b",
    re.IGNORECASE,
)


def contains_jargon(text: str) -> bool:
    """True if `text` contains a statistics term or a raw snake_case
    identifier (driver/signal names like "quantity_effect" always contain
    an underscore — a cheap, reliable tell that internal naming leaked into
    prose meant for a non-technical reader)."""
    return bool(_JARGON_PATTERN.search(text))


_DRIVER_PLAIN_PHRASE = {
    "quantity_effect": "fewer units being sold than usual",
    "avg_price_effect": "a shift in average selling price",
    "discount_effect": "a change in discounting",
    "cost_mix_effect": "a shift in which products are selling",
    "margin_rate_effect": "a change in margins, most often from discounting",
}


def _plain_driver_phrase(driver: DriverContribution) -> str:
    return _DRIVER_PLAIN_PHRASE.get(driver.driver, driver.driver.replace("_", " "))


def build_plain_fallback_narrative(evidence: EvidencePacket) -> str:
    """A guaranteed-jargon-free narrative built directly from evidence
    fields — used only when the LLM's own attempt leaks technical language."""
    m = evidence.movement
    direction = "down" if m.relative_change_pct < 0 else "up"
    pct = abs(m.relative_change_pct)

    if evidence.abstained:
        return (
            f"{m.dimension_label} {m.kpi_name.lower()} moved {direction} {pct:.0f}% this week, and "
            f"we are not yet confident enough to point to one single cause — a couple of different "
            f"explanations look equally likely. We are flagging this for an analyst to take a closer "
            f"look rather than guessing at a next step."
        )

    top = next(
        (h for h in evidence.hypotheses if h.id == evidence.top_hypothesis_id),
        evidence.hypotheses[0] if evidence.hypotheses else None,
    )
    if top is None or not top.drivers:
        return (
            f"{m.dimension_label} {m.kpi_name.lower()} moved {direction} {pct:.0f}% this week. We don't "
            f"yet have a well-supported explanation for this — it's been flagged for an analyst to review."
        )

    lead_driver = max(top.drivers, key=lambda d: abs(d.contribution_pct))
    driver_phrase = _plain_driver_phrase(lead_driver)
    confidence_phrase = (
        "a well-supported explanation" if top.confidence >= 0.75 else "our best current explanation, though we'd call it moderately confident"
    )

    return (
        f"{m.dimension_label} {m.kpi_name.lower()} moved {direction} {pct:.0f}% this week, mainly linked "
        f"to {driver_phrase}. This looks like {confidence_phrase} based on the data we have so far."
    )
