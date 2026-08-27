import { useState } from "react";
import { ChevronDown, FileText } from "lucide-react";
import type { PersonaNarrative } from "../types";

interface Props {
  narrative: PersonaNarrative;
  defaultOpen?: boolean;
}

function stripMarkdown(text: string): string {
  return text
    .replace(/^#{1,6}\s*/gm, "")
    .replace(/\*\*(.*?)\*\*/g, "$1")
    .replace(/^\s*[-*]\s+/gm, "");
}

/** The LLM's written narrative — deliberately secondary in this design
 * (text is a caption, never the primary explanation; the visual zones
 * carry that weight). Collapsed by default so it never competes with the
 * chart/waterfall/action-card for attention; the grounding badge lives
 * right on the toggle so trust status is visible without opening it. */
export function AnalysisNotes({ narrative, defaultOpen = false }: Props) {
  const [open, setOpen] = useState(defaultOpen);
  const grounding = narrative.grounding;

  return (
    <div className="panel" style={{ padding: 0, overflow: "hidden" }}>
      <button
        onClick={() => setOpen((o) => !o)}
        style={{ width: "100%", display: "flex", justifyContent: "space-between", alignItems: "center", padding: "14px 20px", background: "none", border: "none", textAlign: "left" }}
      >
        <span style={{ display: "flex", alignItems: "center", gap: 8, fontSize: 13.5, fontWeight: 650 }}>
          <FileText size={15} className="muted" />
          Written analysis
        </span>
        <span style={{ display: "flex", alignItems: "center", gap: 10 }}>
          <span
            style={{
              fontSize: 11.5,
              fontWeight: 650,
              padding: "3px 9px",
              borderRadius: 999,
              background: grounding.passed ? "var(--status-good-wash)" : "var(--status-warning-wash)",
              color: grounding.passed ? "var(--status-good)" : "#8a5a00",
            }}
          >
            {grounding.passed ? "Verified" : `${grounding.ungrounded_numbers.length} unverified`}
          </span>
          <ChevronDown size={14} className="muted" style={{ transform: open ? "rotate(180deg)" : "none", transition: "transform 0.15s ease" }} />
        </span>
      </button>
      {open && (
        <div className="fade-in secondary" style={{ padding: "0 20px 18px", fontSize: 13.5, lineHeight: 1.6, borderTop: "1px solid var(--gridline)" }}>
          <p style={{ paddingTop: 14, margin: 0, whiteSpace: "pre-wrap" }}>{stripMarkdown(narrative.narrative)}</p>
        </div>
      )}
    </div>
  );
}
