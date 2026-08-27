# Demo Script

A scene-by-scene walkthrough covering every minimum-prototype scenario, for
recording the demo video. The UI is deliberately visual-first — a judge
muting the audio should still follow the story from color, shape, and
icons alone (see `docs/architecture.md` for why). Each scene names exactly
what to click and what to say.

**Setup before recording:** both servers running (`docker compose up` or the
two `README.md` dev commands), browser open to `http://localhost:5173`. The
app opens on **Leader view**, scoped to the West region, by default.

---

## Scene 1 — The KPI Command Center (Scenario 1: connected KPIs)

Land on the home screen.

> "This is the KPI Command Center — a grid, not a table. Every card shows
> an icon, a big number with a direction arrow, a sparkline against its
> normal range, and a confidence dot. No prose. Cards needing attention —
> material movements — get a pulsing ring and float to the front
> automatically; nothing here required reading a sentence yet."

Open **KPI definitions** (top-right).

> "Before looking at any number, here's the semantic contract behind it —
> five KPIs across two independent sources with different grains and
> refresh cadences: weekly sales by region and profit margin by category
> from the Superstore dataset, and weekly support-ticket volume and
> sentiment by category from an independent ticket dataset with no shared
> join key."

Close the modal.

*(Satisfies scenarios 1 and 2.)*

## Scene 2 — A multi-factor movement, correctly decomposed (Scenario 4)

Click into **"West Region — Technology Sales Drop"**.

> "Three zones, always in this order: What changed, Why it changed, What
> to do — read top to bottom like a comic strip. The trend chart shows the
> actual line dropping outside the shaded normal range, flagged automatically,
> not a canned example."

Point at the **waterfall chart** in "Why it changed."

> "This is a literal picture of the math — Expected, then each driver's
> contribution stacked on, to Actual. It's an LMDI decomposition, not an ad
> hoc split, so the bars sum exactly. Units sold and discounting both cut
> into sales here — a genuine multi-cause story, shown as two red bars, not
> hidden in a paragraph."

Point at the driver chips below.

> "Icon, plain-language name, a confidence bar, the contribution percentage
> — no jargon, no snake_case names."

## Scene 3 — Two personas, one event (Scenario 3)

Toggle to **Analyst view** (same scenario).

> "Same screen, more depth — not a different page. The driver chips now
> show the technical names, the trend chart labels switch to 'forecast
> band,' and the Evidence drawer opens by default with the full
> correlation table and written analysis. Toggle back to Leader view —"

Toggle back.

> "— and it's the plain-language version again: three sentences, one
> recommended action, no statistics."

## Scene 4 — Ambiguous evidence: the system abstains (Scenario 5)

Back to the Command Center, click **"Central — Office Supplies Margin
Compression"**.

> "This is the case the brief asks for explicitly. Notice the visual
> treatment is deliberately different — a dashed border, muted tone, a '?'
> icon — not the same card with sadder text. Two competing explanations,
> cost-mix shift and discounting, sit side by side with their own
> confidence bars, because the evidence doesn't clearly favor one. That's a
> feature: the system is being honest, not broken."

## Scene 5 — Sparse history, not just low confidence (Scenario 6)

Click **"Emerging Sub-Category — 3D Printers"**.

> "A real, low-volume slice of the actual dataset — a newly launched
> product line with about six weeks of history, not a fabricated scenario.
> The confidence dot here is capped by data completeness, not statistical
> ambiguity — the movement itself is a clean, large drop."

## Scene 6 — Security: a persona blocked from seeing data outside scope (Scenario 7)

Toggle to **Leader view**, then click the **East** region pill.

> "The Command Center grid changes — West-only cards are gone, replaced by
> East and region-agnostic ones. This is server-enforced, not a client-side
> filter: requesting the West scenario directly as the East leader returns
> a 403."

Open the **Evidence** drawer on any card and click **View underlying raw
records**.

> "Column-level scoping too — customer identity columns are absent from
> this response body entirely for a regional-leader persona, not just
> hidden in the UI."

## Scene 7 — What to do, and the feedback loop

Scroll to **"What to do."**

> "One driver, one lever, one action — icon, a plain-language recommendation,
> a real before/after bar showing the gap this action targets, and an owner.
> Mark as done is a real, single-click feedback capture — it appends to an
> append-only analyst-verdict log, not a form."

Click **Mark as done** (or **Override** to show the correction-note path).

## Scene 8 — Evidence, lineage, and the LLM-vs-non-LLM breakdown (Scenarios 8 & 9)

Open the **Evidence** drawer (Analyst view shows it open by default).

> "This is the literal 'LLM vs. non-LLM' requirement — as a lit-up flow
> diagram, not prose. Data and Stats compute the movement and drivers;
> Rules pick the action from a fixed playbook; the LLM lights up last, and
> only phrases the final sentence. Related signals show as chips —
> 'causally supported' vs. 'correlated' vs. 'insufficient evidence' — with
> the rationale on hover, and the lineage trail runs from the raw
> Kaggle-shaped file down to this exact number."

## Scene 9 — Runtime telemetry (Scenario 10)

Point at the **corner badge** (bottom-right, always visible).

> "Every LLM call is instrumented live — latency, tokens, cost, and which
> tier, cheap or strong, handled it. Tiering reads directly off the
> confidence score the Reasoning layer already computed. Reload the same
> scenario —"

Click back into a scenario already viewed this session.

> "— and the badge flips to 'Instant (cached)': zero additional LLM cost
> for a repeat question."

## Scene 10 — Grounding: a trust check, not a claim

Open **Written analysis** and point at the **Verified** / **N unverified**
badge.

> "After every LLM call, we regex-extract every number it wrote and verify
> it traces back to the evidence packet it was given. This isn't
> theoretical — during development, the local fallback model wrote
> statistics jargon and a raw internal driver name straight into a
> business-leader briefing; a deterministic guardrail caught it and
> replaced the narrative with a template built directly from the evidence,
> without knowing in advance what error the model would make."

---

## Timing note

The local Ollama fallback (used automatically without an `OPENAI_API_KEY`)
takes 30-90 seconds per narrative call on CPU-only hardware — expected and
documented, not a bug. The trend chart and KPI Command Center grid render
instantly regardless (they never wait on the LLM); only "Why it changed"
and "What to do" show a brief skeleton state while the narrative call is in
flight. For a snappier recording, set `OPENAI_API_KEY` in `backend/.env`
(response time drops to 1-5 seconds), or pre-warm the cache by loading each
scenario once before hitting record.
