import { CalendarClock, Database, ShieldCheck, User } from "lucide-react";
import { kpiIcon } from "../lib/icons";
import type { KpiDefinition } from "../types";

interface Props {
  kpi: KpiDefinition;
}

/** The KPI semantic contract as a scannable visual card — icon for the
 * source system, cadence as a clock, owner, access-scope badge — rather
 * than a raw table/YAML dump. */
export function ContractCard({ kpi }: Props) {
  const Icon = kpiIcon(kpi.id);
  return (
    <div className="panel" style={{ display: "flex", flexDirection: "column", gap: 12 }}>
      <div style={{ display: "flex", gap: 12, alignItems: "flex-start" }}>
        <div className="icon-badge" style={{ width: 36, height: 36, background: "var(--brand-wash)", flex: "none" }}>
          <Icon size={19} color="var(--brand)" strokeWidth={2} />
        </div>
        <div>
          <div style={{ fontWeight: 650, fontSize: 15 }}>{kpi.name}</div>
          <p className="secondary" style={{ fontSize: 12.5, margin: "4px 0 0" }}>
            {kpi.definition}
          </p>
        </div>
      </div>

      <div style={{ display: "flex", flexWrap: "wrap", gap: 8 }}>
        <Fact icon={Database} text={kpi.source.replace(/_/g, " ")} />
        <Fact icon={CalendarClock} text={kpi.refresh_cadence} />
        <Fact icon={User} text={kpi.owner} />
        <Fact icon={ShieldCheck} text={kpi.access_restrictions.row_level.split(",")[0]} />
      </div>

      <div className="muted" style={{ fontSize: 12 }}>
        Drivers tracked: {kpi.drivers.map((d) => d.replace(/_/g, " ")).join(", ")}
      </div>
    </div>
  );
}

function Fact({ icon: Icon, text }: { icon: typeof Database; text: string }) {
  return (
    <span
      style={{
        display: "inline-flex",
        alignItems: "center",
        gap: 6,
        padding: "4px 10px",
        borderRadius: 999,
        background: "var(--surface-sunken)",
        fontSize: 11.5,
        color: "var(--text-secondary)",
      }}
    >
      <Icon size={12} />
      {text}
    </span>
  );
}
