import {
  Area,
  CartesianGrid,
  ComposedChart,
  Line,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { movementStatus, STATUS_COLOR } from "../lib/status";
import type { EvidencePacket } from "../types";

interface Props {
  evidence: EvidencePacket;
  /** Analyst mode keeps "forecast band" style labels; leader mode reads in
   * plain language ("normal range"). Default: plain language. */
  technical?: boolean;
}

function directionCaption(evidence: EvidencePacket, technical: boolean): string {
  const m = evidence.movement;
  const direction = m.relative_change_pct < 0 ? "dropped" : "rose";
  const pct = Math.abs(m.relative_change_pct).toFixed(0);
  if (!m.is_material) {
    return `${m.dimension_label} is within its normal range this week.`;
  }
  const band = technical ? "outside the forecast band" : "outside the normal range";
  return `${m.dimension_label} ${direction} ${pct}% ${band}.`;
}

/** Zone 1, "What changed": actual vs. the forecast band fit from each
 * point's own prior history, with the evaluated (material) week marked. A
 * plain-language caption sits ABOVE the chart — the reader gets the
 * takeaway before they even look at the shape. */
export function TrendBand({ evidence, technical = false }: Props) {
  const { trend, movement } = evidence;
  const status = movementStatus({
    isMaterial: movement.is_material,
    relativeChangePct: movement.relative_change_pct,
    abstained: evidence.abstained,
  });
  const markerColor = STATUS_COLOR[status];

  if (trend.length === 0) {
    return <div className="muted">Not enough history yet to chart a trend for this item.</div>;
  }

  const data = trend.map((t) => ({
    week: t.week_start,
    actual: t.actual,
    expected: t.expected,
    band: [t.band_low, t.band_high],
    isEvaluated: t.week_start === movement.period_start,
  }));

  const formatValue = (v: number) => (Math.abs(v) >= 1000 ? `${(v / 1000).toFixed(1)}k` : v.toFixed(1));

  return (
    <div>
      <p style={{ fontSize: 16, fontWeight: 600, margin: "0 0 14px" }}>{directionCaption(evidence, technical)}</p>
      <div style={{ display: "flex", gap: 20, marginBottom: 10, fontSize: 12.5, flexWrap: "wrap" }}>
        <Legend swatch="var(--series-1)" label="What happened" />
        <Legend swatch="var(--series-2)" label={technical ? "Forecast baseline" : "What we expected"} dashed />
        <Legend swatch="var(--band-fill)" label={technical ? "Forecast band" : "Normal range"} />
      </div>
      <ResponsiveContainer width="100%" height={220}>
        <ComposedChart data={data} margin={{ top: 8, right: 16, left: 0, bottom: 0 }}>
          <CartesianGrid stroke="var(--gridline)" vertical={false} />
          <XAxis dataKey="week" stroke="var(--text-muted)" tick={{ fill: "var(--text-muted)", fontSize: 11 }} />
          <YAxis
            stroke="var(--text-muted)"
            tick={{ fill: "var(--text-muted)", fontSize: 12 }}
            tickFormatter={formatValue}
            width={52}
          />
          <Tooltip
            contentStyle={{
              background: "var(--surface-raised)",
              border: "1px solid var(--border)",
              borderRadius: 8,
              fontSize: 13,
            }}
            formatter={(value: number | string, name: string) => [typeof value === "number" ? formatValue(value) : value, name]}
          />
          <Area dataKey="band" fill="var(--band-fill)" stroke="none" isAnimationActive={false} name="Normal range" />
          <Line
            dataKey="expected"
            stroke="var(--series-2)"
            strokeWidth={2}
            strokeDasharray="5 4"
            dot={false}
            isAnimationActive={false}
            name="Expected"
          />
          <Line
            dataKey="actual"
            stroke="var(--series-1)"
            strokeWidth={2.5}
            dot={(props) => {
              const isEval = data[props.index]?.isEvaluated;
              return (
                <circle
                  key={`dot-${props.index}`}
                  cx={props.cx}
                  cy={props.cy}
                  r={isEval ? 6.5 : 3}
                  fill={isEval ? markerColor : "var(--series-1)"}
                  stroke={isEval ? "var(--surface-1)" : "none"}
                  strokeWidth={isEval ? 2 : 0}
                />
              );
            }}
            isAnimationActive={false}
            name="Actual"
          />
        </ComposedChart>
      </ResponsiveContainer>
    </div>
  );
}

function Legend({ swatch, label, dashed }: { swatch: string; label: string; dashed?: boolean }) {
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
      <span
        style={{
          width: 14,
          height: dashed ? 2 : 10,
          background: dashed ? "none" : swatch,
          borderTop: dashed ? `2px dashed ${swatch}` : "none",
          borderRadius: dashed ? 0 : 3,
          display: "inline-block",
        }}
      />
      <span className="secondary">{label}</span>
    </div>
  );
}
