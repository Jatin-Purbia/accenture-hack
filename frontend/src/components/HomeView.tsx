import { useEffect, useState } from "react";
import { api } from "../api/client";
import { movementStatus } from "../lib/status";
import type { EvidencePacket, ScenarioDef } from "../types";
import { KpiCard } from "./KpiCard";
import { SkeletonCard } from "./SkeletonCard";

interface Props {
  scenarios: ScenarioDef[];
  personaId: string;
  onSelect: (scenarioId: string) => void;
}

const RANK: Record<string, number> = { critical: 0, warning: 1, unknown: 2, good: 3 };

/** The KPI Command Center — a grid, not a table. Every card fetches its
 * evidence (fast, no LLM call) in parallel so the whole grid paints in
 * well under a second; cards needing attention float to the front as their
 * evidence arrives. */
export function HomeView({ scenarios, personaId, onSelect }: Props) {
  const [evidenceMap, setEvidenceMap] = useState<Record<string, EvidencePacket>>({});

  useEffect(() => {
    setEvidenceMap({});
    const controller = new AbortController();
    scenarios.forEach((s) => {
      api
        .getScenarioEvidence(s.id, personaId, controller.signal)
        .then((ev) => setEvidenceMap((prev) => ({ ...prev, [s.id]: ev })))
        .catch(() => {
          /* a scenario the persona can't reach shouldn't be in this list at all (server-filtered),
             and an aborted (superseded) request is expected — swallow defensively either way so
             one bad card doesn't blank the grid */
        });
    });
    return () => {
      controller.abort();
    };
  }, [scenarios, personaId]);

  const sorted = [...scenarios].sort((a, b) => {
    const rank = (s: ScenarioDef) => {
      const ev = evidenceMap[s.id];
      if (!ev) return 4;
      return RANK[movementStatus({ isMaterial: ev.movement.is_material, relativeChangePct: ev.movement.relative_change_pct, abstained: ev.abstained })];
    };
    return rank(a) - rank(b);
  });

  return (
    <div>
      <div className="eyebrow" style={{ marginBottom: 4 }}>
        KPI Command Center
      </div>
      <h1 style={{ margin: "0 0 20px", fontSize: 22 }}>What needs your attention</h1>
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(230px, 1fr))", gap: 16 }}>
        {sorted.map((s) =>
          evidenceMap[s.id] ? (
            <KpiCard key={s.id} scenario={s} evidence={evidenceMap[s.id]} onClick={() => onSelect(s.id)} />
          ) : (
            <SkeletonCard key={s.id} />
          )
        )}
      </div>
    </div>
  );
}
