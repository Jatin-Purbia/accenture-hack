import type {
  EvidencePacket,
  FeedbackEntry,
  FeedbackVerdict,
  Insight,
  KpiContract,
  PersonaOut,
  SampleRecord,
  ScenarioDef,
} from "../types";

const BASE = "/api";

async function apiFetch<T>(path: string, personaId: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    ...init,
    headers: {
      "X-Persona-Id": personaId,
      ...(init?.body ? { "Content-Type": "application/json" } : {}),
      ...init?.headers,
    },
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({ detail: res.statusText }));
    throw new ApiError(res.status, body.detail ?? res.statusText);
  }
  return res.json() as Promise<T>;
}

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

export const api = {
  getPersonas: () => apiFetch<PersonaOut[]>("/personas", "analyst_hq"),
  getScenarios: (personaId: string) => apiFetch<ScenarioDef[]>("/scenarios", personaId),
  getKpiContract: (personaId: string) => apiFetch<KpiContract>("/kpis", personaId),
  getInsight: (scenarioId: string, personaId: string, signal?: AbortSignal) =>
    apiFetch<Insight>(`/insights/${scenarioId}`, personaId, { signal }),
  getScenarioEvidence: (scenarioId: string, personaId: string, signal?: AbortSignal) =>
    apiFetch<EvidencePacket>(`/insights/${scenarioId}/evidence`, personaId, { signal }),
  getSampleRecords: (scenarioId: string, personaId: string) =>
    apiFetch<SampleRecord[]>(`/insights/${scenarioId}/sample-records`, personaId),
  submitFeedback: (
    personaId: string,
    payload: {
      kpi_id: string;
      insight_id: string;
      hypothesis_id: string;
      persona_id: string;
      verdict: FeedbackVerdict;
      correction_note?: string;
    }
  ) =>
    apiFetch<FeedbackEntry>("/feedback", personaId, {
      method: "POST",
      body: JSON.stringify(payload),
    }),
};
