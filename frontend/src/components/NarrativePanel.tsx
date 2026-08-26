import type { EvidencePacket, Hypothesis, PersonaNarrative } from "../types";

interface Props {
  evidence: EvidencePacket;
  narrative: PersonaNarrative;
}

/** The prompt instructs the model to avoid markdown, but small local models
 * occasionally slip in a stray "#"/"**" anyway — strip the common markers
 * defensively rather than rendering them as literal characters. This is a
 * display nicety only; it never touches the text the grounding check runs
 * against. */
function stripMarkdown(text: string): string {
  return text
    .replace(/^#{1,6}\s*/gm, "")
    .replace(/\*\*(.*?)\*\*/g, "$1")
    .replace(/^\s*[-*]\s+/gm, "");
}

function confidenceColor(confidence: number): string {
  if (confidence >= 0.75) return "var(--status-good)";
  if (confidence >= 0.55) return "var(--status-warning)";
  return "var(--status-critical)";
}

function ConfidenceBadge({ confidence }: { confidence: number }) {
  return (
    <span
      style={{
        display: "inline-flex",
        alignItems: "center",
        gap: 6,
        padding: "3px 10px",
        borderRadius: 999,
        fontSize: 12,
        fontWeight: 600,
        background: "color-mix(in srgb, " + confidenceColor(confidence) + " 16%, transparent)",
        color: confidenceColor(confidence),
      }}
    >
      <span style={{ width: 7, height: 7, borderRadius: "50%", background: confidenceColor(confidence) }} />
      Confidence {(confidence * 100).toFixed(0)}%
    </span>
  );
}

function HypothesisCard({ hypothesis, isTop }: { hypothesis: Hypothesis; isTop: boolean }) {
  return (
    <div
      className="panel"
      style={{
        flex: 1,
        minWidth: 220,
        borderColor: isTop ? "var(--series-1)" : "var(--border)",
        borderWidth: isTop ? 2 : 1,
      }}
    >
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <h3 style={{ margin: 0, fontSize: 15 }}>{hypothesis.label}</h3>
        <ConfidenceBadge confidence={hypothesis.confidence} />
      </div>
      <p className="secondary" style={{ fontSize: 13 }}>
        {hypothesis.summary}
      </p>
      <div style={{ fontSize: 12 }} className="muted">
        statistical strength {(hypothesis.statistical_strength * 100).toFixed(0)}% · evidence agreement{" "}
        {(hypothesis.evidence_agreement * 100).toFixed(0)}% · data completeness{" "}
        {(hypothesis.data_completeness_score * 100).toFixed(0)}%
      </div>
    </div>
  );
}

export function NarrativePanel({ evidence, narrative }: Props) {
  const grounding = narrative.grounding;

  return (
    <div className="panel">
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: 12 }}>
        <h2 style={{ fontSize: 18 }}>{narrative.headline}</h2>
        <span
          title={
            grounding.passed
              ? "Every number in this narrative was verified against the evidence packet."
              : `${grounding.ungrounded_numbers.length} number(s) could not be verified against the evidence packet: ${grounding.ungrounded_numbers.join(", ")}`
          }
          style={{
            whiteSpace: "nowrap",
            fontSize: 12,
            fontWeight: 600,
            padding: "3px 10px",
            borderRadius: 999,
            background: grounding.passed
              ? "color-mix(in srgb, var(--status-good) 16%, transparent)"
              : "color-mix(in srgb, var(--status-warning) 20%, transparent)",
            color: grounding.passed ? "var(--status-good)" : "#8a5a00",
          }}
        >
          {grounding.passed ? "✓ Grounding verified" : `⚠ ${grounding.ungrounded_numbers.length} ungrounded number(s)`}
        </span>
      </div>

      {evidence.abstained && (
        <div
          style={{
            background: "color-mix(in srgb, var(--status-warning) 14%, transparent)",
            border: "1px solid var(--status-warning)",
            borderRadius: 8,
            padding: "10px 14px",
            marginBottom: 12,
            fontSize: 13,
          }}
        >
          <strong>Abstained — no single explanation was confident enough to commit to.</strong>
          <div className="secondary" style={{ marginTop: 4 }}>
            {evidence.abstention_reason}
          </div>
        </div>
      )}

      <p style={{ whiteSpace: "pre-wrap", lineHeight: 1.55 }}>{stripMarkdown(narrative.narrative)}</p>

      {evidence.hypotheses.length > 0 && (
        <>
          <h3 style={{ fontSize: 13, textTransform: "uppercase", letterSpacing: "0.03em" }} className="muted">
            {evidence.abstained ? "Competing hypotheses" : "Hypothesis"}
          </h3>
          <div style={{ display: "flex", gap: 12, flexWrap: "wrap" }}>
            {evidence.hypotheses.map((h) => (
              <HypothesisCard key={h.id} hypothesis={h} isTop={h.id === evidence.top_hypothesis_id} />
            ))}
          </div>
        </>
      )}
    </div>
  );
}
