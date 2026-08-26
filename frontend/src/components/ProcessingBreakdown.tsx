import type { EvidenceMethod, EvidencePacket, PersonaNarrative } from "../types";

const METHOD_LABELS: Record<EvidenceMethod, string> = {
  trend_seasonality_decomposition: "Trend + seasonality decomposition (STL)",
  forecast_band_deviation: "Forecast-band deviation test",
  driver_tree_decomposition: "Driver-tree decomposition (LMDI / mix-rate)",
  lag_correlation_test: "Lag-aware correlation test",
  lexicon_sentiment_scoring: "Lexicon-based sentiment scoring",
  rule_based_nlp_event_extraction: "Rule-based NLP event/category extraction",
  confidence_scoring: "Confidence scoring & abstention gate",
  rule_based_action_lookup: "Rule-based action-playbook lookup",
  llm_narrative_phrasing: "LLM narrative phrasing",
};

const IS_LLM: Record<EvidenceMethod, boolean> = {
  trend_seasonality_decomposition: false,
  forecast_band_deviation: false,
  driver_tree_decomposition: false,
  lag_correlation_test: false,
  lexicon_sentiment_scoring: false,
  rule_based_nlp_event_extraction: false,
  confidence_scoring: false,
  rule_based_action_lookup: false,
  llm_narrative_phrasing: true,
};

interface Props {
  evidence: EvidencePacket;
  narrative: PersonaNarrative;
}

/** The graded "LLM vs non-LLM" breakdown: every method that touched THIS
 * insight, tagged by which layer produced it. Collected from the actual
 * evidence (driver/correlation methods) rather than a fixed static list, so
 * it reflects what really ran for this specific insight. */
export function ProcessingBreakdown({ evidence, narrative }: Props) {
  const methods = new Set<EvidenceMethod>();
  methods.add(evidence.movement.method);
  methods.add("confidence_scoring");
  for (const h of evidence.hypotheses) {
    for (const d of h.drivers) methods.add(d.method);
    for (const c of h.correlations) methods.add(c.method);
  }
  if (narrative.recommended_actions.length > 0) methods.add("rule_based_action_lookup");
  methods.add("llm_narrative_phrasing");

  const deterministic = [...methods].filter((m) => !IS_LLM[m]);
  const llm = [...methods].filter((m) => IS_LLM[m]);

  return (
    <div className="panel">
      <h2 style={{ fontSize: 15 }}>Processing breakdown</h2>
      <p className="secondary" style={{ fontSize: 13, marginTop: -4 }}>
        Every method that produced a fact in this insight, tagged by layer. The LLM is used ONLY for the
        final phrasing step — every number above it comes from deterministic computation.
      </p>
      <div style={{ display: "flex", gap: 16, flexWrap: "wrap" }}>
        <Column
          title={`Deterministic / non-LLM (${deterministic.length})`}
          color="var(--series-1)"
          items={deterministic.map((m) => METHOD_LABELS[m])}
        />
        <Column title={`LLM (${llm.length})`} color="var(--series-7)" items={llm.map((m) => METHOD_LABELS[m])} />
      </div>
    </div>
  );
}

function Column({ title, color, items }: { title: string; color: string; items: string[] }) {
  return (
    <div style={{ flex: 1, minWidth: 220 }}>
      <div style={{ fontSize: 12, fontWeight: 600, color, marginBottom: 6 }}>{title}</div>
      <ul style={{ margin: 0, paddingLeft: 18, fontSize: 13 }}>
        {items.map((item, i) => (
          <li key={i} style={{ marginBottom: 4 }}>
            {item}
          </li>
        ))}
      </ul>
    </div>
  );
}
