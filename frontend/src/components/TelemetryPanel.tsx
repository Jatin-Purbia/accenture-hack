import { useEffect, useState } from "react";
import { api } from "../api/client";
import type { TelemetrySummary } from "../types";

interface Props {
  personaId: string;
  refreshKey: number;
}

/** Live LLM cost/latency/token telemetry — the runtime panel required by
 * the brief's cost/security/scalability constraints. Polls after every new
 * insight load (refreshKey) rather than on a blind interval. */
export function TelemetryPanel({ personaId, refreshKey }: Props) {
  const [data, setData] = useState<TelemetrySummary | null>(null);

  useEffect(() => {
    api.getTelemetry(personaId).then(setData).catch(() => setData(null));
  }, [personaId, refreshKey]);

  if (!data) return null;

  return (
    <div className="panel">
      <h2 style={{ fontSize: 15 }}>Runtime telemetry</h2>
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(120px, 1fr))", gap: 12 }}>
        <Stat label="LLM calls" value={String(data.total_calls)} />
        <Stat label="Cache hit rate" value={`${(data.cache_hit_rate * 100).toFixed(0)}%`} />
        <Stat label="Tokens in / out" value={`${data.total_tokens_in} / ${data.total_tokens_out}`} />
        <Stat label="Avg latency" value={`${(data.avg_latency_ms / 1000).toFixed(1)}s`} />
        <Stat label="Est. cost" value={`$${data.total_estimated_cost_usd.toFixed(4)}`} />
        <Stat label="Cached responses" value={String(data.cache_size)} />
      </div>
      <div style={{ display: "flex", gap: 20, marginTop: 12, fontSize: 12 }} className="secondary">
        <span>
          Tier split:{" "}
          {Object.entries(data.tier_breakdown)
            .map(([tier, n]) => `${tier} ×${n}`)
            .join(", ") || "—"}
        </span>
        <span>
          Models used:{" "}
          {Object.entries(data.model_breakdown)
            .map(([m, n]) => `${m} ×${n}`)
            .join(", ") || "—"}
        </span>
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
      <div style={{ fontSize: 16, fontWeight: 600 }} className="mono">
        {value}
      </div>
    </div>
  );
}
