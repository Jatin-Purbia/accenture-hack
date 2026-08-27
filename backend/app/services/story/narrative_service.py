"""Story layer orchestrator — the only entry point the API layer calls into
this package. Ties together, in order:

  1. Tier decision (cost/latency control) — cheap model for confident,
     routine insights; strong model reserved for low-confidence/ambiguous
     ones (services/reasoning's own abstention/confidence output decides
     this, not a separate heuristic).
  2. Cache lookup — keyed on (kpi, period, evidence hash, persona); skips
     the LLM call entirely on a hit.
  3. Rule-based action recommendation — computed BEFORE the LLM call, since
     the LLM only phrases the already-decided action, never invents one.
  4. The LLM call itself, via the swappable LLMClient.
  5. The grounding check — verifies every number the LLM wrote traces back
     to the evidence text it was given.
  6. Telemetry assembly (tokens, latency, cost, cache hit, tier) — every
     field the UI's telemetry panel displays comes from this step.
"""
from __future__ import annotations

import re
from datetime import datetime, timezone

from app.core.config import Settings
from app.core.logging import get_logger
from app.models.evidence import EvidencePacket
from app.models.insight import GroundingCheckResult, LlmTelemetry, PersonaNarrative
from app.services.story.action_recommender import recommend_actions
from app.services.story.cache import CacheKey, NarrativeCache, compute_evidence_hash
from app.services.story.grounding import check_grounding
from app.services.story.llm_client import LLMClient, Tier
from app.services.story.plain_language import build_plain_fallback_narrative, contains_jargon
from app.services.story.prompt_templates import (
    PROMPT_VERSION,
    build_user_prompt,
    render_action_context,
    render_evidence_summary,
    system_prompt_for_persona,
)

logger = get_logger(__name__)


def decide_tier(evidence: EvidencePacket, cutoff: float) -> Tier:
    """Cost/latency tiering: reserve the strong model for the cases that
    actually need it (abstained/ambiguous, or a confidence score below the
    cutoff). This decision is derived entirely from the reasoning layer's
    own computed confidence — it is not a separate, independent guess."""
    if evidence.abstained:
        return "strong"
    top = next((h for h in evidence.hypotheses if h.id == evidence.top_hypothesis_id), None)
    if top is None or top.confidence < cutoff:
        return "strong"
    return "cheap"


def generate_persona_narrative(
    evidence: EvidencePacket,
    persona_id: str,
    persona_role: str,
    llm_client: LLMClient,
    cache: NarrativeCache,
    settings: Settings,
) -> PersonaNarrative:
    evidence_summary = render_evidence_summary(evidence)
    evidence_hash = compute_evidence_hash(evidence_summary)
    tier = decide_tier(evidence, settings.llm_tier_confidence_cutoff)

    cache_key = CacheKey(
        kpi_id=evidence.movement.kpi_id,
        period_start=str(evidence.movement.period_start),
        period_end=str(evidence.movement.period_end),
        evidence_hash=evidence_hash,
        persona_id=persona_id,
    )
    cached = cache.get(cache_key)
    if cached is not None:
        logger.info("narrative_cache_hit", kpi_id=evidence.movement.kpi_id, persona_id=persona_id)
        cache_hit_telemetry = (
            cached.llm_telemetry.model_copy(update={"cache_hit": True, "latency_ms": 0.0, "estimated_cost_usd": 0.0})
            if cached.llm_telemetry
            else None
        )
        return cached.model_copy(update={"llm_telemetry": cache_hit_telemetry})

    top_hypothesis = next(
        (h for h in evidence.hypotheses if h.id == evidence.top_hypothesis_id),
        evidence.hypotheses[0] if evidence.hypotheses else None,
    )
    action_recs = recommend_actions(top_hypothesis.drivers, top_hypothesis.confidence) if top_hypothesis else []
    action_lines = [
        f"- Driver '{a.driver}': lever={a.controllable_lever}; action={a.action}; "
        f"expected_impact={a.expected_impact}; owner={a.owner}; monitoring={a.monitoring_plan}"
        for a in action_recs
    ]

    system_prompt = system_prompt_for_persona(persona_role, evidence.abstained)
    user_prompt = build_user_prompt(evidence, action_lines, persona_role)

    response = llm_client.complete(system_prompt, user_prompt, tier)
    narrative_text = response.text

    # Hard requirement, not a style preference: the regional-leader persona
    # must never see statistics jargon or a raw internal identifier
    # (driver/signal names). Small local models don't reliably follow that
    # instruction from the prompt alone, so this is a deterministic
    # guardrail, not an optional cleanup — see plain_language.py.
    used_fallback = False
    if persona_role != "analyst" and contains_jargon(narrative_text):
        logger.warning(
            "leader_narrative_jargon_detected_using_deterministic_fallback",
            kpi_id=evidence.movement.kpi_id,
            persona_id=persona_id,
            model=response.model,
        )
        narrative_text = build_plain_fallback_narrative(evidence)
        used_fallback = True

    # Grounding must check against EVERYTHING the LLM was actually given —
    # the evidence summary AND the rule-based action-playbook text (e.g.
    # "restores 30-50% of lost volume" is a legitimate number from the
    # static ACTION_PLAYBOOK table, not a hallucination, and must not be
    # flagged just because it lives in a different part of the prompt).
    # The deterministic fallback is grounded by construction (every number
    # in it is read directly from the evidence packet), so it isn't
    # re-checked — there's nothing an LLM invented left to verify.
    grounding = (
        check_grounding(narrative_text, evidence_summary + "\n" + render_action_context(action_lines))
        if not used_fallback
        else GroundingCheckResult(passed=True, checked_numbers=[], ungrounded_numbers=[])
    )

    for action in action_recs:
        action.llm_phrased_summary = None if used_fallback else _extract_relevant_sentence(response.text, action.driver)

    telemetry = LlmTelemetry(
        provider=response.provider,
        model=response.model,
        tier=response.tier,
        tokens_in=response.tokens_in,
        tokens_out=response.tokens_out,
        latency_ms=response.latency_ms,
        estimated_cost_usd=response.estimated_cost_usd,
        cache_hit=False,
        called_at=datetime.now(timezone.utc).isoformat(),
    )

    narrative = PersonaNarrative(
        persona_id=persona_id,
        persona_role=persona_role,
        headline=_first_sentence(narrative_text),
        narrative=narrative_text,
        recommended_actions=action_recs,
        grounding=grounding,
        llm_telemetry=telemetry,
    )
    cache.set(cache_key, narrative)
    logger.info(
        "narrative_generated",
        kpi_id=evidence.movement.kpi_id,
        persona_id=persona_id,
        tier=tier,
        prompt_version=PROMPT_VERSION,
        grounding_passed=grounding.passed,
        used_deterministic_fallback=used_fallback,
    )
    return narrative


def _first_sentence(text: str) -> str:
    # Defensive: strip a leading markdown header marker in case the model
    # ignores the "no markdown" prompt rule — otherwise "### Movement..."
    # gets treated as one run-on non-sentence.
    stripped = re.sub(r"^#{1,6}\s*", "", text.strip(), count=1)
    for sep in (". ", ".\n", "!\n", "! "):
        if sep in stripped:
            return stripped.split(sep)[0].strip() + "."
    return stripped[:160]


def _extract_relevant_sentence(text: str, driver_keyword: str) -> str | None:
    keyword = driver_keyword.replace("_", " ").split()[0]
    for sentence in text.replace("\n", " ").split(". "):
        if keyword.lower() in sentence.lower():
            return sentence.strip().rstrip(".") + "."
    return None
