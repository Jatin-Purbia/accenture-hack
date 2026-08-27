import { Area, ComposedChart, Line, ResponsiveContainer } from "recharts";
import type { TrendPoint } from "../types";
import { STATUS_COLOR, type Status } from "../lib/status";

interface Props {
  trend: TrendPoint[];
  status: Status;
  height?: number;
}

/** A tiny history-at-a-glance chart for KPI cards — actual line over a
 * shaded "normal range" band, no axes/labels. The full annotated version
 * with labels/legend is TrendBand.tsx; this is deliberately bare so a grid
 * of these reads as a pattern-matching exercise, not N things to read. */
export function Sparkline({ trend, status, height = 44 }: Props) {
  if (trend.length === 0) {
    return <div style={{ height }} />;
  }
  const data = trend.map((t) => ({ actual: t.actual, band: [t.band_low, t.band_high] }));
  const color = STATUS_COLOR[status];

  return (
    <ResponsiveContainer width="100%" height={height}>
      <ComposedChart data={data} margin={{ top: 2, right: 2, left: 2, bottom: 2 }}>
        <Area dataKey="band" fill={color} fillOpacity={0.12} stroke="none" isAnimationActive={false} />
        <Line dataKey="actual" stroke={color} strokeWidth={2} dot={false} isAnimationActive={false} />
      </ComposedChart>
    </ResponsiveContainer>
  );
}
