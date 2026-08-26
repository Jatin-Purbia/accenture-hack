"""Story layer — narrative response cache.

Keyed on (kpi_id, period, evidence content hash, persona, tier) so an
identical question (same KPI/period/persona) is only re-sent to the LLM if
the underlying evidence actually changed — this is the concrete
implementation of the brief's "avoid redundant LLM calls" requirement.

In-memory, process-lifetime only. A production deployment handling "tens of
thousands of interactions per week" (see README "Scaling") would swap this
for Redis with a TTL — the interface here (`get`/`set` on a content hash)
is what would carry over; only the storage backend would change.
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass

from app.models.insight import PersonaNarrative


def compute_evidence_hash(evidence_summary_text: str) -> str:
    return hashlib.sha256(evidence_summary_text.encode("utf-8")).hexdigest()[:16]


@dataclass
class CacheKey:
    kpi_id: str
    period_start: str
    period_end: str
    evidence_hash: str
    persona_id: str

    def as_str(self) -> str:
        return f"{self.kpi_id}|{self.period_start}|{self.period_end}|{self.evidence_hash}|{self.persona_id}"


class NarrativeCache:
    def __init__(self) -> None:
        self._store: dict[str, PersonaNarrative] = {}
        self.hits = 0
        self.misses = 0

    def get(self, key: CacheKey) -> PersonaNarrative | None:
        hit = self._store.get(key.as_str())
        if hit is not None:
            self.hits += 1
        else:
            self.misses += 1
        return hit

    def set(self, key: CacheKey, narrative: PersonaNarrative) -> None:
        self._store[key.as_str()] = narrative

    @property
    def size(self) -> int:
        return len(self._store)

    @property
    def hit_rate(self) -> float:
        total = self.hits + self.misses
        return (self.hits / total) if total else 0.0


_singleton: NarrativeCache | None = None


def get_narrative_cache() -> NarrativeCache:
    global _singleton
    if _singleton is None:
        _singleton = NarrativeCache()
    return _singleton
