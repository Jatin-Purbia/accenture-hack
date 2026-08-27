import { confidenceStatus, STATUS_COLOR } from "../lib/status";

interface Props {
  confidence: number;
  abstained?: boolean;
  width?: number;
}

/** A small horizontal fill-bar gauge — used on driver chips and hypothesis
 * cards where a shape reads faster than "Confidence 67%" as text. */
export function ConfidenceMeter({ confidence, abstained = false, width = 64 }: Props) {
  const status = confidenceStatus(confidence, abstained);
  const color = STATUS_COLOR[status];
  const pct = abstained ? 100 : Math.max(4, confidence * 100);

  return (
    <div style={{ display: "inline-flex", alignItems: "center", gap: 6 }}>
      <div
        style={{
          width,
          height: 5,
          borderRadius: 999,
          background: "var(--gridline)",
          overflow: "hidden",
          flex: "none",
        }}
      >
        <div
          style={{
            width: `${pct}%`,
            height: "100%",
            background: abstained
              ? `repeating-linear-gradient(45deg, ${color}, ${color} 3px, transparent 3px, transparent 6px)`
              : color,
            borderRadius: 999,
          }}
        />
      </div>
    </div>
  );
}
