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
import type { EvidencePacket } from "../types";

interface Props {
  evidence: EvidencePacket;
}

/**
 * Recent weekly history for the evaluated slice, each point shown against
 * the forecast band fit from ITS OWN prior history (not a single static
 * band) — the same method the Signal layer's anomaly detector uses. The
 * evaluated period (the one the narrative explains) is marked with a
 * reference dot.
 */
export function KpiTrendChart({ evidence }: Props) {
  const { trend, movement } = evidence;

  if (trend.length === 0) {
    return <div className="muted">Not enough history to render a trend band for this slice.</div>;
  }

  const data = trend.map((t) => ({
    week: t.week_start,
    actual: t.actual,
    expected: t.expected,
    band: [t.band_low, t.band_high],
    isEvaluated: t.week_start === movement.period_start,
  }));

  const formatValue = (v: number) =>
    Math.abs(v) >= 1000 ? `${(v / 1000).toFixed(1)}k` : v.toFixed(1);

  return (
    <div>
      <div style={{ display: "flex", gap: 20, marginBottom: 12, fontSize: 13 }}>
        <Legend swatch="var(--series-1)" label="Actual" />
        <Legend swatch="var(--series-2)" label="Expected (forecast baseline)" dashed />
        <Legend swatch="var(--band-fill)" label="Forecast band" />
      </div>
      <ResponsiveContainer width="100%" height={240}>
        <ComposedChart data={data} margin={{ top: 8, right: 16, left: 0, bottom: 0 }}>
          <CartesianGrid stroke="var(--gridline)" vertical={false} />
          <XAxis
            dataKey="week"
            stroke="var(--text-muted)"
            tick={{ fill: "var(--text-muted)", fontSize: 11 }}
          />
          <YAxis
            stroke="var(--text-muted)"
            tick={{ fill: "var(--text-muted)", fontSize: 12 }}
            tickFormatter={formatValue}
            width={56}
          />
          <Tooltip
            contentStyle={{
              background: "var(--surface-raised)",
              border: "1px solid var(--border)",
              borderRadius: 8,
              fontSize: 13,
            }}
            formatter={(value: number | string, name: string) => [
              typeof value === "number" ? formatValue(value) : value,
              name,
            ]}
          />
          <Area dataKey="band" fill="var(--band-fill)" stroke="none" isAnimationActive={false} name="Forecast band" />
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
            strokeWidth={2}
            dot={(props) => {
              const isEval = data[props.index]?.isEvaluated;
              return (
                <circle
                  key={`dot-${props.index}`}
                  cx={props.cx}
                  cy={props.cy}
                  r={isEval ? 6 : 3}
                  fill={isEval ? "var(--status-critical)" : "var(--series-1)"}
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
      <div className="secondary" style={{ marginTop: 8, fontSize: 13 }}>
        Evaluated period: <strong>{movement.period_start}</strong> to {movement.period_end} —{" "}
        {movement.dimension_label} (highlighted point)
      </div>
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
