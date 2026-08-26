import type { ScenarioDef } from "../types";

interface Props {
  scenarios: ScenarioDef[];
  selectedId: string | null;
  onSelect: (id: string) => void;
}

export function ScenarioList({ scenarios, selectedId, onSelect }: Props) {
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
      <span className="muted" style={{ fontSize: 12, textTransform: "uppercase", letterSpacing: "0.03em" }}>
        Scenarios
      </span>
      {scenarios.map((s) => (
        <button
          key={s.id}
          onClick={() => onSelect(s.id)}
          style={{
            textAlign: "left",
            padding: "10px 12px",
            borderRadius: 8,
            border: "1px solid var(--border)",
            background: selectedId === s.id ? "color-mix(in srgb, var(--series-1) 12%, transparent)" : "var(--surface-raised)",
            borderColor: selectedId === s.id ? "var(--series-1)" : "var(--border)",
            color: "var(--text-primary)",
          }}
        >
          <div style={{ fontWeight: 600, fontSize: 13 }}>{s.label}</div>
          <div className="muted" style={{ fontSize: 12, marginTop: 2 }}>
            {s.description}
          </div>
        </button>
      ))}
      {scenarios.length === 0 && <span className="muted" style={{ fontSize: 13 }}>No scenarios visible to this persona.</span>}
    </div>
  );
}
