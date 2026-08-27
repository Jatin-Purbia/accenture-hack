import { formatKpiValue } from "../lib/format";
import type { EvidencePacket } from "../types";
import { AbstainPanel } from "./AbstainPanel";
import { DriverChip } from "./DriverChip";
import { DriverWaterfall } from "./DriverWaterfall";

interface Props {
  evidence: EvidencePacket;
  technical?: boolean;
}

/** Zone 2, "Why it changed". Abstained movements get the deliberately
 * distinct AbstainPanel instead — never the same layout with sadder text. */
export function CauseZone({ evidence, technical = false }: Props) {
  if (evidence.abstained) {
    return <AbstainPanel evidence={evidence} />;
  }

  const top = evidence.hypotheses.find((h) => h.id === evidence.top_hypothesis_id) ?? evidence.hypotheses[0];
  if (!top || top.drivers.length === 0) {
    return <p className="muted">No driver breakdown is available for this movement yet.</p>;
  }

  const m = evidence.movement;
  const formatter = (v: number) => formatKpiValue(m.kpi_id, v);

  return (
    <div>
      <DriverWaterfall
        startLabel="Expected"
        startValue={m.expected_value}
        endLabel="Actual"
        endValue={m.actual_value}
        drivers={top.drivers}
        valueFormatter={formatter}
      />
      <div style={{ display: "flex", flexDirection: "column", gap: 8, marginTop: 8 }}>
        {[...top.drivers]
          .sort((a, b) => Math.abs(b.contribution_pct) - Math.abs(a.contribution_pct))
          .map((d) => (
            <DriverChip key={d.driver} driver={d} confidence={top.confidence} technical={technical} />
          ))}
      </div>
    </div>
  );
}
