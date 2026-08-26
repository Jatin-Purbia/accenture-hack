import type { KpiContract } from "../types";

interface Props {
  contract: KpiContract;
  onClose: () => void;
}

/** Renders the KPI semantic contract (docs/kpi_contract.yaml) — definitions,
 * formulas, grain, source, cadence, owner, materiality thresholds, drivers,
 * access restrictions, and lineage — directly from the same file the
 * backend loads, so this is always the live contract, not a copy. */
export function KpiContractViewer({ contract, onClose }: Props) {
  return (
    <div
      style={{
        position: "fixed",
        inset: 0,
        background: "rgba(0,0,0,0.45)",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        zIndex: 50,
      }}
      onClick={onClose}
    >
      <div
        className="panel"
        style={{ maxWidth: 760, maxHeight: "85vh", overflowY: "auto", width: "90%" }}
        onClick={(e) => e.stopPropagation()}
      >
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
          <h2>KPI Semantic Contract</h2>
          <button
            onClick={onClose}
            style={{ background: "none", border: "none", fontSize: 20, color: "var(--text-muted)" }}
          >
            ×
          </button>
        </div>
        {contract.kpis.map((k) => (
          <div key={k.id} className="panel" style={{ marginBottom: 12 }}>
            <h3 style={{ marginTop: 0 }}>{k.name}</h3>
            <p className="secondary">{k.definition}</p>
            <table>
              <tbody>
                <tr>
                  <td className="muted" style={{ border: "none", paddingLeft: 0 }}>Formula</td>
                  <td className="mono" style={{ border: "none" }}>{k.formula}</td>
                </tr>
                <tr>
                  <td className="muted" style={{ border: "none", paddingLeft: 0 }}>Grain</td>
                  <td style={{ border: "none" }}>{k.grain}</td>
                </tr>
                <tr>
                  <td className="muted" style={{ border: "none", paddingLeft: 0 }}>Source</td>
                  <td style={{ border: "none" }}>{k.source}</td>
                </tr>
                <tr>
                  <td className="muted" style={{ border: "none", paddingLeft: 0 }}>Refresh cadence</td>
                  <td style={{ border: "none" }}>{k.refresh_cadence}</td>
                </tr>
                <tr>
                  <td className="muted" style={{ border: "none", paddingLeft: 0 }}>Owner</td>
                  <td style={{ border: "none" }}>{k.owner}</td>
                </tr>
                <tr>
                  <td className="muted" style={{ border: "none", paddingLeft: 0 }}>Dimensions</td>
                  <td style={{ border: "none" }}>{k.dimensions.join(", ")}</td>
                </tr>
                <tr>
                  <td className="muted" style={{ border: "none", paddingLeft: 0 }}>Drivers</td>
                  <td style={{ border: "none" }}>{k.drivers.join(", ")}</td>
                </tr>
                <tr>
                  <td className="muted" style={{ border: "none", paddingLeft: 0 }}>Materiality</td>
                  <td style={{ border: "none" }}>
                    {k.materiality.min_relative_change_pct}% relative
                    {k.materiality.min_absolute_change_usd != null && ` and $${k.materiality.min_absolute_change_usd} absolute`}
                    {k.materiality.min_absolute_change_pp != null && ` and ${k.materiality.min_absolute_change_pp}pp absolute`}
                    {k.materiality.min_absolute_change_count != null && ` and ${k.materiality.min_absolute_change_count} count absolute`}
                  </td>
                </tr>
                <tr>
                  <td className="muted" style={{ border: "none", paddingLeft: 0 }}>Row-level access</td>
                  <td style={{ border: "none" }}>{k.access_restrictions.row_level}</td>
                </tr>
                <tr>
                  <td className="muted" style={{ border: "none", paddingLeft: 0 }}>Column-level access</td>
                  <td style={{ border: "none" }}>{k.access_restrictions.column_level}</td>
                </tr>
              </tbody>
            </table>
          </div>
        ))}
      </div>
    </div>
  );
}
