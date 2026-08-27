import { STATUS_COLOR, STATUS_LABEL, type Status } from "../lib/status";

interface Props {
  status: Status;
  size?: number;
  pulse?: boolean;
}

/** A single colored dot — no label. Used where the spec calls for
 * "a confidence dot, no explanation text needed at this level" (KPI cards).
 * The title attribute carries the label for anyone who hovers/inspects. */
export function StatusDot({ status, size = 10, pulse = false }: Props) {
  const color = STATUS_COLOR[status];
  return (
    <span
      title={STATUS_LABEL[status]}
      style={{
        position: "relative",
        display: "inline-flex",
        width: size,
        height: size,
        flex: "none",
      }}
    >
      {pulse && (
        <span
          style={{
            position: "absolute",
            inset: 0,
            borderRadius: "50%",
            background: color,
            opacity: 0.5,
            animation: "status-pulse 1.6s ease-out infinite",
          }}
        />
      )}
      <span style={{ position: "relative", width: size, height: size, borderRadius: "50%", background: color }} />
    </span>
  );
}
