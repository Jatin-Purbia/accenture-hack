import { useEffect, useState, type ReactNode } from "react";
import { ArrowLeft } from "lucide-react";
import { api, ApiError } from "../api/client";
import { movementStatus, STATUS_COLOR } from "../lib/status";
import type { EvidencePacket, Insight, ScenarioDef } from "../types";
import { ActionCard } from "./ActionCard";
import { AnalysisNotes } from "./AnalysisNotes";
import { CauseZone } from "./CauseZone";
import { ConfidenceBadge } from "./ConfidenceBadge";
import { EvidenceDrawer } from "./EvidenceDrawer";
import { TelemetryBadge } from "./TelemetryBadge";
import { TrendBand } from "./TrendBand";

interface Props {
  scenario: ScenarioDef;
  personaId: string;
  personaRole: string;
  onBack: () => void;
}

/** The KPI Story View: three visual zones, always in this order — What
 * changed -> Why it changed -> What to do — read top to bottom like a
 * comic strip, not a report. Same component for both personas; only the
 * vocabulary depth (technical=true for analyst) and which panels default
 * open differ. Evidence loads first and paints Zone 1 immediately; the
 * narrative/actions (the slow LLM step) fill in behind it. */
export function DetailView({ scenario, personaId, personaRole, onBack }: Props) {
  const [evidence, setEvidence] = useState<EvidencePacket | null>(null);
  const [insight, setInsight] = useState<Insight | null>(null);
  const [error, setError] = useState<string | null>(null);

  const technical = personaRole === "analyst";

  useEffect(() => {
    // A real AbortController, not just a "cancelled" flag: the narrative
    // call is an expensive LLM request (real cost, real latency). If the
    // scenario/persona changes (or in dev, React StrictMode's intentional
    // double-invoke of this effect) before it resolves, the superseded
    // request must actually be cancelled — otherwise it keeps running on
    // the server and burns a full LLM call nobody will ever see the result
    // of, which is exactly the wasted-spend this project is built to avoid.
    const controller = new AbortController();
    setEvidence(null);
    setInsight(null);
    setError(null);

    api.getScenarioEvidence(scenario.id, personaId, controller.signal).then(setEvidence).catch(() => {});

    api
      .getInsight(scenario.id, personaId, controller.signal)
      .then(setInsight)
      .catch((e) => {
        if (e instanceof DOMException && e.name === "AbortError") return;
        setError(e instanceof ApiError ? `${e.status === 403 ? "Access denied" : "Error"}: ${e.message}` : "Failed to load insight.");
      });

    return () => {
      controller.abort();
    };
  }, [scenario.id, personaId]);

  const displayEvidence = insight?.evidence ?? evidence;
  const narrative = insight?.narratives[personaId];

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>
      <button
        onClick={onBack}
        className="btn"
        style={{ alignSelf: "flex-start", background: "none", border: "none", padding: "4px 0", color: "var(--text-secondary)" }}
      >
        <ArrowLeft size={15} /> All KPIs
      </button>

      {error && (
        <div className="panel fade-in" style={{ borderColor: "var(--status-critical)", background: "var(--status-critical-wash)" }}>
          <strong style={{ color: "var(--status-critical)" }}>{error}</strong>
        </div>
      )}

      {!displayEvidence && !error && (
        <div className="panel" style={{ display: "flex", alignItems: "center", gap: 12 }}>
          <span className="spinner" />
          <span className="muted">Loading this KPI's story…</span>
        </div>
      )}

      {displayEvidence && (
        <>
          <Header evidence={displayEvidence} />

          <ZoneCard eyebrow="What changed">
            <TrendBand evidence={displayEvidence} technical={technical} />
          </ZoneCard>

          <ZoneCard eyebrow="Why it changed">
            {narrative ? (
              <CauseZone evidence={displayEvidence} technical={technical} />
            ) : (
              <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
                <div className="skeleton" style={{ height: 200 }} />
                <div className="skeleton" style={{ height: 48 }} />
                <div className="skeleton" style={{ height: 48 }} />
              </div>
            )}
          </ZoneCard>

          <ZoneCard eyebrow="What to do">
            {narrative ? (
              narrative.recommended_actions.length > 0 ? (
                <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
                  {narrative.recommended_actions.map((a, i) => (
                    <ActionCard key={i} evidence={displayEvidence} action={a} index={i} personaId={personaId} />
                  ))}
                </div>
              ) : (
                <p className="muted">No standard playbook action applies here — flagged for manual review.</p>
              )
            ) : (
              <div className="skeleton" style={{ height: 110 }} />
            )}
          </ZoneCard>

          {narrative && <AnalysisNotes narrative={narrative} defaultOpen={technical} />}
          {narrative && (
            <EvidenceDrawer
              evidence={displayEvidence}
              narrative={narrative}
              scenarioId={scenario.id}
              personaId={personaId}
              defaultOpen={technical}
            />
          )}
          {narrative?.llm_telemetry && <TelemetryBadge telemetry={narrative.llm_telemetry} />}
        </>
      )}
    </div>
  );
}

function Header({ evidence }: { evidence: EvidencePacket }) {
  const m = evidence.movement;
  const status = movementStatus({ isMaterial: m.is_material, relativeChangePct: m.relative_change_pct, abstained: evidence.abstained });
  const top = evidence.hypotheses.find((h) => h.id === evidence.top_hypothesis_id) ?? evidence.hypotheses[0];

  return (
    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", flexWrap: "wrap", gap: 12 }}>
      <div>
        <div className="eyebrow" style={{ marginBottom: 4 }}>
          {m.kpi_name}
        </div>
        <h1 style={{ margin: 0, fontSize: 24, color: STATUS_COLOR[status] }}>
          {m.dimension_label} {m.relative_change_pct < 0 ? "↓" : "↑"} {Math.abs(m.relative_change_pct).toFixed(0)}%
        </h1>
      </div>
      <ConfidenceBadge confidence={top?.confidence ?? 0.5} abstained={evidence.abstained} showPercent />
    </div>
  );
}

function ZoneCard({ eyebrow, children }: { eyebrow: string; children: ReactNode }) {
  return (
    <div className="panel fade-in">
      <div className="eyebrow" style={{ marginBottom: 14 }}>
        {eyebrow}
      </div>
      {children}
    </div>
  );
}
