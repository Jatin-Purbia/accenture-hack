import { useEffect, useState } from "react";
import { api, ApiError } from "./api/client";
import { ActionRecommendations } from "./components/ActionRecommendations";
import { DriverBreakdown } from "./components/DriverBreakdown";
import { EvidenceViewer } from "./components/EvidenceViewer";
import { FeedbackControls } from "./components/FeedbackControls";
import { KpiContractViewer } from "./components/KpiContractViewer";
import { KpiTrendChart } from "./components/KpiTrendChart";
import { NarrativePanel } from "./components/NarrativePanel";
import { PersonaSwitcher } from "./components/PersonaSwitcher";
import { ProcessingBreakdown } from "./components/ProcessingBreakdown";
import { ScenarioList } from "./components/ScenarioList";
import { TelemetryPanel } from "./components/TelemetryPanel";
import type { Insight, KpiContract, PersonaOut, ScenarioDef } from "./types";

export default function App() {
  const [personas, setPersonas] = useState<PersonaOut[]>([]);
  const [personaId, setPersonaId] = useState("analyst_hq");
  const [scenarios, setScenarios] = useState<ScenarioDef[]>([]);
  const [scenarioId, setScenarioId] = useState<string | null>(null);
  // Which persona `scenarios`/`scenarioId` were last resolved for. The
  // insight-fetch effect gates on this (not on comparing to `scenarios`
  // directly) because two effects scheduled in the same commit cannot see
  // each other's state updates — only a value set in a PRIOR commit
  // reliably reflects "this has been reconciled for the current persona".
  const [scenariosResolvedForPersona, setScenariosResolvedForPersona] = useState<string | null>(null);
  const [insight, setInsight] = useState<Insight | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [contract, setContract] = useState<KpiContract | null>(null);
  const [showContract, setShowContract] = useState(false);
  const [telemetryTick, setTelemetryTick] = useState(0);

  useEffect(() => {
    api.getPersonas().then(setPersonas);
  }, []);

  useEffect(() => {
    let cancelled = false;
    api.getScenarios(personaId).then((list) => {
      if (cancelled) return;
      setScenarios(list);
      setScenarioId((current) => (current && list.some((s) => s.id === current) ? current : list[0]?.id ?? null));
      setScenariosResolvedForPersona(personaId);
    });
    return () => {
      cancelled = true;
    };
  }, [personaId]);

  useEffect(() => {
    if (!scenarioId) return;
    // See the comment on scenariosResolvedForPersona above: this blocks
    // the one-commit window where personaId has already changed but the
    // scenario list/id resolved for the OLD persona are still in scope.
    if (scenariosResolvedForPersona !== personaId) return;

    setLoading(true);
    setError(null);
    setInsight(null);
    api
      .getInsight(scenarioId, personaId)
      .then((data) => {
        setInsight(data);
        setTelemetryTick((t) => t + 1);
      })
      .catch((e) => {
        if (e instanceof ApiError) {
          setError(`${e.status === 403 ? "Access denied" : "Error"}: ${e.message}`);
        } else {
          setError("Failed to load insight.");
        }
      })
      .finally(() => setLoading(false));
  }, [scenarioId, personaId, scenariosResolvedForPersona]);

  function toggleContract() {
    if (!contract) {
      api.getKpiContract(personaId).then((c) => {
        setContract(c);
        setShowContract(true);
      });
    } else {
      setShowContract(true);
    }
  }

  const narrative = insight?.narratives[personaId];

  return (
    <div style={{ maxWidth: 1280, margin: "0 auto", padding: "20px 24px 60px" }}>
      <header style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 24 }}>
        <div>
          <h1 style={{ margin: 0, fontSize: 22 }}>KPI Storytelling Engine</h1>
          <p className="muted" style={{ margin: "4px 0 0", fontSize: 13 }}>
            Detects material KPI movements, decomposes root causes, and recommends actions — deterministic
            Signal/Reasoning layers, LLM only for final narrative phrasing.
          </p>
        </div>
        <div style={{ display: "flex", gap: 16, alignItems: "flex-end" }}>
          <button
            onClick={toggleContract}
            style={{
              padding: "8px 14px",
              borderRadius: 8,
              border: "1px solid var(--border)",
              background: "var(--surface-raised)",
              color: "var(--text-primary)",
              fontSize: 13,
              alignSelf: "center",
            }}
          >
            View KPI contract
          </button>
          <PersonaSwitcher personas={personas} selectedId={personaId} onChange={setPersonaId} />
        </div>
      </header>

      <div style={{ display: "grid", gridTemplateColumns: "260px 1fr", gap: 24 }}>
        <aside>
          <ScenarioList scenarios={scenarios} selectedId={scenarioId} onSelect={setScenarioId} />
        </aside>

        <main style={{ display: "flex", flexDirection: "column", gap: 20 }}>
          {loading && (
            <div className="panel muted">
              Generating insight… the local LLM fallback can take 30-90s per narrative on CPU-only hardware
              (see README — configure an OpenAI key in backend/.env for sub-5s responses).
            </div>
          )}
          {error && (
            <div className="panel" style={{ borderColor: "var(--status-critical)", color: "var(--status-critical)" }}>
              {error}
            </div>
          )}

          {insight && !loading && (
            <>
              <div className="panel">
                <KpiTrendChart evidence={insight.evidence} />
              </div>

              <div className="panel">
                <h2 style={{ fontSize: 15 }}>Driver breakdown</h2>
                <DriverBreakdown
                  drivers={
                    insight.evidence.hypotheses.find((h) => h.id === insight.evidence.top_hypothesis_id)?.drivers ??
                    insight.evidence.hypotheses[0]?.drivers ??
                    []
                  }
                />
              </div>

              {narrative && <NarrativePanel evidence={insight.evidence} narrative={narrative} />}

              {narrative && (
                <div className="panel">
                  <h2 style={{ fontSize: 15 }}>Recommended actions</h2>
                  <ActionRecommendations actions={narrative.recommended_actions} />
                </div>
              )}

              {narrative && <ProcessingBreakdown evidence={insight.evidence} narrative={narrative} />}

              <EvidenceViewer evidence={insight.evidence} scenarioId={scenarioId!} personaId={personaId} />

              <FeedbackControls evidence={insight.evidence} personaId={personaId} />

              <TelemetryPanel personaId={personaId} refreshKey={telemetryTick} />
            </>
          )}
        </main>
      </div>

      {showContract && contract && <KpiContractViewer contract={contract} onClose={() => setShowContract(false)} />}
    </div>
  );
}
