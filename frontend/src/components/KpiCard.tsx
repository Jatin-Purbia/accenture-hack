import { ArrowDown, ArrowUp, Minus } from "lucide-react";
import { kpiIcon } from "../lib/icons";
import { confidenceStatus, movementStatus, STATUS_COLOR, STATUS_WASH } from "../lib/status";
import type { EvidencePacket, ScenarioDef } from "../types";
import { Sparkline } from "./Sparkline";
import { StatusDot } from "./StatusDot";

interface Props {
  scenario: ScenarioDef;
  evidence: EvidencePacket;
  onClick: () => void;
}

/** A single glance: icon, big number + direction, sparkline against its
 * normal range, one confidence dot. No prose — click through for the story.
 * Anything needing attention (material + non-green) gets a colored ring so
 * it visually floats above routine cards without the user having to hunt. */
export function KpiCard({ scenario, evidence, onClick }: Props) {
  const Icon = kpiIcon(scenario.kpi_id);
  const m = evidence.movement;
  const status = movementStatus({
    isMaterial: m.is_material,
    relativeChangePct: m.relative_change_pct,
    abstained: evidence.abstained,
  });
  const topHypothesis = evidence.hypotheses.find((h) => h.id === evidence.top_hypothesis_id) ?? evidence.hypotheses[0];
  const confStatus = confidenceStatus(topHypothesis?.confidence ?? 0.5, evidence.abstained);
  const needsAttention = status === "critical" || status === "warning";

  const Arrow = m.relative_change_pct > 0.5 ? ArrowUp : m.relative_change_pct < -0.5 ? ArrowDown : Minus;
  const color = STATUS_COLOR[status];

  return (
    <button
      onClick={onClick}
      className="panel fade-in"
      style={{
        textAlign: "left",
        display: "flex",
        flexDirection: "column",
        gap: 12,
        border: needsAttention ? `1.5px solid ${color}` : "1px solid var(--border)",
        boxShadow: needsAttention ? `0 0 0 3px ${STATUS_WASH[status]}, var(--shadow-sm)` : "var(--shadow-sm)",
        position: "relative",
      }}
    >
      {needsAttention && (
        <div style={{ position: "absolute", top: -6, right: -6 }}>
          <StatusDot status={status} pulse size={11} />
        </div>
      )}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
        <div className="icon-badge" style={{ width: 34, height: 34, background: "var(--brand-wash)" }}>
          <Icon size={18} color="var(--brand)" strokeWidth={2} />
        </div>
        <div title={confStatus === "unknown" ? "Needs analyst review" : undefined}>
          <StatusDot status={confStatus} size={11} />
        </div>
      </div>

      <div>
        <div style={{ fontSize: 13.5, fontWeight: 650, marginBottom: 2 }}>{scenario.label}</div>
        <div className="muted" style={{ fontSize: 11.5 }}>
          {m.dimension_label}
        </div>
      </div>

      <div style={{ display: "flex", alignItems: "baseline", gap: 6 }}>
        <Arrow size={22} color={color} strokeWidth={2.5} />
        <span style={{ fontSize: 26, fontWeight: 700, color, letterSpacing: "-0.02em" }}>
          {Math.abs(m.relative_change_pct).toFixed(0)}%
        </span>
      </div>

      <Sparkline trend={evidence.trend} status={status} />
    </button>
  );
}
