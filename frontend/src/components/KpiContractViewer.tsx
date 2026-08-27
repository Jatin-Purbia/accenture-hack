import { X } from "lucide-react";
import type { KpiContract } from "../types";
import { ContractCard } from "./ContractCard";

interface Props {
  contract: KpiContract;
  onClose: () => void;
}

/** Renders the KPI semantic contract (docs/kpi_contract.yaml) as a grid of
 * visual cards, sourced from the same file the backend loads — so this is
 * always the live contract, not a copy. */
export function KpiContractViewer({ contract, onClose }: Props) {
  return (
    <div
      style={{
        position: "fixed",
        inset: 0,
        background: "rgba(15,15,12,0.5)",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        zIndex: 50,
        padding: 20,
      }}
      onClick={onClose}
    >
      <div
        className="panel fade-in"
        style={{ maxWidth: 900, maxHeight: "85vh", overflowY: "auto", width: "100%" }}
        onClick={(e) => e.stopPropagation()}
      >
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 16 }}>
          <div>
            <h2 style={{ margin: 0, fontSize: 18 }}>KPI Definitions</h2>
            <p className="muted" style={{ fontSize: 12.5, margin: "2px 0 0" }}>
              The live semantic contract — definitions, cadence, owners, and access rules.
            </p>
          </div>
          <button onClick={onClose} className="btn" style={{ padding: 8 }} aria-label="Close">
            <X size={16} />
          </button>
        </div>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(280px, 1fr))", gap: 14 }}>
          {contract.kpis.map((k) => (
            <ContractCard key={k.id} kpi={k} />
          ))}
        </div>
      </div>
    </div>
  );
}
