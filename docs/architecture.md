# Architecture

## Why this exists

A dashboard can tell you revenue dropped 8%. It can't tell you why, whether
you should worry, or what to do about it. This system is a **KPI
intelligence-to-action engine**: it detects material KPI movements,
reconciles evidence across two independent, differently-shaped data
sources, decomposes likely causes with deterministic statistics, and only
then hands a structured, numeric evidence packet to an LLM to phrase — never
to compute.

## The one rule everything else follows

> **The LLM is never the source of quantitative truth.**

Concretely, in this codebase:

- Every number that ever reaches an API response or a rendered narrative
  was computed by pandas/NumPy/statsmodels/scipy in `services/signal` or
  `services/reasoning`.
- The LLM (`services/story/llm_client.py`) is called from exactly one
  place — `services/story/narrative_service.py` — and is given a
  fully-serialized `EvidencePacket` as plain text. It never sees raw rows.
- Every narrative call is followed by an automated **grounding check**
  (`services/story/grounding.py`) that regex-extracts every number the LLM
  wrote and verifies it traces back to a number in the evidence text it was
  given. Numbers that don't match are logged and surfaced in the UI as
  "ungrounded" — this is a real check, not a claim; during development it
  caught a genuine sign error from the local fallback model (see
  "Known limitations").
- The rule-based action playbook (`services/story/action_recommender.py`)
  decides the lever/action/owner/monitoring plan from a static lookup
  table keyed on `(driver, direction)`. The LLM's only involvement is
  phrasing ONE summary sentence for an already-decided recommendation.

## The four layers

```
┌─────────────────────────────────────────────────────────────────────┐
│ DATA LAYER            services/data/                                │
│  • schema_normalization.py — fuzzy, alias-based column matching      │
│  • ingestion.py            — type cleaning, weekly aggregation       │
│  • kpi_registry.py         — loads docs/kpi_contract.yaml            │
│  • scenario_catalog.py     — curated demo-case shortlist             │
│  • feedback_store.py       — append-only analyst-verdict log         │
├─────────────────────────────────────────────────────────────────────┤
│ SIGNAL LAYER (deterministic)     services/signal/                    │
│  • anomaly.py     — STL/linear-trend forecast bands, materiality     │
│  • nlp_events.py  — rule-based category tagging + lexicon sentiment  │
├─────────────────────────────────────────────────────────────────────┤
│ REASONING LAYER (deterministic)  services/reasoning/                 │
│  • driver_tree.py       — LMDI decomposition; mix/rate decomposition │
│  • correlation.py       — lag correlation + quasi-control causal test│
│  • confidence.py        — confidence score + abstention gate         │
│  • hypothesis_engine.py — assembles/ranks candidate hypotheses       │
│  • evidence_builder.py  — orchestrates all of the above -> packet    │
├─────────────────────────────────────────────────────────────────────┤
│ STORY LAYER (the ONLY layer that calls an LLM)  services/story/      │
│  • llm_client.py       — swappable OpenAI/Ollama interface            │
│  • prompt_templates.py — versioned, persona-specific prompts          │
│  • grounding.py         — post-call number verification               │
│  • action_recommender.py — rule-based playbook lookup                 │
│  • cache.py / telemetry_log.py — cost/latency control & visibility    │
│  • narrative_service.py — orchestrates the above                      │
└─────────────────────────────────────────────────────────────────────┘
```

`app/api/*` routers are intentionally thin — they resolve a persona, call
exactly one service function, and serialize the result. All branching logic
lives in `services/`.

## Fragmented sources — a deliberate design choice, not a limitation

The two datasets are **not** natively joined:

- Superstore sales data has `region`, `category`, `sub_category` — no
  concept of a support ticket.
- The support-ticket dataset has `product` (free text) and a purchase
  date — no region field, no shared foreign key with an order.

This is realistic. In actual enterprise environments, the sales system and
the support system are owned by different teams, refresh on different
schedules, and were never designed to join. The Signal layer's rule-based
category tagger (`nlp_events.tag_category`) is the ONLY bridge between the
two sources, and the Reasoning layer treats any cross-source relationship as
a **correlation to test**, never an assumed join. This is what the
`correlation.py` module's causal-vs-correlated logic is actually for.

## Correlation vs. "causally supported"

`services/reasoning/correlation.py` implements a lightweight, honest
version of the standard requirement: a correlation is only promoted from
"correlated" to "causally supported" when a natural comparison group
(other regions selling the same category, which were not plausibly
affected) does NOT show the same signal-KPI relationship. If the
relationship holds broadly across the comparison group too, it's more
likely a shared/category-wide pattern (or a confound like seasonality) than
something specific to the treated slice, and it stays labeled "correlated".

