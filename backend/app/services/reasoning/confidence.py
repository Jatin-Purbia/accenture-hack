"""Reasoning layer — confidence scoring and the abstention gate.

Confidence is a weighted combination of three independently-computed
signals (never a single number pulled from one source):

  - statistical_strength   how large/unusual the deviation is (z-score) and
                            how dominant the driver-tree's top driver is
                            relative to the others (a concentrated, clean
                            decomposition is more trustworthy than one where
                            many small effects roughly cancel out)
  - evidence_agreement      whether independent signals (driver direction,
                            correlation direction, control-group comparison)
                            point the same way, or contradict each other
  - data_completeness       how much history backs the estimate, and how
                            fresh the underlying source is

The abstention gate is a real decision function over these computed scores
— it is evaluated identically for every KPI movement the system processes,
not special-cased for any particular demo record. Whether it ends up
abstaining on a given real movement is a genuine property of that
movement's evidence, not a scripted outcome.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class ConfidenceInputs:
    statistical_strength: float  # 0-1
    evidence_agreement: float  # 0-1
    data_completeness: float  # 0-1


DEFAULT_WEIGHTS = (0.45, 0.30, 0.25)  # (statistical, agreement, completeness)


def compute_confidence(inputs: ConfidenceInputs, weights: tuple[float, float, float] = DEFAULT_WEIGHTS) -> float:
    w_stat, w_agree, w_complete = weights
    score = (
        w_stat * inputs.statistical_strength
        + w_agree * inputs.evidence_agreement
        + w_complete * inputs.data_completeness
    )
    return max(0.0, min(1.0, score))


def statistical_strength_from_zscore(z: float | None, cap: float = 4.0) -> float:
    """Normalize a z-score magnitude to [0, 1]. `cap` is the z-score treated
    as "maximally strong" (beyond it, additional deviation stops adding
    confidence — very large z-scores are already conclusive)."""
    if z is None:
        return 0.3  # no stable band could be fit (insufficient history) — neutral-low, not zero
    return max(0.0, min(1.0, abs(z) / cap))


def driver_concentration_strength(contribution_pcts: list[float]) -> float:
    """How dominant is the single largest driver relative to the rest?
    Uses a normalized Herfindahl-style concentration index over the absolute
    contribution shares — 1.0 if one driver explains ~100% of the movement,
    lower as multiple drivers of similar size compete to explain it.

    NOTE: multiple co-occurring real drivers (the multi-factor scenario)
    correctly produce a LOWER concentration score than a single dominant
    driver — this is intentional. Concentration measures how cleanly a
    single-cause story can be told, which is genuinely a different (and
    lower) thing than how well the total movement is explained.
    """
    abs_shares = [abs(p) / 100 for p in contribution_pcts if p is not None]
    if not abs_shares:
        return 0.0
    total = sum(abs_shares)
    if total <= 1e-9:
        return 0.0
    normalized = [s / total for s in abs_shares]
    herfindahl = sum(s**2 for s in normalized)
    n = len(normalized)
    # Rescale so a perfectly even split across n drivers -> 0, single driver -> 1
    floor = 1 / n
    return max(0.0, min(1.0, (herfindahl - floor) / (1 - floor))) if n > 1 else 1.0


def data_completeness_score(weeks_of_history: int, weeks_required: int) -> float:
    if weeks_required <= 0:
        return 1.0
    return max(0.0, min(1.0, weeks_of_history / weeks_required))


def agreement_score(direction_signals: list[int]) -> float:
    """`direction_signals` is a list of +1/-1/0 (0 = no signal / neutral).
    Returns the fraction of non-neutral signals that agree with the
    majority direction; 1.0 if all non-neutral signals agree, 0.5 if evenly
    split, and a neutral 0.5 if there are no non-neutral signals at all
    (nothing to agree or disagree with)."""
    non_neutral = [s for s in direction_signals if s != 0]
    if not non_neutral:
        return 0.5
    positive = sum(1 for s in non_neutral if s > 0)
    negative = len(non_neutral) - positive
    majority = max(positive, negative)
    return majority / len(non_neutral)


@dataclass
class AbstentionDecision:
    abstained: bool
    reason: str | None
    top_hypothesis_id: str | None
    confidence_margin: float | None


def decide_abstention(
    hypothesis_confidences: list[tuple[str, float]],
    low_threshold: float,
    abstain_margin: float,
) -> AbstentionDecision:
    """`hypothesis_confidences` is [(hypothesis_id, confidence), ...].

    Real decision function, evaluated the same way for every movement:
      1. No hypotheses at all -> abstain (nothing to say).
      2. Single hypothesis below the low-confidence threshold -> abstain.
      3. Multiple hypotheses whose top-2 confidence margin is below the
         abstain-margin threshold -> abstain and surface the competitors.
      4. Otherwise -> commit to the top hypothesis.
    """
    if not hypothesis_confidences:
        return AbstentionDecision(
            abstained=True,
            reason="No hypotheses could be generated from the available evidence.",
            top_hypothesis_id=None,
            confidence_margin=None,
        )

    ranked = sorted(hypothesis_confidences, key=lambda h: h[1], reverse=True)
    top_id, top_conf = ranked[0]

    if len(ranked) == 1:
        if top_conf < low_threshold:
            return AbstentionDecision(
                abstained=True,
                reason=(
                    f"Only one hypothesis was generated and its confidence "
                    f"({top_conf:.2f}) is below the low-confidence threshold "
                    f"({low_threshold:.2f})."
                ),
                top_hypothesis_id=top_id,
                confidence_margin=None,
            )
        return AbstentionDecision(abstained=False, reason=None, top_hypothesis_id=top_id, confidence_margin=None)

    second_conf = ranked[1][1]
    margin = top_conf - second_conf

    if top_conf < low_threshold:
        return AbstentionDecision(
            abstained=True,
            reason=(
                f"Top hypothesis confidence ({top_conf:.2f}) is below the low-confidence "
                f"threshold ({low_threshold:.2f})."
            ),
            top_hypothesis_id=top_id,
            confidence_margin=margin,
        )
    if margin < abstain_margin:
        return AbstentionDecision(
            abstained=True,
            reason=(
                f"Top hypothesis ({top_conf:.2f}) leads the runner-up ({second_conf:.2f}) by "
                f"only {margin:.2f}, below the {abstain_margin:.2f} margin required to commit "
                f"to a single explanation — evidence is genuinely contested."
            ),
            top_hypothesis_id=top_id,
            confidence_margin=margin,
        )

    return AbstentionDecision(abstained=False, reason=None, top_hypothesis_id=top_id, confidence_margin=margin)
