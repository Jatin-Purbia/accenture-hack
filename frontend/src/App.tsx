import { useEffect, useState } from "react";
import { api } from "./api/client";
import { DetailView } from "./components/DetailView";
import { HomeView } from "./components/HomeView";
import { KpiContractViewer } from "./components/KpiContractViewer";
import { PersonaToggle } from "./components/PersonaToggle";
import { ThemeToggle } from "./components/ThemeToggle";
import { applyTheme, getInitialTheme, type Theme } from "./lib/theme";
import type { KpiContract, PersonaOut, ScenarioDef } from "./types";

export default function App() {
  const [personas, setPersonas] = useState<PersonaOut[]>([]);
  const [personaId, setPersonaId] = useState("leader_west");
  const [scenarios, setScenarios] = useState<ScenarioDef[]>([]);
  const [scenarioId, setScenarioId] = useState<string | null>(null);
  const [contract, setContract] = useState<KpiContract | null>(null);
  const [showContract, setShowContract] = useState(false);
  const [theme, setTheme] = useState<Theme>(getInitialTheme);

  useEffect(() => {
    applyTheme(theme);
  }, [theme]);

  useEffect(() => {
    api.getPersonas().then(setPersonas);
  }, []);

  useEffect(() => {
    api.getScenarios(personaId).then(setScenarios);
  }, [personaId]);

  const currentPersona = personas.find((p) => p.id === personaId);
  const selectedScenario = scenarios.find((s) => s.id === scenarioId) ?? null;

  function goHome() {
    setScenarioId(null);
  }

  function changePersona(id: string) {
    setPersonaId(id);
    setScenarioId(null); // a scenario valid for the old persona may not exist/be in-scope for the new one
  }

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

  return (
    <div style={{ minHeight: "100vh" }}>
      <div style={{ position: "sticky", top: 0, zIndex: 10, background: "var(--surface-1)", borderBottom: "1px solid var(--gridline)" }}>
        <div
          style={{
            maxWidth: 1160,
            margin: "0 auto",
            padding: "16px 24px",
            display: "flex",
            justifyContent: "space-between",
            alignItems: "flex-start",
            gap: 20,
          }}
        >
          <button onClick={goHome} style={{ display: "flex", gap: 12, alignItems: "center", background: "none", border: "none", padding: 0 }}>
            <BrandMark />
            <div style={{ textAlign: "left" }}>
              <h1 style={{ margin: 0, fontSize: 18 }}>KPI Storytelling Engine</h1>
              <p className="muted" style={{ margin: "2px 0 0", fontSize: 12 }}>
                What changed, why, and what to do next.
              </p>
            </div>
          </button>
          <div style={{ display: "flex", gap: 12, alignItems: "flex-start" }}>
            <div style={{ display: "flex", gap: 8, marginTop: 2 }}>
              <ThemeToggle theme={theme} onChange={setTheme} />
              <button className="btn" onClick={toggleContract}>
                KPI definitions
              </button>
            </div>
            <PersonaToggle personas={personas} selectedId={personaId} onChange={changePersona} />
          </div>
        </div>
      </div>

      <div style={{ maxWidth: 1160, margin: "0 auto", padding: "28px 24px 100px" }}>
        {selectedScenario && currentPersona ? (
          <DetailView
            key={`${selectedScenario.id}:${personaId}`}
            scenario={selectedScenario}
            personaId={personaId}
            personaRole={currentPersona.role}
            onBack={goHome}
          />
        ) : (
          <HomeView scenarios={scenarios} personaId={personaId} onSelect={setScenarioId} />
        )}
      </div>

      {showContract && contract && <KpiContractViewer contract={contract} onClose={() => setShowContract(false)} />}
    </div>
  );
}

function BrandMark() {
  return (
    <div style={{ width: 34, height: 34, borderRadius: 9, background: "var(--brand)", display: "flex", alignItems: "center", justifyContent: "center", flex: "none" }}>
      <svg width="18" height="18" viewBox="0 0 20 20" fill="none">
        <path d="M3 14l4-5 3 3 6-8" stroke="white" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
        <circle cx="16" cy="4" r="1.8" fill="white" />
      </svg>
    </div>
  );
}
