import { useEffect, useState, type ReactNode } from "react";
import type { PersonaOut } from "../types";

interface Props {
  personas: PersonaOut[];
  selectedId: string;
  onChange: (id: string) => void;
}

export function PersonaToggle({ personas, selectedId, onChange }: Props) {
  const leaders = personas.filter((persona) => persona.role === "regional_leader");
  const analyst = personas.find((persona) => persona.role === "analyst");
  const current = personas.find((persona) => persona.id === selectedId);
  const mode: "leader" | "analyst" = current?.role === "analyst" ? "analyst" : "leader";
  const [lastLeaderId, setLastLeaderId] = useState(selectedId);

  useEffect(() => {
    if (current?.role === "regional_leader") setLastLeaderId(current.id);
  }, [current]);

  function showLeader() {
    const nextId = leaders.some((leader) => leader.id === lastLeaderId) ? lastLeaderId : leaders[0]?.id;
    if (nextId) onChange(nextId);
  }

  return (
    <div className="persona-controls" aria-label="View controls">
      <span className="persona-label">Viewing as</span>
      <div className="mode-switch">
        <ModeButton active={mode === "leader"} onClick={showLeader}>Leader</ModeButton>
        {analyst && <ModeButton active={mode === "analyst"} onClick={() => onChange(analyst.id)}>Analyst</ModeButton>}
      </div>
      {mode === "leader" && leaders.length > 1 && (
        <select
          className="region-select"
          aria-label="Region"
          value={selectedId}
          onChange={(event) => {
            setLastLeaderId(event.target.value);
            onChange(event.target.value);
          }}
        >
          {leaders.map((persona) => (
            <option key={persona.id} value={persona.id}>{persona.region_scope.join(", ") || persona.display_name}</option>
          ))}
        </select>
      )}
    </div>
  );
}

function ModeButton({ active, onClick, children }: { active: boolean; onClick: () => void; children: ReactNode }) {
  return (
    <button className={active ? "mode-button active" : "mode-button"} onClick={onClick} aria-pressed={active}>
      {children}
    </button>
  );
}
