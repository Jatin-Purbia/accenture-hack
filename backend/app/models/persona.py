"""API-facing persona schema (a thin, non-sensitive view of core.access_control.Persona)."""
from __future__ import annotations

from pydantic import BaseModel


class PersonaOut(BaseModel):
    id: str
    display_name: str
    role: str
    region_scope: list[str]
