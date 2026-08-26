"""Loads the KPI semantic contract (docs/kpi_contract.yaml) into typed
Pydantic models. This is the ONLY place that reads the YAML file — every
other module (signal, reasoning, story, api) depends on this registry
rather than parsing YAML itself.
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

import yaml

from app.models.kpi import KpiContract


@lru_cache
def load_kpi_contract(docs_path: Path) -> KpiContract:
    contract_path = docs_path / "kpi_contract.yaml"
    if not contract_path.exists():
        raise FileNotFoundError(
            f"KPI contract not found at {contract_path}. This file is the "
            f"single source of truth for KPI definitions and must exist."
        )
    with contract_path.open("r", encoding="utf-8") as f:
        raw = yaml.safe_load(f)
    return KpiContract.model_validate(raw)
