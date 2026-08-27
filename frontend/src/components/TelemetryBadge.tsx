import { Coins, DollarSign, Zap } from "lucide-react";
import type { LlmTelemetry } from "../types";

interface Props {
  telemetry: LlmTelemetry | null;
}

/** Persistent corner widget, not a buried settings page — a badge of
 * quality ("look how cheap and fast this is"), not an admin log. Shows the
 * LAST insight's actual call stats; a cache hit gets a distinct "instant"
 * treatment so the cost-saving is visible live during a demo. */
export function TelemetryBadge({ telemetry }: Props) {
  if (!telemetry) return null;

  const isInstant = telemetry.cache_hit;

  return (
    <div
      className="panel fade-in"
      style={{
        position: "fixed",
        bottom: 20,
        right: 20,
        padding: "10px 16px",
        display: "flex",
        alignItems: "center",
        gap: 16,
        zIndex: 20,
        boxShadow: "var(--shadow-lg)",
      }}
    >
      {isInstant ? (
        <span
          style={{
            display: "inline-flex",
            alignItems: "center",
            gap: 6,
            fontSize: 12.5,
            fontWeight: 700,
            color: "var(--brand)",
          }}
        >
          <Zap size={14} fill="var(--brand)" /> Instant (cached)
        </span>
      ) : (
        <Stat icon={Zap} value={`${(telemetry.latency_ms / 1000).toFixed(1)}s`} />
      )}
      <Stat icon={Coins} value={`${telemetry.tokens_in + telemetry.tokens_out}`} />
      <Stat icon={DollarSign} value={telemetry.estimated_cost_usd > 0 ? `$${telemetry.estimated_cost_usd.toFixed(4)}` : "free (local)"} />
      <span
        className="eyebrow"
        style={{ paddingLeft: 12, borderLeft: "1px solid var(--gridline)" }}
        title={`Model: ${telemetry.model}`}
      >
        {telemetry.tier} tier
      </span>
    </div>
  );
}

function Stat({ icon: Icon, value }: { icon: typeof Zap; value: string }) {
  return (
    <span style={{ display: "inline-flex", alignItems: "center", gap: 5, fontSize: 12.5, fontWeight: 600 }}>
      <Icon size={13} className="muted" style={{ color: "var(--text-muted)" }} />
      {value}
    </span>
  );
}
