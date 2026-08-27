import { Bar, BarChart, CartesianGrid, Cell, LabelList, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import type { DriverContribution } from "../types";

interface Props {
  startLabel: string;
  startValue: number;
  endLabel: string;
  endValue: number;
  drivers: DriverContribution[];
  valueFormatter?: (v: number) => string;
}

interface Row {
  name: string;
  base: number;
  value: number;
  kind: "start" | "end" | "increase" | "decrease";
  raw: number;
}

function buildRows(props: Props): Row[] {
  const rows: Row[] = [{ name: props.startLabel, base: 0, value: props.startValue, kind: "start", raw: props.startValue }];
  let running = props.startValue;
  const ranked = [...props.drivers].sort((a, b) => Math.abs(b.contribution_value) - Math.abs(a.contribution_value));
  for (const d of ranked) {
    const delta = d.contribution_value;
    if (delta >= 0) {
      rows.push({ name: d.driver.replace(/_/g, " "), base: running, value: delta, kind: "increase", raw: delta });
    } else {
      rows.push({ name: d.driver.replace(/_/g, " "), base: running + delta, value: -delta, kind: "decrease", raw: delta });
    }
    running += delta;
  }
  rows.push({ name: props.endLabel, base: 0, value: props.endValue, kind: "end", raw: props.endValue });
  return rows;
}

const KIND_COLOR: Record<Row["kind"], string> = {
  start: "var(--text-muted)",
  end: "var(--brand)",
  increase: "var(--delta-good)",
  decrease: "var(--status-critical)",
};

/** The "why it changed" bridge chart: start value -> each driver's
 * contribution (colored by whether it helped or hurt) -> end value. Bars
 * sum exactly (LMDI / mix-rate decomposition — see backend driver_tree.py),
 * so this is a literal picture of the math, not an illustration of it. */
export function DriverWaterfall({ valueFormatter = (v) => v.toFixed(0), ...props }: Props) {
  const rows = buildRows(props);

  return (
    <ResponsiveContainer width="100%" height={240}>
      <BarChart data={rows} margin={{ top: 24, right: 16, left: 0, bottom: 0 }}>
        <CartesianGrid stroke="var(--gridline)" vertical={false} />
        <XAxis dataKey="name" stroke="var(--text-muted)" tick={{ fill: "var(--text-primary)", fontSize: 12 }} interval={0} />
        <YAxis
          stroke="var(--text-muted)"
          tick={{ fill: "var(--text-muted)", fontSize: 12 }}
          tickFormatter={valueFormatter}
          width={56}
        />
        <Tooltip
          contentStyle={{
            background: "var(--surface-raised)",
            border: "1px solid var(--border)",
            borderRadius: 8,
            fontSize: 13,
          }}
          // The invisible "base" stacking series would otherwise add its
          // own (meaningless) row to the tooltip — filter to just the
          // visible "value" (contribution) entry.
          content={({ active, payload }) => {
            if (!active || !payload?.length) return null;
            const entry = payload.find((p) => p.dataKey === "value");
            const row = entry?.payload as Row | undefined;
            if (!row) return null;
            const isTotal = row.kind === "start" || row.kind === "end";
            return (
              <div
                style={{
                  background: "var(--surface-raised)",
                  border: "1px solid var(--border)",
                  borderRadius: 8,
                  fontSize: 13,
                  padding: "8px 12px",
                }}
              >
                <div style={{ fontWeight: 600, marginBottom: 2 }}>{row.name}</div>
                <div className="secondary">
                  {isTotal ? "Value" : "Contribution"}: {!isTotal && row.raw >= 0 ? "+" : ""}
                  {valueFormatter(row.raw)}
                </div>
              </div>
            );
          }}
        />
        <Bar dataKey="base" stackId="bridge" fill="transparent" isAnimationActive={false} />
        <Bar dataKey="value" stackId="bridge" radius={4} isAnimationActive={false}>
          {rows.map((row, i) => (
            <Cell key={i} fill={KIND_COLOR[row.kind]} />
          ))}
          <LabelList
            dataKey="raw"
            position="top"
            formatter={(v: number) => {
              const isTotal = v === props.startValue || v === props.endValue;
              return `${!isTotal && v >= 0 ? "+" : ""}${valueFormatter(v)}`;
            }}
            style={{ fontSize: 11, fill: "var(--text-secondary)" }}
          />
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}
