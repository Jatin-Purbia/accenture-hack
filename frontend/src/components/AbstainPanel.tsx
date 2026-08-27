import { CircleHelp } from "lucide-react";
import type { EvidencePacket } from "../types";
import { ConfidenceMeter } from "./ConfidenceMeter";

interface Props {
  evidence: EvidencePacket;
}

/** The abstained state must look deliberately different from a confident
 * result — not "the same card, sadder text." Dashed borders, muted tone,
 * a "?" motif: this reads as the system being honest, a feature, not a
 * failure — never styled like an error state. */
export function AbstainPanel({ evidence }: Props) {
  return (
    <div className="abstain-card fade-in">
      <div style={{ display: "flex", gap: 12, alignItems: "flex-start", marginBottom: 18 }}>
        <div className="icon-badge" style={{ width: 36, height: 36, background: "var(--status-unknown-wash)", flex: "none" }}>
          <CircleHelp size={19} color="var(--text-muted)" strokeWidth={2} />
        </div>
        <div>
          <p style={{ margin: 0, fontSize: 15.5, fontWeight: 650 }}>Not confident enough to pick one explanation</p>
          <p className="secondary" style={{ margin: "4px 0 0", fontSize: 13.5, maxWidth: 560 }}>
            {evidence.abstention_reason ?? "Two explanations are equally well supported by the evidence so far."}
          </p>
        </div>
      </div>

      <div style={{ display: "flex", gap: 14, flexWrap: "wrap" }}>
        {evidence.hypotheses.map((h) => (
          <div
            key={h.id}
            style={{
              flex: "1 1 220px",
              minWidth: 220,
              background: "var(--surface-1)",
              border: "1px dashed var(--border-strong)",
              borderRadius: "var(--radius-sm)",
              padding: "14px 16px",
            }}
          >
            <div style={{ fontWeight: 650, fontSize: 14, marginBottom: 6 }}>{h.label}</div>
            <p className="secondary" style={{ fontSize: 12.5, margin: "0 0 10px" }}>
              {h.summary}
            </p>
            <ConfidenceMeter confidence={h.confidence} width={100} />
          </div>
        ))}
      </div>

      <p className="muted" style={{ fontSize: 12.5, marginTop: 16, marginBottom: 0 }}>
        Flagged for analyst review rather than acted on automatically — see the Evidence panel below for what
        additional data would help resolve this.
      </p>
    </div>
  );
}
