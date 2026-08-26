"""Reasoning-layer orchestrator — assembles a complete, typed EvidencePacket
for a (kpi_id, dimension) request by driving the Data -> Signal -> Reasoning
pipeline end to end. This is the ONLY module that touches every layer below
the Story layer; the API routers call this (and only this) to get an
EvidencePacket, then hand it to services/story for narration.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path

import pandas as pd

from app.core.logging import get_logger
from app.models.evidence import (
    CorrelationClass,
    CorrelationSignal,
    DataCompleteness,
    DriverContribution,
    EvidenceMethod,
    EvidencePacket,
    Hypothesis,
    KpiMovement,
    TrendPoint,
)
from app.models.kpi import KpiContract
from app.services.data.ingestion import (
    build_weekly_category_margin,
    build_weekly_subcategory_mix,
    load_raw_superstore,
    load_raw_support_tickets,
)
from app.services.reasoning.confidence import decide_abstention
from app.services.reasoning.correlation import evaluate_lag_correlation
from app.services.reasoning.driver_tree import DriverEffect, decompose_margin_mix_and_rate, decompose_sales_drivers
from app.services.reasoning.hypothesis_engine import build_hypotheses
from app.services.signal.anomaly import AnomalyResult, detect_anomaly, series_with_forecast_band
from app.services.signal.nlp_events import build_weekly_ticket_signals, extract_ticket_events

logger = get_logger(__name__)

WEEKS_REQUIRED_FOR_HIGH_CONFIDENCE = 26
ANOMALY_SCAN_LOOKBACK_WEEKS = 8
CORRELATION_LOOKBACK_WEEKS = 16
ALL_REGIONS = ("West", "East", "Central", "South")


class InsightNotFoundError(ValueError):
    pass


@dataclass
class DataStore:
    superstore: pd.DataFrame
    ticket_events: pd.DataFrame
    ticket_weekly: pd.DataFrame


@lru_cache
def load_data_store(raw_dir: Path) -> DataStore:
    superstore = load_raw_superstore(raw_dir)
    tickets = load_raw_support_tickets(raw_dir)
    events = extract_ticket_events(tickets)
    ticket_weekly = build_weekly_ticket_signals(events)
    logger.info(
        "data_store_loaded",
        superstore_rows=len(superstore),
        ticket_rows=len(tickets),
        ticket_weekly_rows=len(ticket_weekly),
    )
    return DataStore(superstore=superstore, ticket_events=events, ticket_weekly=ticket_weekly)


def _find_evaluation_period(series: pd.Series, materiality, lookback_weeks: int = ANOMALY_SCAN_LOOKBACK_WEEKS) -> AnomalyResult:
    """Scan the most recent `lookback_weeks` weeks and surface the most
    material one, preferring the MOST RECENT material week over the most
    statistically extreme one (this is a monitoring feed, not a historical
    search — a dashboard surfaces "what's material right now", not the
    single biggest blip anywhere in the last two months); if none are
    material, honestly return the latest week's (non-material) result
    rather than reaching further back to find a flag."""
    n = len(series)
    candidates: list[AnomalyResult] = []
    start = max(2, n - lookback_weeks)
    for i in range(start, n + 1):
        sub = series.iloc[:i]
        if len(sub) < 2:
            continue
        candidates.append(detect_anomaly(sub, materiality))
    if not candidates:
        return detect_anomaly(series, materiality)
    for result in reversed(candidates):  # most recent first
        if result.is_material:
            return result
    return candidates[-1]


def _build_trend_points(
    series: pd.Series, materiality, anomaly_period_start: pd.Timestamp, display_weeks: int = 14
) -> list[TrendPoint]:
    """Recent weekly history with a forecast band fit at EACH point (from
    that point's own prior history only — see anomaly.series_with_forecast_band)
    for the UI's trend chart. Bounded to a ~30-week compute window so this
    stays fast even though it re-fits a band at every displayed point."""
    windowed = series.loc[: anomaly_period_start].tail(30)
    if len(windowed) < 6:
        return []
    band_df = series_with_forecast_band(windowed, materiality)
    band_df = band_df.tail(display_weeks)
    return [
        TrendPoint(
            week_start=row.week_start.date(),
            actual=float(row.actual),
            expected=float(row.expected),
            band_low=float(row.band_low),
            band_high=float(row.band_high),
            is_material=bool(row.is_material),
        )
        for row in band_df.itertuples()
    ]


def _driver_effect_to_model(effect: DriverEffect) -> DriverContribution:
    return DriverContribution(
        driver=effect.driver,
        description=effect.description,
        contribution_value=effect.contribution_value,
        contribution_pct=effect.contribution_pct,
        direction=effect.direction,
        method=EvidenceMethod.DRIVER_TREE_DECOMPOSITION,
    )


def _correlation_finding_to_model(finding) -> CorrelationSignal:
    return CorrelationSignal(
        signal_name=finding.signal_name,
        source_kpi_id="weekly_ticket_volume_by_category",
        lag_weeks=finding.lag_weeks,
        correlation_coefficient=finding.correlation_coefficient,
        p_value=finding.p_value,
        classification=CorrelationClass(finding.classification),
        rationale=finding.rationale,
        method=EvidenceMethod.LAG_CORRELATION_TEST,
    )


def _run_ticket_correlations(
    store: DataStore, region: str | None, category: str, kpi_series: pd.Series, control_series: list[pd.Series]
) -> list[CorrelationSignal]:
    cat_tickets = store.ticket_weekly[store.ticket_weekly.category == category].set_index("week_start").sort_index()
    if cat_tickets.empty:
        return []
    findings = []
    for col in ("negative_share", "ticket_count", "mean_sentiment"):
        signal_series = cat_tickets[col].reindex(kpi_series.index).ffill().bfill()
        finding = evaluate_lag_correlation(
            kpi_series, signal_series, f"{category.lower().replace(' ', '_')}_{col}",
            control_kpi_series=control_series, lookback_weeks=CORRELATION_LOOKBACK_WEEKS,
        )
        findings.append(_correlation_finding_to_model(finding))
    return findings


def _build_hypothesis_models(drafts, weeks_of_history: int) -> tuple[list[Hypothesis], str | None, float | None, bool, str | None]:
    if not drafts:
        return [], None, None, True, "No hypotheses could be generated — insufficient evidence to explain this movement."

    decision = decide_abstention(
        [(d.id, d.confidence) for d in drafts], low_threshold=0.55, abstain_margin=0.12
    )
    hypotheses = [
        Hypothesis(
            id=d.id,
            label=d.label,
            summary=d.summary,
            drivers=[_driver_effect_to_model(e) for e in d.drivers],
            # d.correlations are already CorrelationSignal models — the
            # evidence builder converts findings to models BEFORE handing
            # them to build_hypotheses (hypothesis_engine only reads their
            # shared fields, so either representation works there; here we
            # just pass the already-typed models straight through).
            correlations=d.correlations,
            statistical_strength=d.statistical_strength,
            evidence_agreement=d.evidence_agreement,
            data_completeness_score=d.data_completeness,
            confidence=d.confidence,
        )
        for d in drafts
    ]
    return hypotheses, decision.top_hypothesis_id, decision.confidence_margin, decision.abstained, decision.reason


def build_sales_evidence(
    store: DataStore,
    contract: KpiContract,
    kpi_id: str,
    region: str | None,
    category: str,
    sub_category: str | None = None,
) -> EvidencePacket:
    kpi_def = contract.get(kpi_id)
    df = store.superstore
    # Filter to the requested slice, then ALWAYS aggregate to week_start
    # alone (region/category/sub_category are filters here, never a
    # preserved groupby key) — this is deliberately NOT reusing
    # ingestion.build_weekly_region_sales directly, since that function
    # keeps "region" in its groupby even when region=None, which would
    # leave one row PER REGION per week whenever a sub_category (like the
    # emerging-product scenario) spans multiple regions, corrupting the
    # time series with duplicate week_start entries.
    working = df
    if region is not None:
        working = working[working.region == region]
    if category is not None:
        working = working[working.category == category]
    if sub_category is not None:
        working = working[working.sub_category == sub_category]
    weekly = (
        working.groupby("week_start")
        .agg(sales=("sales", "sum"), quantity=("quantity", "sum"), discount=("discount", "mean"))
        .sort_index()
    )
    if weekly.empty:
        raise InsightNotFoundError(f"No data found for {kpi_id} region={region} category={category} sub_category={sub_category}")

    anomaly = _find_evaluation_period(weekly["sales"], kpi_def.materiality)
    eval_window = weekly.loc[: anomaly.period_start]

    drivers, _ = decompose_sales_drivers(eval_window["quantity"], eval_window["discount"], eval_window["sales"])

    control_series = []
    if region is not None:
        for other_region in ALL_REGIONS:
            if other_region == region:
                continue
            other = df[(df.region == other_region) & (df.category == category)]
            if sub_category is not None:
                other = other[other.sub_category == sub_category]
            s = other.groupby("week_start")["sales"].sum().sort_index().loc[: anomaly.period_start]
            if len(s) >= 10:
                control_series.append(s)

    correlations = _run_ticket_correlations(store, region, category, eval_window["sales"], control_series)

    drafts = build_hypotheses(drivers, correlations, anomaly.z_score, anomaly.weeks_of_history, WEEKS_REQUIRED_FOR_HIGH_CONFIDENCE)
    hypotheses, top_id, margin, abstained, reason = _build_hypothesis_models(drafts, anomaly.weeks_of_history)

    trend = _build_trend_points(weekly["sales"], kpi_def.materiality, anomaly.period_start)

    dimension_label = " / ".join(p for p in [region, category, sub_category] if p)
    return EvidencePacket(
        insight_id=f"{kpi_id}:{dimension_label}:{anomaly.period_start.date()}",
        trend=trend,
        movement=KpiMovement(
            kpi_id=kpi_id,
            kpi_name=kpi_def.name,
            dimension_label=dimension_label or "All",
            period_start=anomaly.period_start.date(),
            period_end=anomaly.period_end.date(),
            actual_value=anomaly.actual_value,
            expected_value=anomaly.expected_value,
            forecast_band_low=anomaly.band_low,
            forecast_band_high=anomaly.band_high,
            absolute_change=anomaly.absolute_change,
            relative_change_pct=anomaly.relative_change_pct,
            is_material=anomaly.is_material,
        ),
        hypotheses=hypotheses,
        top_hypothesis_id=top_id,
        confidence_margin=margin,
        abstained=abstained,
        abstention_reason=reason,
        data_completeness=DataCompleteness(
            weeks_of_history=anomaly.weeks_of_history,
            weeks_required_for_high_confidence=WEEKS_REQUIRED_FOR_HIGH_CONFIDENCE,
            missing_periods=0,
            source_freshness_days=1,
        ),
        lineage=kpi_def.lineage + [f"dimension slice: {dimension_label or 'All'}"],
        generated_at=datetime.now(timezone.utc).isoformat(),
    )


def build_margin_evidence(
    store: DataStore, contract: KpiContract, kpi_id: str, region: str | None, category: str
) -> EvidencePacket:
    kpi_def = contract.get(kpi_id)
    df = store.superstore
    margin_df = build_weekly_category_margin(df, region=region)
    margin_series = (
        margin_df[margin_df.category == category].set_index("week_start")["profit_margin_pct"].sort_index()
    )
    if margin_series.empty:
        raise InsightNotFoundError(f"No margin data for category={category} region={region}")

    anomaly = _find_evaluation_period(margin_series, kpi_def.materiality)

    mix_df = build_weekly_subcategory_mix(df, category=category, region=region)
    mix_window = mix_df[mix_df.week_start <= anomaly.period_start]
    drivers = decompose_margin_mix_and_rate(mix_window)

    control_series = []
    if region is not None:
        for other_region in ALL_REGIONS:
            if other_region == region:
                continue
            other_margin = build_weekly_category_margin(df, region=other_region)
            s = (
                other_margin[other_margin.category == category]
                .set_index("week_start")["profit_margin_pct"]
                .sort_index()
                .loc[: anomaly.period_start]
            )
            if len(s) >= 10:
                control_series.append(s)

    correlations = _run_ticket_correlations(store, region, category, margin_series.loc[: anomaly.period_start], control_series)

    drafts = build_hypotheses(drivers, correlations, anomaly.z_score, anomaly.weeks_of_history, WEEKS_REQUIRED_FOR_HIGH_CONFIDENCE)
    hypotheses, top_id, margin_gap, abstained, reason = _build_hypothesis_models(drafts, anomaly.weeks_of_history)

    trend = _build_trend_points(margin_series, kpi_def.materiality, anomaly.period_start)

    dimension_label = " / ".join(p for p in [region, category] if p)
    return EvidencePacket(
        trend=trend,
        insight_id=f"{kpi_id}:{dimension_label}:{anomaly.period_start.date()}",
        movement=KpiMovement(
            kpi_id=kpi_id,
            kpi_name=kpi_def.name,
            dimension_label=dimension_label or "All",
            period_start=anomaly.period_start.date(),
            period_end=anomaly.period_end.date(),
            actual_value=anomaly.actual_value,
            expected_value=anomaly.expected_value,
            forecast_band_low=anomaly.band_low,
            forecast_band_high=anomaly.band_high,
            absolute_change=anomaly.absolute_change,
            relative_change_pct=anomaly.relative_change_pct,
            is_material=anomaly.is_material,
        ),
        hypotheses=hypotheses,
        top_hypothesis_id=top_id,
        confidence_margin=margin_gap,
        abstained=abstained,
        abstention_reason=reason,
        data_completeness=DataCompleteness(
            weeks_of_history=anomaly.weeks_of_history,
            weeks_required_for_high_confidence=WEEKS_REQUIRED_FOR_HIGH_CONFIDENCE,
            missing_periods=0,
            source_freshness_days=1,
        ),
        lineage=kpi_def.lineage + [f"dimension slice: {dimension_label or 'All'}"],
        generated_at=datetime.now(timezone.utc).isoformat(),
    )


def get_sample_transactions(
    store: DataStore,
    region: str | None,
    category: str | None,
    sub_category: str | None,
    period_start,
    period_end,
    limit: int = 10,
) -> pd.DataFrame:
    """The most-impactful raw order lines behind an evaluated period — this
    is what the Evidence Viewer's "lineage back to raw data" panel shows,
    and what the API's column-level access control (core/access_control.py)
    actually redacts for a regional-leader persona (customer_id/
    customer_name are dropped before the response is serialized)."""
    df = store.superstore
    working = df[(df.order_date >= pd.Timestamp(period_start)) & (df.order_date <= pd.Timestamp(period_end))]
    if region is not None:
        working = working[working.region == region]
    if category is not None:
        working = working[working.category == category]
    if sub_category is not None:
        working = working[working.sub_category == sub_category]
    working = working.assign(_impact=working["sales"].abs()).sort_values("_impact", ascending=False)
    return working.drop(columns=["_impact"]).head(limit)
