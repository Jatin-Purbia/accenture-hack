import { confidenceLabel, confidenceStatus, STATUS_COLOR, STATUS_WASH } from "../lib/status";

interface Props {
  confidence: number;
  abstained?: boolean;
  showPercent?: boolean;
}

export function ConfidenceBadge({ confidence, abstained = false, showPercent = false }: Props) {
  const status = confidenceStatus(confidence, abstained);
  const label = confidenceLabel(confidence, abstained);
  return (
    <span
      style={{
        display: "inline-flex",
        alignItems: "center",
        gap: 6,
        padding: "4px 12px",
        borderRadius: 999,
        fontSize: 12.5,
        fontWeight: 650,
        background: STATUS_WASH[status],
        color: STATUS_COLOR[status],
        whiteSpace: "nowrap",
      }}
    >
      <span style={{ width: 7, height: 7, borderRadius: "50%", background: STATUS_COLOR[status] }} />
      {label}
      {showPercent && !abstained ? ` (${(confidence * 100).toFixed(0)}%)` : ""}
    </span>
  );
}
