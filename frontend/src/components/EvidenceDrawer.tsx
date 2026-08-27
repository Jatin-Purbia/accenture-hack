import { useState } from "react";
import { Bot, ChevronDown, Clock, Database, ListChecks, SigmaSquare, Table2 } from "lucide-react";
import { api } from "../api/client";
import type { EvidencePacket, PersonaNarrative, SampleRecord } from "../types";

interface Props {
  evidence: EvidencePacket;
  narrative: PersonaNarrative;
  scenarioId: string;
  personaId: string;
  defaultOpen?: boolean;
}

const CLASSIFICATION_LABEL: Record<string, string> = {
  causally_supported: "Causally supported",
  correlated: "Correlated, not causal",
  insufficient_evidence: "Insufficient evidence",
};
const CLASSIFICATION_COLOR: Record<string, string> = {
  causally_supported: "var(--status-good)",
  correlated: "var(--status-warning)",
  insufficient_evidence: "var(--text-muted)",
};

/** The evidence drawer — freshness, the Data→Stats→Rules→LLM breakdown as
 * a lit-up flow strip (not prose), correlation caveats as chips, lineage,
 * and an optional raw-record table. Collapsed by default for a business
 * leader, open by default for the analyst persona. */
export function EvidenceDrawer({ evidence, narrative, scenarioId, personaId, defaultOpen = false }: Props) {
  const [open, setOpen] = useState(defaultOpen);
  const [showTable, setShowTable] = useState(false);
  const [records, setRecords] = useState<SampleRecord[] | null>(null);
  const [loadingRecords, setLoadingRecords] = useState(false);

  const allCorrelations = evidence.hypotheses.flatMap((h) => h.correlations);
  const uniqueCorrelations = Array.from(new Map(allCorrelations.map((c) => [c.signal_name, c])).values());

  async function loadRecords() {
    setLoadingRecords(true);
    try {
      setRecords(await api.getSampleRecords(scenarioId, personaId));
      setShowTable(true);
    } finally {
      setLoadingRecords(false);
    }
  }

  return (
    <div className="panel" style={{ padding: 0, overflow: "hidden" }}>
      <button
        onClick={() => setOpen((o) => !o)}
        style={{ width: "100%", display: "flex", justifyContent: "space-between", alignItems: "center", padding: "16px 22px", background: "none", border: "none", textAlign: "left" }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
          <div style={{ fontWeight: 650, fontSize: 15 }}>Evidence</div>
          <span className="muted" style={{ fontSize: 12, display: "inline-flex", alignItems: "center", gap: 4 }}>
            <Clock size={13} /> Updated {evidence.data_completeness.source_freshness_days}d ago
          </span>
        </div>
        <ChevronDown size={16} className="muted" style={{ transform: open ? "rotate(180deg)" : "none", transition: "transform 0.15s ease" }} />
      </button>

      {open && (
        <div className="fade-in" style={{ padding: "0 22px 22px", borderTop: "1px solid var(--gridline)" }}>
          <div style={{ paddingTop: 18, display: "flex", flexDirection: "column", gap: 20 }}>
            <FlowStrip tier={narrative.llm_telemetry?.tier} />

            {uniqueCorrelations.length > 0 && (
              <div>
                <div className="eyebrow" style={{ marginBottom: 8 }}>
                  Related signals
                </div>
                <div style={{ display: "flex", flexWrap: "wrap", gap: 8 }}>
                  {uniqueCorrelations.map((c) => (
                    <span
                      key={c.signal_name}
                      title={c.rationale}
                      style={{
                        display: "inline-flex",
                        alignItems: "center",
                        gap: 6,
                        padding: "5px 11px",
                        borderRadius: 999,
                        fontSize: 12,
                        fontWeight: 600,
                        background: "var(--surface-sunken)",
                        border: `1px solid ${CLASSIFICATION_COLOR[c.classification]}`,
                        color: CLASSIFICATION_COLOR[c.classification],
                        cursor: "help",
                      }}
                    >
                      <span style={{ width: 6, height: 6, borderRadius: "50%", background: CLASSIFICATION_COLOR[c.classification] }} />
                      {c.signal_name.replace(/_/g, " ")} · {CLASSIFICATION_LABEL[c.classification]}
                    </span>
                  ))}
                </div>
              </div>
            )}

            <div>
              <div className="eyebrow" style={{ marginBottom: 8 }}>
                Data lineage
              </div>
              <ol style={{ margin: 0, paddingLeft: 18, fontSize: 12.5 }} className="secondary">
                {evidence.lineage.map((step, i) => (
                  <li key={i} style={{ marginBottom: 3 }}>
                    <code className="mono" style={{ fontSize: 11.5 }}>
                      {step}
                    </code>
                  </li>
                ))}
              </ol>
            </div>

            <div>
              <button className="btn" onClick={loadRecords} disabled={loadingRecords}>
                {loadingRecords && <span className="spinner" style={{ width: 12, height: 12, borderWidth: 2 }} />}
                <Table2 size={14} />
                {records ? (showTable ? "Hide raw records" : "Show raw records") : "View underlying raw records"}
              </button>
              {records && showTable && (
                <div style={{ overflowX: "auto", marginTop: 12 }}>
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
              {records && !showTable && (
                <button className="btn" onClick={() => setShowTable(true)} style={{ marginLeft: 8 }}>
                  Show table
                </button>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

const FLOW_STEPS = [
  { key: "data", label: "Data", icon: Database },
  { key: "stats", label: "Stats", icon: SigmaSquare },
  { key: "rules", label: "Rules", icon: ListChecks },
  { key: "llm", label: "LLM", icon: Bot },
] as const;

/** The literal "LLM vs non-LLM breakdown" as a lit-up flow diagram instead
 * of prose: every insight passes through all four layers, in this order —
 * the LLM only ever phrases what the first three already computed. */
function FlowStrip({ tier }: { tier?: string }) {
  return (
    <div>
      <div className="eyebrow" style={{ marginBottom: 10 }}>
        How this was produced
      </div>
      <div style={{ display: "flex", alignItems: "center", gap: 4 }}>
        {FLOW_STEPS.map((step, i) => (
          <div key={step.key} style={{ display: "flex", alignItems: "center", gap: 4 }}>
            <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 6, width: 64 }}>
              <div
                className="icon-badge"
                style={{
                  width: 38,
                  height: 38,
                  background: step.key === "llm" ? "var(--series-7)" : "var(--brand)",
                  opacity: 1,
                }}
              >
                <step.icon size={18} color="white" strokeWidth={2} />
              </div>
              <span style={{ fontSize: 11, fontWeight: 600, textAlign: "center" }}>
                {step.label}
                {step.key === "llm" && tier && <div className="muted" style={{ fontWeight: 500 }}>({tier})</div>}
              </span>
            </div>
            {i < FLOW_STEPS.length - 1 && <div style={{ width: 20, height: 2, background: "var(--border-strong)" }} />}
          </div>
        ))}
      </div>
      <p className="muted" style={{ fontSize: 12, marginTop: 10, marginBottom: 0, maxWidth: 480 }}>
        Data and Stats compute the movement and drivers; Rules pick the action from a fixed playbook; the LLM only
        phrases the final sentence — it never invents a number.
      </p>
    </div>
  );
}
