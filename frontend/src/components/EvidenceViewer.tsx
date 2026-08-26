import { useState } from "react";
import { api } from "../api/client";
import type { EvidencePacket, SampleRecord } from "../types";

interface Props {
  evidence: EvidencePacket;
  scenarioId: string;
  personaId: string;
}

const CLASSIFICATION_LABEL: Record<string, string> = {
  causally_supported: "Causally supported",
  correlated: "Correlated (not causal)",
  insufficient_evidence: "Insufficient evidence",
};

const CLASSIFICATION_COLOR: Record<string, string> = {
  causally_supported: "var(--status-good)",
  correlated: "var(--status-warning)",
  insufficient_evidence: "var(--text-muted)",
};

/** Evidence + lineage + traceability — freshness, method, contribution %,
 * confidence, and a drill-down to the raw records behind the number. */
export function EvidenceViewer({ evidence, scenarioId, personaId }: Props) {
  const [records, setRecords] = useState<SampleRecord[] | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const allCorrelations = evidence.hypotheses.flatMap((h) => h.correlations);
  const uniqueCorrelations = Array.from(new Map(allCorrelations.map((c) => [c.signal_name, c])).values());

  async function loadRecords() {
    setLoading(true);
    setError(null);
    try {
      const data = await api.getSampleRecords(scenarioId, personaId);
      setRecords(data);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load sample records");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="panel">
      <h2 style={{ fontSize: 15 }}>Evidence & lineage</h2>

      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(160px, 1fr))", gap: 12, marginBottom: 14 }}>
        <Stat label="Data completeness" value={`${evidence.data_completeness.weeks_of_history} / ${evidence.data_completeness.weeks_required_for_high_confidence} wks`} />
        <Stat label="Source freshness" value={`${evidence.data_completeness.source_freshness_days}d ago`} />
        <Stat label="Missing periods" value={String(evidence.data_completeness.missing_periods)} />
        <Stat label="Generated" value={new Date(evidence.generated_at).toLocaleString()} />
      </div>

      {uniqueCorrelations.length > 0 && (
        <>
          <h3 style={{ fontSize: 13 }} className="muted">
            Correlation signals
          </h3>
          <table style={{ marginBottom: 14 }}>
            <thead>
              <tr>
                <th>Signal</th>
                <th>Lag</th>
                <th>r</th>
                <th>p</th>
                <th>Classification</th>
              </tr>
            </thead>
            <tbody>
              {uniqueCorrelations.map((c) => (
                <tr key={c.signal_name}>
                  <td>{c.signal_name}</td>
                  <td>{c.lag_weeks}w</td>
                  <td className="mono">{c.correlation_coefficient.toFixed(2)}</td>
                  <td className="mono">{c.p_value.toFixed(2)}</td>
                  <td>
                    <span style={{ color: CLASSIFICATION_COLOR[c.classification], fontWeight: 600, fontSize: 12 }}>
                      {CLASSIFICATION_LABEL[c.classification]}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </>
      )}

      <h3 style={{ fontSize: 13 }} className="muted">
        Lineage (raw file → this number)
      </h3>
      <ol style={{ margin: "0 0 14px", paddingLeft: 18, fontSize: 13 }} className="secondary">
        {evidence.lineage.map((step, i) => (
          <li key={i} style={{ marginBottom: 3 }}>
            <code className="mono" style={{ fontSize: 12 }}>
              {step}
            </code>
          </li>
        ))}
      </ol>

      <div>
        <button
          onClick={loadRecords}
          disabled={loading}
          style={{
            padding: "6px 14px",
            borderRadius: 6,
            border: "1px solid var(--border)",
            background: "var(--surface-raised)",
            color: "var(--text-primary)",
            fontSize: 13,
          }}
        >
          {loading ? "Loading…" : records ? "Refresh raw records" : "View underlying raw records"}
        </button>
        {error && <div style={{ color: "var(--status-critical)", fontSize: 13, marginTop: 6 }}>{error}</div>}
        {records && (
          <div style={{ overflowX: "auto", marginTop: 10 }}>
            <table>
              <thead>
                <tr>
                  {Object.keys(records[0] ?? {}).map((col) => (
                    <th key={col}>{col}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {records.map((r, i) => (
                  <tr key={i}>
                    {Object.entries(r).map(([k, v]) => (
                      <td key={k} className={typeof v === "number" ? "mono" : undefined}>
                        {String(v)}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
            {!("customer_name" in (records[0] ?? {})) && (
              <div className="muted" style={{ fontSize: 12, marginTop: 6 }}>
                Customer identity columns are hidden for this persona (column-level access control).
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <div className="muted" style={{ fontSize: 11, textTransform: "uppercase", letterSpacing: "0.03em" }}>
        {label}
      </div>
      <div style={{ fontSize: 15, fontWeight: 600 }}>{value}</div>
    </div>
  );
}
