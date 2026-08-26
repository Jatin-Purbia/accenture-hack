"""A small, curated catalog of demo scenario slices (KPI + dimension combo).

This curates WHICH slices are presented as navigable "cases" in the UI — it
does not curate or alter the ANALYSIS, which remains fully computed by the
Signal/Reasoning layers for whatever slice is requested (the API also
exposes an unrestricted `/api/insights/custom` path for arbitrary
region/category/sub_category combinations; this catalog is a curated
shortlist, not the only valid input). Analogous to a BI tool shipping a set
of pre-built dashboard views on top of a general query engine.
"""
from __future__ import annotations

from pydantic import BaseModel


class ScenarioDef(BaseModel):
    id: str
    kpi_id: str
    label: str
    description: str
    region: str | None = None
    category: str | None = None
    sub_category: str | None = None


SCENARIOS: list[ScenarioDef] = [
    ScenarioDef(
        id="west_technology_drop",
        kpi_id="weekly_sales_by_region",
        label="West Region — Technology Sales Drop",
        description=(
            "Multi-factor decline: both lower unit volume AND increased discounting "
            "contribute materially, correctly decomposed by the driver tree."
        ),
        region="West",
        category="Technology",
    ),
    ScenarioDef(
        id="central_office_supplies_margin",
        kpi_id="weekly_profit_margin_by_category",
        label="Central — Office Supplies Margin Compression",
        description=(
            "Ambiguous: a cost-mix shift and a within-category discounting effect are "
            "comparably well supported by the evidence — the system abstains and shows "
            "both competing hypotheses rather than picking a winner."
        ),
        region="Central",
        category="Office Supplies",
    ),
    ScenarioDef(
        id="emerging_3d_printers",
        kpi_id="weekly_sales_by_subcategory_emerging",
        label="Emerging Sub-Category — 3D Printers",
        description=(
            "A newly launched product line with only ~6 weeks of history — confidence "
            "is capped by data completeness rather than by any statistical ambiguity."
        ),
        category="Technology",
        sub_category="3D Printers",
    ),
    ScenarioDef(
        id="west_region_overview",
        kpi_id="weekly_sales_by_region",
        label="West Region — Sales Overview",
        description="Baseline region view for the West regional-leader persona.",
        region="West",
    ),
    ScenarioDef(
        id="east_region_overview",
        kpi_id="weekly_sales_by_region",
        label="East Region — Sales Overview",
        description="Baseline region view — used to demonstrate persona-based region access scoping.",
        region="East",
    ),
]


def get_scenario(scenario_id: str) -> ScenarioDef:
    for s in SCENARIOS:
        if s.id == scenario_id:
            return s
    raise KeyError(f"Unknown scenario id '{scenario_id}'. Known: {[s.id for s in SCENARIOS]}")


def scenarios_visible_to(region_scope: tuple[str, ...]) -> list[ScenarioDef]:
    if not region_scope:
        return list(SCENARIOS)
    return [s for s in SCENARIOS if s.region is None or s.region in region_scope]
