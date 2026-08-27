import { driverIcon, driverLabel } from "../lib/icons";
import type { DriverContribution } from "../types";
import { ConfidenceMeter } from "./ConfidenceMeter";

interface Props {
  driver: DriverContribution;
  confidence: number;
  technical?: boolean;
}

/** Icon + name + contribution % + a confidence bar — a compact card, never
 * a paragraph. This is the "ranked list of drivers" from the why-it-changed
 * zone, one chip per driver. */
export function DriverChip({ driver, confidence, technical = false }: Props) {
  const Icon = driverIcon(driver.driver);
  const helped = driver.direction === "increase";
  const color = helped ? "var(--delta-good)" : "var(--status-critical)";

  return (
    <div
      className="panel"
      style={{ display: "flex", alignItems: "center", gap: 12, padding: "12px 16px" }}
      title={technical ? driver.description : undefined}
    >
      <div className="icon-badge" style={{ width: 32, height: 32, background: "var(--surface-sunken)", flex: "none" }}>
        <Icon size={16} color="var(--text-secondary)" strokeWidth={2} />
      </div>
      <div style={{ flex: 1, minWidth: 0 }}>
        <div style={{ fontSize: 13.5, fontWeight: 650, textTransform: "capitalize" }}>{driverLabel(driver.driver, technical)}</div>
        <ConfidenceMeter confidence={confidence} width={70} />
      </div>
      <div style={{ fontSize: 15, fontWeight: 700, color, flex: "none" }}>
        {driver.contribution_pct >= 0 ? "+" : ""}
        {driver.contribution_pct.toFixed(0)}%
      </div>
    </div>
  );
}
