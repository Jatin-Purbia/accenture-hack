"""Thin router — exposes the KPI semantic contract (docs/kpi_contract.yaml)
to the frontend, satisfying the "contract viewable in the UI" requirement."""
from __future__ import annotations

from fastapi import APIRouter, Depends

from app.core.dependencies import kpi_contract_dependency
from app.models.kpi import KpiContract

router = APIRouter(prefix="/api/kpis", tags=["kpis"])


@router.get("", response_model=KpiContract)
def get_kpi_contract(contract: KpiContract = Depends(kpi_contract_dependency)) -> KpiContract:
    return contract
  