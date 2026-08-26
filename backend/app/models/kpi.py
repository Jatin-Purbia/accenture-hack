"""Pydantic schemas mirroring the KPI semantic contract (docs/kpi_contract.yaml).

These are read-side models: the YAML file is the source of truth, this
module just gives the rest of the app (and the API layer) a typed view of it.
"""
from __future__ import annotations

from pydantic import BaseModel, Field


class MaterialityThresholds(BaseModel):
    min_absolute_change_usd: float | None = None
    min_absolute_change_pp: float | None = None
    min_absolute_change_count: float | None = None
    min_absolute_change: float | None = None
    min_relative_change_pct: float
    note: str | None = None


class AccessRestrictions(BaseModel):
    row_level: str
    column_level: str


class KpiDefinition(BaseModel):
    id: str
    name: str
    definition: str
    formula: str
    grain: str
    dimensions: list[str]
    source: str
    refresh_cadence: str
    owner: str
    materiality: MaterialityThresholds
    drivers: list[str]
    access_restrictions: AccessRestrictions
    lineage: list[str]


class PersonaContractEntry(BaseModel):
    id: str
    role: str
    region_scope: list[str] = Field(default_factory=list)


class KpiContract(BaseModel):
    kpis: list[KpiDefinition]
    personas: list[PersonaContractEntry]

    def get(self, kpi_id: str) -> KpiDefinition:
        for k in self.kpis:
            if k.id == kpi_id:
                return k
        raise KeyError(f"KPI '{kpi_id}' not found in contract")
