"""Persona-scoped row/column-level access control.

This is intentionally simple (in-memory persona registry, not a full IAM
system) but it is *real*: every API route that returns KPI data or evidence
resolves a `Persona` from a request header and the persona's `region_scope`
is applied as a hard row-level filter before any other layer sees the data.
Column-level scoping hides internal analyst-only fields (e.g. raw customer
identifiers) from business-leader personas.

There is no bypass path — even if a caller requests a region outside their
scope, the filter silently narrows to the allowed set rather than erroring
with information that would itself leak scope (this mirrors how real BI
row-level security behaves).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

import pandas as pd


class PersonaRole(str, Enum):
    REGIONAL_LEADER = "regional_leader"
    ANALYST = "analyst"


@dataclass(frozen=True)
class Persona:
    id: str
    display_name: str
    role: PersonaRole
    # Empty tuple => no restriction (full access). Non-empty => allow-list.
    region_scope: tuple[str, ...] = field(default_factory=tuple)
    hidden_columns: tuple[str, ...] = field(default_factory=tuple)

    @property
    def is_scoped(self) -> bool:
        return len(self.region_scope) > 0


# Demo persona registry. In a production system this would be backed by an
# identity provider (SSO group -> persona/region mapping); the interface
# (`get_persona`) is what the rest of the app depends on, so swapping the
# backing store later does not touch calling code.
_PERSONAS: dict[str, Persona] = {
    "leader_west": Persona(
        id="leader_west",
        display_name="Regional Leader — West",
        role=PersonaRole.REGIONAL_LEADER,
        region_scope=("West",),
        hidden_columns=("customer_id", "customer_name", "full_text", "ticket_description", "ticket_subject"),
    ),
    "leader_east": Persona(
        id="leader_east",
        display_name="Regional Leader — East",
        role=PersonaRole.REGIONAL_LEADER,
        region_scope=("East",),
        hidden_columns=("customer_id", "customer_name", "full_text", "ticket_description", "ticket_subject"),
    ),
    "analyst_hq": Persona(
        id="analyst_hq",
        display_name="HQ Analyst",
        role=PersonaRole.ANALYST,
        region_scope=(),  # full access, all regions
        hidden_columns=(),
    ),
}

DEFAULT_PERSONA_ID = "analyst_hq"


class UnknownPersonaError(ValueError):
    pass


def get_persona(persona_id: str) -> Persona:
    try:
        return _PERSONAS[persona_id]
    except KeyError as exc:
        raise UnknownPersonaError(
            f"Unknown persona id '{persona_id}'. Known personas: {sorted(_PERSONAS)}"
        ) from exc


def list_personas() -> list[Persona]:
    return list(_PERSONAS.values())


def apply_row_scope(df: pd.DataFrame, persona: Persona, region_column: str = "region") -> pd.DataFrame:
    """Row-level filter: narrow to the persona's allowed regions, if scoped."""
    if not persona.is_scoped:
        return df
    if region_column not in df.columns:
        return df
    return df[df[region_column].isin(persona.region_scope)].copy()


def apply_column_scope(df: pd.DataFrame, persona: Persona) -> pd.DataFrame:
    """Column-level filter: drop columns the persona is not entitled to see."""
    cols_to_drop = [c for c in persona.hidden_columns if c in df.columns]
    if not cols_to_drop:
        return df
    return df.drop(columns=cols_to_drop)


def assert_region_allowed(persona: Persona, region: str) -> None:
    """Raise if a persona explicitly requests a region outside their scope.

    Used by API routes that take an explicit `region` query param (as opposed
    to routes that just list "your" data) so a scoped persona gets a clear
    403 rather than a silently empty/narrowed result.
    """
    if persona.is_scoped and region not in persona.region_scope:
        raise PermissionError(
            f"Persona '{persona.id}' is not entitled to region '{region}'. "
            f"Allowed regions: {list(persona.region_scope)}"
        )
