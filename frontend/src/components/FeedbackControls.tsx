import { useState } from "react";
import { api } from "../api/client";
import type { EvidencePacket, FeedbackVerdict } from "../types";

interface Props {
  evidence: EvidencePacket;
  personaId: string;
}

/** The analyst-feedback capture mechanism — real, append-only, wired to
 * POST /api/feedback. See docs/architecture.md "Feedback loop" for how this
 * would feed back into confidence calibration (a v2 roadmap item). */
export function FeedbackControls({ evidence, personaId }: Props) {
  const [submitted, setSubmitted] = useState<FeedbackVerdict | null>(null);
  const [note, setNote] = useState("");
  const [busy, setBusy] = useState(false);

  const hypothesisId = evidence.top_hypothesis_id ?? evidence.hypotheses[0]?.id ?? "none";

  async function submit(verdict: FeedbackVerdict) {
    setBusy(true);
    try {
      await api.submitFeedback(personaId, {
        kpi_id: evidence.movement.kpi_id,
        insight_id: evidence.insight_id,
        hypothesis_id: hypothesisId,
        persona_id: personaId,
        verdict,
        correction_note: note || undefined,
      });
      setSubmitted(verdict);
    } finally {
      setBusy(false);
    }
  }

  if (submitted) {
    return (
      <div className="panel" style={{ fontSize: 13 }}>
        Thanks — recorded as <strong>{submitted.replace("_", " ")}</strong>. This is appended to the
        analyst-feedback log used for future confidence calibration.
      </div>
    );
  }

  return (
    <div className="panel">
      <h3 style={{ fontSize: 14, marginTop: 0 }}>Do you agree with this explanation?</h3>
      <div style={{ display: "flex", gap: 8, marginBottom: 8 }}>
        <FeedbackButton label="Agree" onClick={() => submit("agree")} disabled={busy} color="var(--status-good)" />
        <FeedbackButton
          label="Partially agree"
          onClick={() => submit("partially_agree")}
          disabled={busy}
          color="var(--status-warning)"
        />
        <FeedbackButton
          label="Disagree"
          onClick={() => submit("disagree")}
          disabled={busy}
          color="var(--status-critical)"
        />
      </div>
      <textarea
        placeholder="Optional correction note…"
        value={note}
        onChange={(e) => setNote(e.target.value)}
        rows={2}
        style={{
          width: "100%",
          padding: 8,
          borderRadius: 6,
          border: "1px solid var(--border)",
          background: "var(--surface-raised)",
          color: "var(--text-primary)",
          fontFamily: "inherit",
          fontSize: 13,
          resize: "vertical",
        }}
      />
    </div>
  );
}

function FeedbackButton({
  label,
  onClick,
  disabled,
  color,
}: {
  label: string;
  onClick: () => void;
  disabled: boolean;
  color: string;
}) {
  return (
    <button
      onClick={onClick}
      disabled={disabled}
      style={{
        padding: "6px 14px",
        borderRadius: 6,
        border: `1px solid ${color}`,
        background: "transparent",
        color,
        fontSize: 13,
        fontWeight: 600,
      }}
    >
      {label}
    </button>
  );
}
