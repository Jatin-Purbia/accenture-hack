/** The ONE traffic-light system used everywhere in the app — KPI cards,
 * confidence dots/meters, alerts, action cards. Every component reads
 * color/label from here rather than re-deriving its own thresholds, so the
 * mapping only ever needs to change in one place. */
export type Status = "good" | "warning" | "critical" | "unknown";

export const STATUS_COLOR: Record<Status, string> = {
  good: "var(--status-good)",
  warning: "var(--status-warning)",
  critical: "var(--status-critical)",
  unknown: "var(--text-muted)",
};

export const STATUS_WASH: Record<Status, string> = {
  good: "var(--status-good-wash)",
  warning: "var(--status-warning-wash)",
  critical: "var(--status-critical-wash)",
  unknown: "var(--status-unknown-wash)",
};

export const STATUS_LABEL: Record<Status, string> = {
  good: "On track",
  warning: "Worth a look",
  critical: "Needs action",
  unknown: "Insufficient data",
};

/** Status for a KPI movement card: is this material, and which direction?
 * A material decline needs action (red); a material rise is worth a look
 * (amber, understand it so it can be repeated); nothing material is green.
 * An abstained/no-evidence movement is always grey, regardless of size. */
export function movementStatus(params: { isMaterial: boolean; relativeChangePct: number; abstained: boolean }): Status {
  if (params.abstained) return "unknown";
  if (!params.isMaterial) return "good";
  return params.relativeChangePct < 0 ? "critical" : "warning";
}

/** Status for a confidence value (a hypothesis, an action's backing
 * evidence). Abstained always reads as "unknown", never a low number. */
export function confidenceStatus(confidence: number, abstained: boolean): Status {
  if (abstained) return "unknown";
  if (confidence >= 0.75) return "good";
  if (confidence >= 0.55) return "warning";
  return "critical";
}

export function confidenceLabel(confidence: number, abstained: boolean): string {
  if (abstained) return "Needs analyst review";
  if (confidence >= 0.75) return "High confidence";
  if (confidence >= 0.55) return "Moderate confidence";
  return "Low confidence";
}
