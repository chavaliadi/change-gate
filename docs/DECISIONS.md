# Decisions — AI Change Gate

Every architectural decision, with the rejected alternative. These are settled unless marked `open`.
When a new decision is made, append it here using the template at the bottom. Never delete — mark superseded.

---

### D1 — Product is a change gate, not an observability platform
**Status:** active

Observability platforms need production traffic. This project has none — a monitoring dashboard would render empty charts. A gate creates its own workload every time it runs, so it's fully demoable on day one with zero users.

**Rejected:** LLM observability platform. Crowded category (LangSmith, Langfuse, Braintrust, Phoenix), and unusable without traffic.

---

### D2 — MVP gates prompt changes only
**Status:** active

One variable is a comparison. Two is a 2×2 factorial. Four is 16 cells with per-cell sample sizes too small to detect anything. Model becomes variable two in Phase 4, where real attribution unlocks.

**Rejected:** gating prompt + model + params + retrieval from day one.

---

### D3 — No LangChain
**Status:** active

For this project LangChain abstracts over three API calls. A hand-written wrapper (call, retry, token counting, cost calculation, timeout, ~150 lines) means the execution path is fully visible — critical when debugging why a replay diverged. Abstraction hides exactly what needs visibility here.

**Rejected:** LangChain for model abstraction and prompt templating.

---

### D4 — LangGraph only in the eval generator, decided in Phase 3
**Status:** open — decide in Phase 3

The replay flow is fan-out then fan-in: no cycles, no conditional routing. That's `asyncio.gather` + workers; LangGraph there is decoration.

The eval-set generator may need cycles: propose → critique → discard weak → dedupe → regenerate to fill gaps.

**Decision procedure (Phase 3):** design the generator's workflow on paper first. Cycles → adopt LangGraph. Linear → skip it, and pick a replacement learning target (do not drop from four to three targets without replacing).

**Rejected:** LangGraph for the replay pipeline. Also rejected: "use it if it comes up" — that resolves to never once momentum builds.

---

### D5 — Exact-match cache, never semantic
**Status:** active

Key: `sha256(rendered_prompt + model + params_json + input_json)`.

Replay must reproduce exactly. A semantic cache returns an approximately-similar response, making attribution meaningless and the verdict untrustworthy. Reproducibility is the product.

**Rejected:** semantic caching. Legitimate technique for serving — wrong here.

---

### D6 — Paired comparison, not independent means
**Status:** active

`delta_i = score(candidate, case_i) − score(baseline, case_i)`. Test the deltas, not the raw scores.

Pairing removes case difficulty as a variance source. This is the difference between needing 500 cases and needing 50.

**Rejected:** comparing `mean(baseline_scores)` to `mean(candidate_scores)`.

---

### D7 — INCONCLUSIVE is a first-class verdict
**Status:** active

When the bootstrap CI on the mean delta crosses zero, there isn't enough signal. Say so — report CI width and prompt for more cases. Don't round to PASS or FAIL.

**Rejected:** two-way PASS/FAIL, which claims certainty the data doesn't support.

---

### D8 — Judge calibration is a kill gate before Phase 3
**Status:** active

Everything sits on top of the judge. Without calibration, the statistics are precise measurement of noise.

Procedure: hand-label 30–50 outputs → measure Cohen's κ → threshold is κ ≥ 0.6 (or ≥ 80% if binary) → below threshold, fix the rubric and re-measure → do not proceed until it passes.

Also: run judge 3× per output, take median. Store judge prompt as a versioned artifact — a judge change can itself cause a false regression.

**Rejected:** trusting an uncalibrated judge; single-shot judging.

---

### D9 — Postgres, not Mongo
**Status:** active

Core query: "for this run, aggregate scores across variants grouped by case, joined to eval cases and prompt versions." Joins and aggregates — relational shape, not document. Also a deliberate Postgres-depth exercise.

**Rejected:** MongoDB (wrong data shape, already known — teaches nothing new).

---

### D10 — CLI before API before frontend
**Status:** active

Phase 1–2 are a CLI. The engine must be correct before any web layer exists. Building FastAPI and Next.js early is the most common way a project like this stalls at 60%.

**Rejected:** scaffolding FastAPI and Next.js in Phase 1.

---

### D11 — Redis for cache and queue
**Status:** active

Already in the stack for exact-match caching. Handles queuing fine at this scale. Adding RabbitMQ means running two brokers for something Redis covers. Kafka is an event log for many-consumer replay — that problem doesn't exist here.

**Rejected:** RabbitMQ, Kafka.

---

### D12 — Docker parked, not excluded
**Status:** active

Blocked on local storage, not on design. Workers must stay stateless so containerising later is a packaging change, not a redesign.

**Rejected:** designing around Docker's permanent absence.

---

### D13 — Target application chosen from existing projects
**Status:** open — decide in Phase 0

A gate with nothing to gate is a demo. Options: Conceptra (study/explanation prompt), Conquer (interview question generation), KnowledgeHub (RAG answers). Pick one, extract its prompt, params, and 20–30 real inputs as the first eval set.

Later: gate P2's decision-extraction prompts with this tool. Dogfooding beats a synthetic demo.

**Note:** write the threshold and methodology doc before extracting the eval set — don't let familiarity with the target bias what you consider a "passing" quality bar.

---

## Template

```
### D<n> — <one-line decision>
**Status:** active | open | superseded by D<n>

<why, 2–4 sentences>

**Rejected:** <the alternative and why not>
```
