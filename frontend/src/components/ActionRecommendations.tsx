import type { ActionRecommendation } from "../types";

interface Props {
  actions: ActionRecommendation[];
}

/** driver -> controllable lever -> action -> expected impact -> owner ->
 * confidence -> monitoring plan. This structure comes entirely from the
 * rule-based playbook (services/story/action_recommender.py); the LLM only
 * supplies llm_phrased_summary, one phrased sentence per row. */
export function ActionRecommendations({ actions }: Props) {
  if (actions.length === 0) {
    return <p className="muted">No standard playbook action matched — flagged for manual analyst review.</p>;
  }

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
      {actions.map((a, i) => (
        <div key={i} className="panel" style={{ padding: "12px 16px" }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 6 }}>
            <span
              style={{
                fontSize: 11,
                fontWeight: 700,
                textTransform: "uppercase",
                letterSpacing: "0.03em",
                color: "var(--series-1)",
              }}
            >
              Driver: {a.driver.replace(/_/g, " ")}
            </span>
            <span className="muted" style={{ fontSize: 12 }}>
              Confidence {(a.confidence * 100).toFixed(0)}%
            </span>
          </div>
          {a.llm_phrased_summary && (
            <p style={{ fontStyle: "italic", margin: "0 0 8px" }}>&ldquo;{a.llm_phrased_summary}&rdquo;</p>
          )}
          <table>
            <tbody>
              <Row label="Controllable lever" value={a.controllable_lever} />
              <Row label="Action" value={a.action} />
              <Row label="Expected impact" value={a.expected_impact} />
              <Row label="Owner" value={a.owner} />
              <Row label="Monitoring plan" value={a.monitoring_plan} />
            </tbody>
          </table>
        </div>
      ))}
    </div>
  );
}

function Row({ label, value }: { label: string; value: string }) {
  return (
    <tr>
      <td className="muted" style={{ width: 160, verticalAlign: "top", border: "none", paddingLeft: 0 }}>
        {label}
      </td>
      <td style={{ border: "none", paddingLeft: 0 }}>{value}</td>
    </tr>
  );
}
