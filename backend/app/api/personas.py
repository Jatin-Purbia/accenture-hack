"""Thin router — persona listing for the frontend's persona switcher."""
from __future__ import annotations

from fastapi import APIRouter

from app.core.access_control import list_personas
from app.models.persona import PersonaOut

router = APIRouter(prefix="/api/personas", tags=["personas"])


@router.get("", response_model=list[PersonaOut])
def get_personas() -> list[PersonaOut]:
    return [
        PersonaOut(id=p.id, display_name=p.display_name, role=p.role.value, region_scope=list(p.region_scope))
        for p in list_personas()
    ]
