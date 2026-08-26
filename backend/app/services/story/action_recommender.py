"""Story layer — rule-based action recommendation.

Per the brief: driver -> controllable lever -> action -> expected impact ->
owner -> confidence -> monitoring plan. This entire structure is a static
lookup table keyed by (driver, direction) — the LLM is never asked to invent
a lever or action; its only involvement (in narrative_service.py) is
phrasing a one-sentence summary of an ALREADY-DECIDED recommendation for the
target persona's tone.
"""
from __future__ import annotations

from dataclasses import dataclass

from app.models.insight import ActionRecommendation
from app.services.reasoning.driver_tree import DriverEffect

MATERIAL_DRIVER_FLOOR_PCT = 15.0


@dataclass(frozen=True)
class ActionTemplate:
    controllable_lever: str
    action: str
    expected_impact: str
    owner: str
    monitoring_plan: str


ACTION_PLAYBOOK: dict[tuple[str, str], ActionTemplate] = {
    ("quantity_effect", "decrease"): ActionTemplate(
        controllable_lever="Demand generation / merchandising",
        action=(
            "Investigate the volume decline with the category/regional sales team; "
            "review recent stock-outs, competitor activity, and marketing cadence for "
            "the affected segment."
        ),
        expected_impact="Recovering a fixable cause (stock-out, promo gap) typically restores 30-50% of lost unit volume within 4-6 weeks.",
        owner="Regional Sales Leader",
        monitoring_plan="Track weekly unit volume for the affected region/category against the forecast band for 6 weeks.",
    ),
    ("quantity_effect", "increase"): ActionTemplate(
        controllable_lever="Demand generation / merchandising",
        action="Document what drove the volume increase (promotion, seasonality, channel shift) so it can be repeated deliberately.",
        expected_impact="Sustain the incremental volume by codifying the driver into the next planning cycle.",
        owner="Regional Sales Leader",
        monitoring_plan="Continue tracking weekly volume; flag if it reverts to the prior baseline.",
    ),
    ("discount_effect", "decrease"): ActionTemplate(
        controllable_lever="Discount / pricing governance",
        action="Review discount approval thresholds for the affected category/region; confirm recent discounting was intentional and within policy.",
        expected_impact="Recovering half the excess discount back to baseline typically restores roughly half of the associated sales/margin impact.",
        owner="Pricing / Category Manager",
        monitoring_plan="Track weekly average discount rate for the affected slice against its historical baseline.",
    ),
    ("discount_effect", "increase"): ActionTemplate(
        controllable_lever="Discount / pricing governance",
        action="Confirm the lower discounting is sustainable and not suppressing volume before treating it as a pure win.",
        expected_impact="Maintain current margin improvement while watching for offsetting volume softness.",
        owner="Pricing / Category Manager",
        monitoring_plan="Track weekly discount rate alongside unit volume for the same slice.",
    ),
    ("avg_price_effect", "decrease"): ActionTemplate(
        controllable_lever="List pricing",
        action="Review list-price changes and product mix within the category for unintended average selling-price erosion.",
        expected_impact="Restoring list pricing to baseline would directly recover the associated sales dollars.",
        owner="Pricing / Category Manager",
        monitoring_plan="Track weekly average unit price for the affected slice.",
    ),
    ("avg_price_effect", "increase"): ActionTemplate(
        controllable_lever="List pricing",
        action="Confirm the price increase is not driving customers away before relying on it as a sustained gain.",
        expected_impact="Maintain the incremental revenue while monitoring volume and ticket-sentiment signals.",
        owner="Pricing / Category Manager",
        monitoring_plan="Track weekly average unit price alongside unit volume and ticket sentiment.",
    ),
    ("cost_mix_effect", "decrease"): ActionTemplate(
        controllable_lever="Product mix / merchandising",
        action="Review merchandising and promotional placement driving the shift toward lower-margin sub-categories; consider rebalancing promotion toward higher-margin lines.",
        expected_impact="Shifting a meaningful share of volume back toward the prior mix recovers roughly proportional margin points.",
        owner="Category Manager",
        monitoring_plan="Track weekly sales-share by sub-category within the category against its baseline distribution.",
    ),
    ("cost_mix_effect", "increase"): ActionTemplate(
        controllable_lever="Product mix / merchandising",
        action="Document what drove the shift toward higher-margin sub-categories so it can be reinforced.",
        expected_impact="Sustain the mix improvement by continuing the current merchandising approach.",
        owner="Category Manager",
        monitoring_plan="Continue tracking weekly sales-share by sub-category.",
    ),
    ("margin_rate_effect", "decrease"): ActionTemplate(
        controllable_lever="Discount / pricing governance",
        action="Audit recent discount approvals within the category for policy adherence — this is typically the largest lever on within-category margin rate.",
        expected_impact="Tightening discounting back to baseline directly recovers the associated margin points.",
        owner="Pricing / Category Manager",
        monitoring_plan="Track weekly category-level average discount rate and margin percentage together.",
    ),
    ("margin_rate_effect", "increase"): ActionTemplate(
        controllable_lever="Discount / pricing governance",
        action="Confirm the margin improvement is not being achieved by under-discounting in a way that risks volume.",
        expected_impact="Maintain the margin gain while watching sales volume for offsetting softness.",
        owner="Pricing / Category Manager",
        monitoring_plan="Track weekly margin percentage alongside sales volume.",
    ),
}


def recommend_actions(drivers: list[DriverEffect], confidence: float) -> list[ActionRecommendation]:
    """One ActionRecommendation per material driver (>= MATERIAL_DRIVER_FLOOR_PCT).
    `confidence` is the owning hypothesis's overall confidence score."""
    recommendations = []
    for driver in drivers:
        if abs(driver.contribution_pct) < MATERIAL_DRIVER_FLOOR_PCT:
            continue
        template = ACTION_PLAYBOOK.get((driver.driver, driver.direction))
        if template is None:
            continue
        recommendations.append(
            ActionRecommendation(
                driver=driver.driver,
                controllable_lever=template.controllable_lever,
                action=template.action,
                expected_impact=template.expected_impact,
                owner=template.owner,
                confidence=confidence,
                monitoring_plan=template.monitoring_plan,
                llm_phrased_summary=None,
            )
        )
    return recommendations
