import { Bar, BarChart, CartesianGrid, Cell, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import type { DriverContribution } from "../types";

interface Props {
  drivers: DriverContribution[];
}

/** Driver-tree decomposition — every bar sums to the total movement exactly
 * (LMDI / mix-rate decomposition, see backend services/reasoning/driver_tree.py).
 * Color encodes direction (helped vs. hurt the KPI), never rank. */
export function DriverBreakdown({ drivers }: Props) {
  const data = [...drivers]
    .sort((a, b) => Math.abs(b.contribution_pct) - Math.abs(a.contribution_pct))
    .map((d) => ({
      name: d.driver.replace(/_/g, " "),
      pct: d.contribution_pct,
      direction: d.direction,
      description: d.description,
    }));

  return (
    <div>
      <ResponsiveContainer width="100%" height={Math.max(120, data.length * 56)}>
        <BarChart data={data} layout="vertical" margin={{ top: 4, right: 24, left: 8, bottom: 4 }}>
          <CartesianGrid stroke="var(--gridline)" horizontal={false} />
          <XAxis
            type="number"
            stroke="var(--text-muted)"
            tick={{ fill: "var(--text-muted)", fontSize: 12 }}
            tickFormatter={(v) => `${v}%`}
          />
          <YAxis
            type="category"
            dataKey="name"
            stroke="var(--text-muted)"
            tick={{ fill: "var(--text-primary)", fontSize: 13 }}
            width={140}
          />
          <Tooltip
            contentStyle={{
              background: "var(--surface-raised)",
              border: "1px solid var(--border)",
              borderRadius: 8,
              fontSize: 13,
              maxWidth: 280,
            }}
            formatter={(value: number) => [`${value.toFixed(1)}%`, "Contribution to movement"]}
          />
          <Bar dataKey="pct" radius={4}>
            {data.map((d, i) => (
              <Cell key={i} fill={d.direction === "increase" ? "var(--delta-good)" : "var(--status-critical)"} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
      <ul style={{ margin: "8px 0 0", paddingLeft: 18, fontSize: 13 }} className="secondary">
        {data.map((d, i) => (
          <li key={i} style={{ marginBottom: 4 }}>
            <strong style={{ textTransform: "capitalize" }}>{d.name}</strong>: {d.description}
          </li>
        ))}
      </ul>
    </div>
  );
}
