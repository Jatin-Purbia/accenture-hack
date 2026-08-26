"""Thin router — the curated demo scenario catalog, filtered to what the
requesting persona is entitled to see (row-level region scoping applied at
the catalog level, same rule the insights router enforces on the analysis
itself)."""
from __future__ import annotations

from fastapi import APIRouter, Depends

from app.core.access_control import Persona
from app.core.dependencies import persona_dependency
from app.services.data.scenario_catalog import ScenarioDef, scenarios_visible_to

router = APIRouter(prefix="/api/scenarios", tags=["scenarios"])


@router.get("", response_model=list[ScenarioDef])
def get_scenarios(persona: Persona = Depends(persona_dependency)) -> list[ScenarioDef]:
    return scenarios_visible_to(persona.region_scope)
