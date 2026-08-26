# Business Proposal — KPI Storytelling Engine

## Problem framing

Business dashboards report *what* changed. Translating that into *why* and
*what to do next* still routes through an analyst, typically taking days —
by which time the window to act (a promo correction, a stock-out fix, a
churn-risk outreach) has often already closed. The gap isn't a lack of data;
it's the absence of a system that reliably connects a KPI movement to its
evidence, states its own confidence honestly, and proposes a grounded next
step without needing an analyst to assemble the story by hand every time.

## Solution design

A four-layer pipeline (see `docs/architecture.md` for the full technical
design):

1. **Data layer** — ingests two independent, differently-shaped sources
   (transactional retail sales; free-text support tickets) via fuzzy schema
   normalization, under a documented KPI semantic contract.
2. **Signal layer** — deterministic anomaly/materiality detection and
   classical NLP event extraction. No ML black boxes; every signal is
   inspectable.
3. **Reasoning layer** — LMDI driver-tree decomposition, lag-correlation
   testing with a quasi-control causal check, and a confidence scorer with
   a genuine abstention gate.
4. **Story layer** — the ONLY place an LLM is called, strictly for phrasing
   an already-computed, already-decided evidence packet and action
   recommendation for a specific persona. Every output number is checked
   against the evidence packet after the fact.

This ordering is deliberate: an enterprise deploying this needs to trust the
*numbers* first. The LLM adds language, not arithmetic.

## Target users

| Persona | Need | What they get |
|---|---|---|
| Regional/business leader | A fast, plain-language answer and one action | 3-5 sentence briefing, no jargon, single recommended action |
| Analyst | Full evidence to validate or challenge the system | Driver breakdown, correlation caveats, confidence scores, lineage |
| Category/pricing manager | Which lever to pull | The action-recommendation table (driver → lever → action → impact → owner → monitoring) |
| Support/CX operations lead | Whether ticket trends are actually linked to a sales movement | The correlation table, with an honest correlated-vs-causal label |

## Business case / impact

- **Time-to-explanation** compresses from an analyst's ad hoc,
  multi-day investigation to a system response measured in seconds
  (with a hosted LLM) — the deterministic layers are the same either way;
  only the final phrasing step's latency depends on the LLM provider.
- **Trust, not just speed**: the grounding check, explicit abstention, and
  visible LLM-vs-non-LLM breakdown mean the system's confidence is
  calibrated to what the evidence actually supports, rather than a
  uniformly confident-sounding LLM narrative that erodes trust the first
  time it's wrong.
- **Action, not just insight**: every insight ends at a specific,
  owned, monitored recommendation — closing the loop dashboards leave
  open.

## Phased roadmap

- **v1 (this prototype)**: 5 KPIs across 2 real sources, deterministic
  Signal/Reasoning layers, persona-specific Story layer, feedback capture,
  cost/latency telemetry, role-based access control.
- **v1.1**: real Kaggle downloads in place of the schema-accurate
  placeholder generator (mechanical swap — see README "Data provenance");
  a proper metrics backend (replace the in-memory telemetry log/cache with
  Redis + a real metrics store) for multi-instance deployment.
- **v2**: feedback-driven confidence recalibration — use the accumulated
  analyst-verdict log to adjust each KPI's materiality thresholds and
  driver-weighting priors, closing the "learn from feedback" loop the v1
  capture mechanism only records today.
- **v2+**: additional KPI sources (marketing spend, inventory), a proper
  identity provider integration for persona resolution (replacing the demo
  header-based persona selection), and an alerting integration (push
  material, high-confidence insights to Slack/email rather than requiring
  a dashboard visit).

## Key risks & mitigations

| Risk | Mitigation |
|---|---|
| LLM hallucinates a number | Grounding check on every narrative call; ungrounded numbers are logged and surfaced, never silently trusted |
| Overclaiming causality from observational data | Correlation module never returns "causally supported" without a quasi-control comparison, and labels it as evidence-consistent, not proven |
| Confident-sounding answer on weak evidence | Abstention gate is a real decision function over computed confidence, not a UI nicety — low-margin or low-confidence cases surface competing hypotheses instead |
| Cost/latency at scale | Tiering (cheap model for high-confidence routine cases) + response caching keyed on evidence content hash; see README "Cost, latency & scaling" |
| A regional leader sees another region's data | Row-level access enforced server-side (403, not silent filtering, on an explicit out-of-scope request); column-level PII redaction enforced on any raw-record endpoint |
| Real Kaggle data doesn't match the placeholder schema exactly | Ingestion uses fuzzy, alias-based column matching (not exact header names) and fails with a specific, actionable error naming the unmatched concept |