This is a quasi-experimental (difference-in-differences-style) comparison,
not a randomized trial — the docstrings and the UI copy both say so
explicitly, because overclaiming causality from observational retail data
would be a worse error than the abstention it's meant to prevent.

## Driver-tree decomposition — LMDI, not ad hoc percentages

`decompose_sales_drivers` uses the **Log-Mean Divisia Index (LMDI)** method
to split a change in `Sales = Quantity × Gross Price × (1 − Discount)` into
additive quantity/price/discount contributions that **sum exactly** to the
observed change, with zero unexplained residual. LMDI is a standard,
published technique for decomposing multiplicative aggregates (widely used
in energy and economics analysis) — chosen specifically because a naive
"percentage of each factor's own change" approach does not have this exact-
sum property and silently misattributes cross-terms.

`decompose_margin_mix_and_rate` uses a complementary share-based
decomposition (composition/mix effect vs. within-group rate effect) —
appropriate for a *ratio* metric (profit margin %), where LMDI's
multiplicative-factor framing doesn't apply directly.

## Confidence scoring & the abstention gate

`services/reasoning/confidence.py` combines three independently-computed
signals into one score:

| Component | What it measures | Computed from |
|---|---|---|
| `statistical_strength` | How large/unusual the deviation is, and how cleanly one driver (or a coherent group of drivers) explains it | z-score + driver concentration |
| `evidence_agreement` | Whether independent signals point the same way | driver direction + correlation direction agreement |
| `data_completeness` | How much history backs the estimate | weeks of history vs. the KPI's required minimum |

The **abstention gate** (`decide_abstention`) is a real decision function,
evaluated identically for every movement:

1. No hypotheses at all → abstain.
2. A single hypothesis below the low-confidence threshold → abstain.
3. Multiple hypotheses whose top-2 confidence margin is below the
   abstain-margin threshold → abstain, surface all competing hypotheses.
4. Otherwise → commit to the top hypothesis.

Whether a given real movement abstains or not is a property of its own
computed evidence — nothing in this gate is keyed to a specific KPI, region,
or demo scenario.

### Multi-driver vs. competing-hypothesis split

`hypothesis_engine.build_hypotheses` decides whether a movement gets ONE
unified hypothesis (citing every material driver as facets of one coherent
story) or SPLITS into competing, single-driver hypotheses, using a general
threshold rule: if the largest driver explains ≥60% of the movement AND
leads the runner-up by ≥30 points, it's one coherent story; otherwise, no
driver is dominant enough to anchor a single narrative, and each of the
top-2 drivers gets its own hypothesis for the confidence scorer/abstention
gate to adjudicate.

## Cost, latency & scaling

See the README's "Cost, latency & scaling" section for the tiering rule,
caching strategy, and a discussion of how this would scale to tens of
thousands of interactions per week.

## Feedback loop

`POST /api/feedback` appends an analyst verdict (agree/disagree/partially
agree, plus an optional correction note) to an append-only JSONL log
(`services/data/feedback_store.py`). The capture mechanism is real and runs
in the demo. Using accumulated feedback to actually recalibrate confidence
weights or materiality thresholds is a v2 roadmap item — see README
"Roadmap" — deliberately not built here, since doing it honestly requires
enough real feedback volume to calibrate against, which a hackathon demo
cannot generate without faking the data that would justify it.

## Known limitations

- The local Ollama fallback (used automatically when no OpenAI key is
  configured) is CPU-bound on typical dev hardware and can take 30-90
  seconds per narrative call. The architecture (tiering, caching,
  swappable client) is what would matter at scale; wall-clock latency in
  this specific demo environment is a hardware artifact, not a design
  limitation. Configuring `OPENAI_API_KEY` drops this to 1-5 seconds.
- The two Kaggle datasets are represented here by a schema-accurate
  placeholder generator (`backend/scripts/generate_sample_data.py`) because
  this environment did not have Kaggle credentials at build time — see
  README "Data provenance" for exactly what that means and how to swap in
  the real files with zero code changes.
- `decompose_sales_drivers`'s own multiplicative baseline (built from
  independently-forecast quantity/price/discount) can differ slightly from
  the anomaly detector's direct univariate forecast of the same Sales
  series — this is a normal top-down/bottom-up reconciliation gap in
  decomposition analysis, and the evidence packet does not hide it (see
  `reconciliation_gap` in `driver_tree.decompose_sales_drivers`).
