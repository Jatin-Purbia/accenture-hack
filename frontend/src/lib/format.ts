/** KPI values are either dollars (sales) or percentage points (margin) —
 * one place to format either consistently across every chart. */
export function formatKpiValue(kpiId: string, value: number): string {
  if (kpiId.includes("margin")) return `${value.toFixed(1)}%`;
  const sign = value < 0 ? "-" : "";
  const abs = Math.abs(value);
  if (abs >= 1000) return `${sign}$${(abs / 1000).toFixed(0)}k`;
  return `${sign}$${abs.toFixed(0)}`;
}
