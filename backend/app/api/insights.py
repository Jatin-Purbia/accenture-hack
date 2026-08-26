"""Insights router — the API's main endpoint. For a given scenario (or an
arbitrary custom dimension slice) and the requesting persona, builds the
full EvidencePacket (Data -> Signal -> Reasoning) and a single persona-
scoped narrative (Story layer), enforcing row-level region access control
before any analysis is even run.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query

from app.core.access_control import Persona, apply_column_scope
from app.core.config import Settings
from app.core.dependencies import (
    data_store_dependency,
    feedback_store_dependency,
    kpi_contract_dependency,
    llm_client_dependency,
    narrative_cache_dependency,
    persona_dependency,
    settings_dependency,
    telemetry_log_dependency,
)
from app.models.evidence import EvidencePacket
from app.models.insight import Insight
from app.models.kpi import KpiContract
from app.services.data.scenario_catalog import get_scenario
from app.services.reasoning.evidence_builder import (
    DataStore,
    InsightNotFoundError,
    build_margin_evidence,
    build_sales_evidence,
    get_sample_transactions,
)
from app.services.story.cache import NarrativeCache
from app.services.story.llm_client import LLMClient
from app.services.story.narrative_service import generate_persona_narrative
from app.services.story.telemetry_log import TelemetryLog

router = APIRouter(prefix="/api/insights", tags=["insights"])

_MARGIN_KPI_IDS = {"weekly_profit_margin_by_category"}


def _build_evidence(
    store: DataStore, contract: KpiContract, kpi_id: str, region: str | None, category: str | None, sub_category: str | None
) -> EvidencePacket:
    try:
        if kpi_id in _MARGIN_KPI_IDS:
            if category is None:
                raise HTTPException(status_code=400, detail="category is required for margin KPIs")
            return build_margin_evidence(store, contract, kpi_id, region, category)
        return build_sales_evidence(store, contract, kpi_id, region=region, category=category, sub_category=sub_category)
    except InsightNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


def _enforce_region_access(persona: Persona, region: str | None) -> None:
    if region is not None and persona.is_scoped and region not in persona.region_scope:
        raise HTTPException(
            status_code=403,
            detail=(
                f"Persona '{persona.id}' is scoped to {list(persona.region_scope)} and is not "
                f"entitled to view region '{region}'."
            ),
        )


def _respond(
    evidence: EvidencePacket,
    persona: Persona,
    llm_client: LLMClient,
    cache: NarrativeCache,
    settings: Settings,
    telemetry_log: TelemetryLog,
) -> Insight:
    narrative = generate_persona_narrative(
        evidence=evidence,
        persona_id=persona.id,
        persona_role=persona.role.value,
        llm_client=llm_client,
        cache=cache,
        settings=settings,
    )
    if narrative.llm_telemetry:
        telemetry_log.record(narrative.llm_telemetry)
    return Insight(
        insight_id=evidence.insight_id,
        kpi_id=evidence.movement.kpi_id,
        evidence=evidence,
        narratives={persona.id: narrative},
    )


@router.get("/{scenario_id}", response_model=Insight)
def get_scenario_insight(
    scenario_id: str,
    persona: Persona = Depends(persona_dependency),
    store: DataStore = Depends(data_store_dependency),
    contract: KpiContract = Depends(kpi_contract_dependency),
    llm_client: LLMClient = Depends(llm_client_dependency),
    cache: NarrativeCache = Depends(narrative_cache_dependency),
    settings: Settings = Depends(settings_dependency),
    telemetry_log: TelemetryLog = Depends(telemetry_log_dependency),
) -> Insight:
    try:
        scenario = get_scenario(scenario_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    _enforce_region_access(persona, scenario.region)
    evidence = _build_evidence(store, contract, scenario.kpi_id, scenario.region, scenario.category, scenario.sub_category)
    return _respond(evidence, persona, llm_client, cache, settings, telemetry_log)


@router.get("/custom/query", response_model=Insight)
def get_custom_insight(
    kpi_id: str = Query(...),
    region: str | None = Query(default=None),
    category: str | None = Query(default=None),
    sub_category: str | None = Query(default=None),
    persona: Persona = Depends(persona_dependency),
    store: DataStore = Depends(data_store_dependency),
    contract: KpiContract = Depends(kpi_contract_dependency),
    llm_client: LLMClient = Depends(llm_client_dependency),
    cache: NarrativeCache = Depends(narrative_cache_dependency),
    settings: Settings = Depends(settings_dependency),
    telemetry_log: TelemetryLog = Depends(telemetry_log_dependency),
) -> Insight:
    _enforce_region_access(persona, region)
    evidence = _build_evidence(store, contract, kpi_id, region, category, sub_category)
    return _respond(evidence, persona, llm_client, cache, settings, telemetry_log)


@router.get("/{scenario_id}/sample-records")
def get_sample_records(
    scenario_id: str,
    persona: Persona = Depends(persona_dependency),
    store: DataStore = Depends(data_store_dependency),
    contract: KpiContract = Depends(kpi_contract_dependency),
) -> list[dict]:
    """Raw order lines behind the scenario's evaluated period — the
    Evidence Viewer's "lineage back to raw data" drill-down. Column-level
    access control is applied here concretely: a regional-leader persona
    never receives customer_id/customer_name in the response body at all
    (not just hidden client-side)."""
    try:
        scenario = get_scenario(scenario_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    _enforce_region_access(persona, scenario.region)
    evidence = _build_evidence(store, contract, scenario.kpi_id, scenario.region, scenario.category, scenario.sub_category)

    records = get_sample_transactions(
        store,
        region=scenario.region,
        category=scenario.category,
        sub_category=scenario.sub_category,
        period_start=evidence.movement.period_start,
        period_end=evidence.movement.period_end,
    )
    records = apply_column_scope(records, persona)
    return records.assign(order_date=records["order_date"].astype(str)).to_dict(orient="records")
