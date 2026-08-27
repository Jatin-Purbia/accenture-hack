import { useState, type ReactNode } from "react";
import type { PersonaOut } from "../types";

interface Props {
  personas: PersonaOut[];
  selectedId: string;
  onChange: (id: string) => void;
}

/** Two clearly labeled modes (Leader / Analyst) as the primary switch — the
 * region choice within Leader mode is a secondary control, so the region-
 * scoping requirement (a leader is scoped to one region) stays visible and
 * real without cluttering the primary toggle with a 3-way choice. */
export function PersonaToggle({ personas, selectedId, onChange }: Props) {
  const leaders = personas.filter((p) => p.role === "regional_leader");
  const analyst = personas.find((p) => p.role === "analyst");
  const current = personas.find((p) => p.id === selectedId);
  const mode: "leader" | "analyst" = current?.role === "analyst" ? "analyst" : "leader";

  const [lastLeaderId, setLastLeaderId] = useState(mode === "leader" ? selectedId : leaders[0]?.id ?? "");

  function pickLeader(id: string) {
    setLastLeaderId(id);
    onChange(id);
  }

  return (
    <div style={{ display: "flex", flexDirection: "column", alignItems: "flex-end", gap: 6 }}>
      <div className="eyebrow">Viewing as</div>
      <div style={{ display: "flex", background: "var(--surface-sunken)", borderRadius: 999, padding: 3, border: "1px solid var(--border)", gap: 2 }}>
        <ModeButton active={mode === "leader"} onClick={() => onChange(lastLeaderId || leaders[0]?.id)}>
          Leader view
        </ModeButton>
        {analyst && (
          <ModeButton active={mode === "analyst"} onClick={() => onChange(analyst.id)}>
            Analyst view
          </ModeButton>
        )}
      </div>

      {mode === "leader" && leaders.length > 1 && (
        <div style={{ display: "flex", gap: 4 }}>
          {leaders.map((p) => (
            <button
              key={p.id}
              onClick={() => pickLeader(p.id)}
              style={{
                padding: "3px 10px",
                borderRadius: 999,
                border: "1px solid var(--border)",
                background: p.id === selectedId ? "var(--brand-wash)" : "transparent",
                color: p.id === selectedId ? "var(--brand)" : "var(--text-muted)",
                fontSize: 11.5,
                fontWeight: 600,
              }}
            >
              {p.display_name.replace("Regional Leader — ", "")}
            </button>
          ))}
        </div>
      )}

      {current && (
        <span className="muted" style={{ fontSize: 11.5 }}>
          {current.region_scope.length > 0 ? `Scoped to: ${current.region_scope.join(", ")}` : "Unrestricted — all regions"}
        </span>
      )}
    </div>
  );
}

function ModeButton({ active, onClick, children }: { active: boolean; onClick: () => void; children: ReactNode }) {
  return (
    <button
      onClick={onClick}
      style={{
        padding: "6px 16px",
        borderRadius: 999,
        border: "none",
        fontSize: 13,
        fontWeight: 650,
        background: active ? "var(--surface-raised)" : "transparent",
        color: active ? "var(--brand)" : "var(--text-secondary)",
        boxShadow: active ? "var(--shadow-sm)" : "none",
      }}
    >
      {children}
    </button>
  );
}
