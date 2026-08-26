# Demo Script

A scene-by-scene walkthrough covering every minimum-prototype scenario, for
recording the demo video. Each scene names exactly what to click and what to
say. Total run time depends on LLM latency (see note at the bottom).

**Setup before recording:** both servers running (`docker compose up` or the
two `README.md` dev commands), browser open to `http://localhost:5173`,
persona switcher defaulted to **HQ Analyst**.

---

## Scene 1 — The problem, in one screen (Scenario 1: connected KPIs)

Open the **KPI contract** modal (top-right button).

> "This system explains KPI movements, not just charts. Before looking at
> any number, here's the semantic contract behind it — five KPIs across two
> independent sources with different grains and refresh cadences: weekly
> sales by region, weekly profit margin by category (transactional grain,
> from the Superstore dataset), and weekly support-ticket volume and
> sentiment by category (ticket grain, from an independent support-ticket
> dataset with no shared join key)."

Point out: formula, grain, source, refresh cadence, owner, materiality
thresholds, drivers, and access restrictions for `weekly_sales_by_region`.
Close the modal.

*(Satisfies scenarios 1 and 2.)*

## Scene 2 — A multi-factor movement, correctly decomposed (Scenario 4)

Select **"West Region — Technology Sales Drop"** in the sidebar.

> "The system flagged this automatically — it's not a canned example. The
> trend chart shows the actual vs. the forecast band for the evaluated
> week; the point is well outside the band."

Point at the **Driver breakdown** bar chart.

> "The decomposition uses LMDI — a standard multiplicative-factor
> decomposition, not an ad hoc percentage split — and the three bars sum
> exactly to the observed change. Both quantity (down 25%) and discount
> (up 13 points) are material contributors here — a genuine multi-cause
> story, not a single driver."

Scroll to the narrative panel.

> "Confidence sits around 65-70% — moderate, not maxed out — because this
> committed to one hypothesis but the drivers don't perfectly concentrate
> on a single cause. Note the correlation signal: ticket sentiment for
> Technology is labeled 'causally supported', not just correlated — that's
> because the SAME signal does NOT show the same relationship in the other
> three regions, which is the quasi-control-group check."

## Scene 3 — Two personas, one event (Scenario 3)

Switch persona to **"Regional Leader — West"** (still on the same scenario).

> "Same evidence, same reasoning output — only the Story-layer prompt
> differs. The regional leader gets three sentences, no jargon, one
> recommended action. The analyst got a full breakdown with confidence
> scores and correlation caveats."

## Scene 4 — Ambiguous evidence: the system abstains (Scenario 5)

Switch back to **HQ Analyst**, select **"Central — Office Supplies Margin
Compression"**.

> "This is the case the brief asks for explicitly: when evidence is
> genuinely contested, the system does not guess. Two hypotheses —
> cost-mix shift and within-category discounting — both compute to roughly
> 40/50/60% of the movement, with confidence scores 0.79 and 0.80. That
> margin is below the abstain threshold, so instead of a single confident
> story, you get both hypotheses side by side, the specific reason for the
> abstention, and what additional data would resolve it."

Read the abstention banner text aloud.

## Scene 5 — Sparse history, not just low confidence (Scenario 6)

Select **"Emerging Sub-Category — 3D Printers"**.

> "This is a real, low-volume slice of the actual dataset — a newly
> launched product line with about six weeks of history — not a fabricated
> synthetic scenario. Data completeness is the limiting factor here, not
> statistical ambiguity: the movement itself is a clean, large drop, but
> confidence is capped because there isn't enough history yet to trust a
> forecast band built on five data points."

## Scene 6 — Security: a persona blocked from seeing data outside scope (Scenario 7)

Switch persona to **"Regional Leader — East"**. Try to select
**"West Region — Technology Sales Drop"** from the (now filtered) sidebar —
it won't even be listed. Then hit the underlying endpoint directly (or note
the 403 behavior) for **West** while logged in as the East leader.

> "Row-level access is enforced server-side, not just hidden in the UI —
> a scoped persona gets a 403, not an empty result. Column-level scoping is
> enforced too: open 'View underlying raw records' as the East leader,
> and customer_id/customer_name are absent from the response body, not
> just hidden client-side."

## Scene 7 — Evidence, lineage, and the LLM-vs-non-LLM breakdown (Scenarios 8 & 9)

Back on any scenario as HQ Analyst, scroll to **Processing breakdown**.

> "This is the literal requirement from the brief: every method that
> touched this insight, tagged by which layer produced it. Everything in
> the left column — trend decomposition, driver-tree math, correlation
> tests, confidence scoring, the action-playbook lookup — is deterministic
> pandas/NumPy/statsmodels/scipy. The LLM appears exactly once, at the
> bottom, for narrative phrasing only."

Scroll to **Evidence & lineage**.

> "Source freshness, weeks of history, the correlation table with lag/r/p/
> classification, and the lineage trail from the raw Kaggle-shaped file
> through normalization to this exact number. Click 'View underlying raw
> records' to see the actual order lines behind this week's figure."

## Scene 8 — Runtime telemetry (Scenario 10)

Scroll to **Runtime telemetry**.

> "Every LLM call is instrumented: tokens in/out, latency, model, estimated
> cost, and which tier — cheap vs. strong — was used. Tiering isn't a
> separate guess; it's read directly off the confidence score the
> Reasoning layer already computed. Cache hit rate is live too: asking for
> the same insight twice costs zero additional LLM calls."

## Scene 9 — Grounding: a trust check, not a claim

Point at the "Grounding verified" / "N ungrounded numbers" badge on the
narrative panel.

> "After every LLM call, we regex-extract every number it wrote and verify
> it traces back to the evidence packet it was given. This isn't
> theoretical — during development, the local fallback model once wrote a
> negative percentage where the evidence had a positive one, and the check
> caught it and flagged it in the UI, without us knowing in advance what
> error it would make."

## Scene 10 — The feedback loop (Scenario "learn from feedback")

Click **Agree** / **Partially agree** / **Disagree** on the current
insight's feedback control.

> "This appends a real record — KPI, hypothesis shown, verdict, timestamp
> — to an append-only log. It's a thin mechanism today; the roadmap in the
> README covers how accumulated verdicts would recalibrate confidence
> weights over time."

---

## Timing note

The local Ollama fallback (used automatically without an `OPENAI_API_KEY`)
takes 30-90 seconds per narrative call on CPU-only hardware — expected and
documented, not a bug. For a snappier recording, set `OPENAI_API_KEY` in
`backend/.env` before recording (response time drops to 1-5 seconds), or
pre-warm the cache by loading each scenario once before hitting record.
