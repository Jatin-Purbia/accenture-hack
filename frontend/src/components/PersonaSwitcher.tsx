import type { PersonaOut } from "../types";

interface Props {
  personas: PersonaOut[];
  selectedId: string;
  onChange: (id: string) => void;
}

export function PersonaSwitcher({ personas, selectedId, onChange }: Props) {
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
      <span className="muted" style={{ fontSize: 12, textTransform: "uppercase", letterSpacing: "0.03em" }}>
        Viewing as
      </span>
      <select
        value={selectedId}
        onChange={(e) => onChange(e.target.value)}
        style={{
          padding: "8px 10px",
          borderRadius: 8,
          border: "1px solid var(--border)",
          background: "var(--surface-raised)",
          color: "var(--text-primary)",
          fontSize: 14,
        }}
      >
        {personas.map((p) => (
          <option key={p.id} value={p.id}>
            {p.display_name}
          </option>
        ))}
      </select>
      {(() => {
        const persona = personas.find((p) => p.id === selectedId);
        if (!persona) return null;
        return (
          <span className="muted" style={{ fontSize: 12 }}>
            {persona.region_scope.length > 0
              ? `Scoped to: ${persona.region_scope.join(", ")}`
              : "Unrestricted access (all regions)"}
          </span>
        );
      })()}
    </div>
  );
}
