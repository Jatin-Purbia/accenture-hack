"""Story layer — versioned prompt templates.

Centralized here (not inlined at call sites) so every prompt used in
production is reviewable in one place and stamped with a version string that
appears in telemetry. The LLM is given ONLY the evidence packet's own
structured fields, rendered as plain text below — never raw transaction rows
or raw ticket text. This is what the grounding check in grounding.py verifies
against: every number the LLM writes must trace back to a number in this
same rendered evidence summary.
"""
from __future__ import annotations

from app.models.evidence import EvidencePacket

PROMPT_VERSION = "story-v2"

_FORMAT_RULES = """
- Plain prose paragraphs ONLY. Do NOT use markdown formatting of any kind —
  no "#" headers, no "**bold**", no bullet/numbered lists, no horizontal
  rules. Write the way you would in a plain-text email.
"""

_REGIONAL_LEADER_SYSTEM = """You are writing a KPI briefing for a busy regional business leader.
Rules:
- 3-5 sentences maximum. Plain business language. No statistics jargon (no "z-score", "p-value", "standard deviation", "regression").
- Do not require the reader to interpret a chart.
- State what happened, your best-supported explanation, and ONE recommended next action.
- Every number you state must come from the evidence given to you below — never invent, round-trip-guess, or extrapolate a number that isn't already present in the evidence.
- If the evidence says the finding is uncertain or contested, say so plainly instead of picking a confident-sounding explanation.
""" + _FORMAT_RULES

_ANALYST_SYSTEM = """You are writing a KPI analysis for a data/business analyst audience.
Rules:
- Give a full breakdown: the movement, each contributing driver with its % contribution, any correlation findings WITH their correlated-vs-causally-supported label and rationale, and the overall confidence score.
- Be explicit about caveats: sparse history, contradictory signals, or why a correlation is not being called causal.
- Every number you state must come from the evidence given to you below — never invent, round-trip-guess, or extrapolate a number that isn't already present in the evidence.
- Write 2-4 short paragraphs. It is fine to be technical.
""" + _FORMAT_RULES

_ABSTENTION_ADDENDUM = """
IMPORTANT: The reasoning system could NOT confidently settle on a single explanation for this movement — multiple competing hypotheses remain plausible. Do NOT pick a winner or imply more certainty than the evidence supports.
Present the competing hypotheses side by side, state what additional data would help resolve the ambiguity (the evidence lists this), and recommend this be flagged for human analyst review rather than acted on automatically.
"""


def system_prompt_for_persona(persona_role: str, abstained: bool) -> str:
    base = _ANALYST_SYSTEM if persona_role == "analyst" else _REGIONAL_LEADER_SYSTEM
    return base + (_ABSTENTION_ADDENDUM if abstained else "")


def render_evidence_summary(evidence: EvidencePacket) -> str:
    """Render the evidence packet as plain text — this text (not the
    original Pydantic object) is what grounding.py scans for numbers, and
    it is the ONLY numeric context the LLM receives."""
    m = evidence.movement
    lines = [
        f"KPI: {m.kpi_name} — {m.dimension_label}",
        f"Period: {m.period_start} to {m.period_end}",
        f"Actual value: {m.actual_value:.2f}",
        f"Expected value (forecast baseline): {m.expected_value:.2f}",
        f"Forecast band: {m.forecast_band_low:.2f} to {m.forecast_band_high:.2f}",
        f"Absolute change: {m.absolute_change:+.2f}",
        f"Relative change: {m.relative_change_pct:+.1f}%",
        f"Flagged material: {m.is_material}",
        "",
        f"Data completeness: {evidence.data_completeness.weeks_of_history} weeks of history "
        f"(out of {evidence.data_completeness.weeks_required_for_high_confidence} recommended), "
        f"source last refreshed {evidence.data_completeness.source_freshness_days} day(s) ago.",
        "",
    ]

    if evidence.abstained:
        lines.append(f"STATUS: ABSTAINED — {evidence.abstention_reason}")
        lines.append("")

    for h in evidence.hypotheses:
        marker = " (TOP HYPOTHESIS)" if h.id == evidence.top_hypothesis_id and not evidence.abstained else ""
        lines.append(f"Hypothesis [{h.id}]{marker}: {h.label} — confidence {h.confidence:.2f}")
        lines.append(f"  Summary: {h.summary}")
        for d in h.drivers:
            lines.append(
                f"  Driver '{d.driver}': {d.contribution_pct:+.1f}% of movement, "
                f"direction={d.direction}. {d.description}"
            )
        for c in h.correlations:
            lines.append(
                f"  Correlation signal '{c.signal_name}': r={c.correlation_coefficient:.2f}, "
                f"p={c.p_value:.2f}, lag={c.lag_weeks}w, classification={c.classification.value}. "
                f"{c.rationale}"
            )
        lines.append("")

    lines.append("Lineage: " + " -> ".join(evidence.lineage))
    return "\n".join(lines)


def render_action_context(action_lines: list[str]) -> str:
    if not action_lines:
        return "No standard playbook action was found for the leading driver(s) — recommend manual analyst review."
    header = "Rule-based recommended action(s) (drivers/levers/actions are NOT generated by you — you may only phrase the final summary sentence for the reader; do not invent alternatives):"
    return header + "\n" + "\n".join(action_lines)


def build_user_prompt(evidence: EvidencePacket, action_lines: list[str], persona_role: str) -> str:
    evidence_summary = render_evidence_summary(evidence)
    action_context = render_action_context(action_lines)
    audience_instruction = (
        "Write the briefing for the regional leader persona."
        if persona_role != "analyst"
        else "Write the analysis for the analyst persona."
    )
    return (
        f"{audience_instruction}\n\n"
        f"=== EVIDENCE (the only source of numbers/facts you may use) ===\n{evidence_summary}\n\n"
        f"=== ACTION PLAYBOOK CONTEXT ===\n{action_context}\n"
    )
