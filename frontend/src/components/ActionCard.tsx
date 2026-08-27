import { useState } from "react";
import { Check, Megaphone, Package, RotateCcw, Tag, Users } from "lucide-react";
import { api } from "../api/client";
import type { ActionRecommendation, EvidencePacket } from "../types";

interface Props {
  evidence: EvidencePacket;
  action: ActionRecommendation;
  index: number;
  personaId: string;
}

function leverIcon(lever: string) {
  const l = lever.toLowerCase();
  if (l.includes("discount") || l.includes("pricing")) return Tag;
  if (l.includes("mix") || l.includes("merchandising")) return Package;
  if (l.includes("demand") || l.includes("generation")) return Megaphone;
  return Users;
}

function formatValue(v: number) {
  return Math.abs(v) >= 1000 ? `$${(v / 1000).toFixed(0)}k` : `$${v.toFixed(0)}`;
}

/** A real before/after visual grounded in the evidence itself — "current"
 * vs. "expected" (the gap this action targets closing) — rather than an
 * invented recovery number the backend never computed. */
function ImpactBars({ current, target }: { current: number; target: number }) {
  const max = Math.max(current, target, 1);
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 6, width: "100%", maxWidth: 220 }}>
      <BarRow label="Now" value={current} max={max} color="var(--status-critical)" />
      <BarRow label="Goal" value={target} max={max} color="var(--delta-good)" />
    </div>
  );
}

function BarRow({ label, value, max, color }: { label: string; value: number; max: number; color: string }) {
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 8, fontSize: 11.5 }}>
      <span className="muted" style={{ width: 32, flex: "none" }}>
        {label}
      </span>
      <div style={{ flex: 1, height: 8, background: "var(--gridline)", borderRadius: 999, overflow: "hidden" }}>
        <div style={{ width: `${(value / max) * 100}%`, height: "100%", background: color, borderRadius: 999 }} />
      </div>
      <span className="mono secondary" style={{ width: 50, textAlign: "right", flex: "none" }}>
        {formatValue(value)}
      </span>
    </div>
  );
}

export function ActionCard({ evidence, action, index, personaId }: Props) {
  const [verdict, setVerdict] = useState<"agree" | "disagree" | null>(null);
  const [showOverride, setShowOverride] = useState(false);
  const [note, setNote] = useState("");
  const [busy, setBusy] = useState(false);

  const Icon = leverIcon(action.controllable_lever);
  const hypothesisId = evidence.top_hypothesis_id ?? evidence.hypotheses[0]?.id ?? "none";

  async function submit(v: "agree" | "disagree") {
    setBusy(true);
    try {
      await api.submitFeedback(personaId, {
        kpi_id: evidence.movement.kpi_id,
        insight_id: evidence.insight_id,
        hypothesis_id: hypothesisId,
        persona_id: personaId,
        verdict: v,
        correction_note: v === "disagree" ? note || undefined : undefined,
      });
      setVerdict(v);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="panel fade-in" style={{ display: "flex", gap: 18, alignItems: "flex-start", flexWrap: "wrap" }}>
      <div className="icon-badge" style={{ width: 40, height: 40, background: "var(--brand-wash)", flex: "none" }}>
        <Icon size={20} color="var(--brand)" strokeWidth={2} />
      </div>

      <div style={{ flex: "1 1 260px", minWidth: 220 }}>
        {index === 0 && (
          <div className="eyebrow" style={{ color: "var(--brand)", marginBottom: 6 }}>
            Recommended action
          </div>
        )}
        <p style={{ margin: "0 0 8px", fontSize: 16, fontWeight: 600, lineHeight: 1.4 }}>{action.action}</p>
        <p className="secondary" style={{ margin: "0 0 10px", fontSize: 13.5 }}>
          {action.expected_impact}
        </p>
        <div className="muted" style={{ fontSize: 12 }}>
          Owner: <strong style={{ color: "var(--text-secondary)" }}>{action.owner}</strong>
        </div>
      </div>

      <ImpactBars current={evidence.movement.actual_value} target={evidence.movement.expected_value} />

      <div style={{ flex: "none", display: "flex", flexDirection: "column", gap: 8, minWidth: 140 }}>
        {verdict ? (
          <div
            style={{
              display: "flex",
              alignItems: "center",
              gap: 6,
              fontSize: 13,
              fontWeight: 600,
              color: verdict === "agree" ? "var(--status-good)" : "var(--text-secondary)",
            }}
          >
            <Check size={16} />
            {verdict === "agree" ? "Marked as done" : "Override recorded"}
          </div>
        ) : showOverride ? (
          <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
            <input
              value={note}
              onChange={(e) => setNote(e.target.value)}
              placeholder="What should happen instead?"
              style={{
                padding: "7px 10px",
                borderRadius: 8,
                border: "1px solid var(--border-strong)",
                background: "var(--surface-raised)",
                color: "var(--text-primary)",
                fontSize: 12.5,
              }}
            />
            <button className="btn" disabled={busy} onClick={() => submit("disagree")} style={{ fontSize: 12.5 }}>
              Submit override
            </button>
          </div>
        ) : (
          <>
            <button
              className="btn btn-primary"
              disabled={busy}
              onClick={() => submit("agree")}
              style={{ justifyContent: "center" }}
            >
              <Check size={15} /> Mark as done
            </button>
            <button
              className="btn"
              disabled={busy}
              onClick={() => setShowOverride(true)}
              style={{ justifyContent: "center" }}
            >
              <RotateCcw size={14} /> Override
            </button>
          </>
        )}
      </div>
    </div>
  );
}
