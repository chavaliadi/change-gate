# Project Plan — Benizakura

Full specification. Read the relevant section before implementing a new component.
Update this file at the end of each phase — tick off milestones, add learnings.

---

## MVP scope

**In:**
- One change type: the prompt template. Model, temperature, params, retrieval all frozen.
- One target per project (a target = one AI feature under test)
- Deterministic evaluators + one calibrated LLM judge
- Paired baseline-vs-candidate replay
- PASS / FAIL / INCONCLUSIVE verdict with per-case diff

**Out — do not implement, do not suggest:**
- Model swaps as a variable (Phase 4, not before)
- Retrieval config as a variable (Phase 5 or never)
- Multi-tenancy, teams, orgs
- Production traffic monitoring
- Auto-fixing or auto-rewriting prompts
- Any dashboard before Phase 5

---

## How it works

```
        Developer / coding agent
                  │
        submits candidate prompt
                  ▼
        ┌──────────────────┐
        │   Run created    │
        └────────┬─────────┘
                 │
     ┌───────────┴───────────┐
     ▼                       ▼
 BASELINE variant      CANDIDATE variant
 (prompt v13)          (prompt v14)
     │                       │
     │  for each eval case   │
     │  × N repetitions      │
     ▼                       ▼
 cache hit? ──yes──▶  use cached output
     │ no
     ▼
  LLM call
     │
     ▼
  executions ────────────────▶ executions
           │                        │
           └──────────┬─────────────┘
                      ▼
              SCORING (deterministic + LLM judge)
                      ▼
              paired per-case deltas
                      ▼
              bootstrap CI on mean delta
                      ▼
              PASS / FAIL / INCONCLUSIVE
```

### Five moving parts

| Part | What it is |
|---|---|
| **Target** | The AI feature under test — prompt template, model, params, input schema |
| **Eval set** | Collection of cases; each case = input + expectations |
| **Run** | One gate invocation; contains two variants (baseline + candidate) |
| **Execution** | One (variant × case × repetition) tuple hitting the model — the atomic unit |
| **Verdict** | Aggregated, significance-tested answer |

---

## Evaluation design (🟢 human writes this)

Layer evaluators — push as much as possible to the deterministic tier:

| Tier | What | Cost | Trust |
|---|---|---|---|
| Deterministic | Schema valid, required fields present, forbidden strings absent, regex, length bounds, refusal detection, latency budget, cost budget | free | high |
| Reference-based | Exact match, F1 vs expected answer, embedding similarity to reference | cheap | medium-high |
| LLM judge | Rubric-scored subjective quality | expensive | needs calibration |

Most real regressions surface as schema violations and refusals, not subtle quality drops.

### Statistical method (🟢 human implements)

**Paired comparison:**
```
delta_i = score(candidate, case_i) − score(baseline, case_i)
```

**Bootstrap CI (10,000 iterations):**
```
for b in 1..10,000:
    sample N deltas with replacement
    record the mean
CI = [2.5th percentile, 97.5th percentile]
```

**Verdict rules:**

| Condition | Verdict |
|---|---|
| CI entirely below regression threshold | FAIL |
| CI entirely above it | PASS |
| CI crosses zero | INCONCLUSIVE — report CI width |

---

## Database schema

```sql
projects
  id, name, created_at

targets
  id, project_id, name, model, params_json,
  input_schema_json, active_prompt_version_id

prompt_versions
  id, target_id, version_no, template, variables_json,
  content_hash, created_at
  UNIQUE (target_id, version_no)

eval_sets
  id, target_id, name, created_at

eval_cases
  id, eval_set_id, input_json, expectations_json,
  tags[], source ('manual'|'generated'|'imported')

judges
  id, name, rubric_template, model, version_no
  -- versioned: a judge prompt change can cause a false regression

runs
  id, target_id, eval_set_id, status,
  baseline_prompt_version_id, candidate_prompt_version_id,
  repetitions, budget_cents, spent_cents,
  started_at, finished_at

variants
  id, run_id, role ('baseline'|'candidate'), prompt_version_id

executions
  id, variant_id, eval_case_id, repetition_no,
  raw_output, tokens_in, tokens_out, cost_cents,
  latency_ms, error, cache_hit, created_at
  INDEX (variant_id, eval_case_id)

scores
  id, execution_id, evaluator_name, evaluator_tier,
  judge_id NULL, value_numeric, value_bool, detail_json

verdicts
  id, run_id, decision ('PASS'|'FAIL'|'INCONCLUSIVE'),
  mean_delta, ci_low, ci_high,
  cost_delta_cents, latency_delta_ms,
  regressed_case_ids[], reason_text

cache_entries
  key_hash PRIMARY KEY,
  raw_output, tokens_in, tokens_out, model,
  created_at, hit_count
```

**Postgres depth to practise:** composite index on `(variant_id, eval_case_id)`, partial index on `executions WHERE error IS NOT NULL`, materialised view for run summaries, `EXPLAIN ANALYZE` on the aggregation query, connection pooling once workers are concurrent.

---

## API surface

```
POST   /projects
POST   /projects/{id}/targets
GET    /targets/{id}

POST   /targets/{id}/prompt-versions
GET    /targets/{id}/prompt-versions

POST   /targets/{id}/eval-sets
POST   /eval-sets/{id}/cases
POST   /eval-sets/{id}/generate          # async, LangGraph if adopted Phase 3
GET    /eval-sets/{id}/cases

POST   /runs                             # {target_id, eval_set_id,
                                         #  candidate_prompt_version_id,
                                         #  repetitions, budget_cents}
GET    /runs/{id}                        # status + progress
GET    /runs/{id}/verdict
GET    /runs/{id}/diff                   # per-case baseline vs candidate
POST   /runs/{id}/cancel

GET    /targets/{id}/history             # verdicts over time
```

### MCP tools (Phase 6)

```
gate.run_check(target, candidate_prompt)  →  run_id
gate.get_verdict(run_id)                  →  PASS|FAIL|INCONCLUSIVE + reason
gate.explain_regression(run_id)           →  which cases broke and how
gate.list_targets()                       →  available targets
```

---

## System design

```
      Next.js (Phase 5)
            │
         HTTPS
            ▼
      FastAPI (Phase 3+)
            │
  ┌─────────┼─────────┐
  ▼         ▼         ▼
Postgres   Redis   Run queue
           cache   (Redis list)
                       │
                       ▼
               Run workers (N)
                       │
            ┌──────────┼──────────┐
            ▼          ▼          ▼
         Model       Judge      Cost
         clients     panel      tracker
```

**Design decisions:**
- Async workers — a run is minutes long. Return `run_id` immediately, client polls.
- Idempotent executions keyed `(variant, case, repetition)` — crashed worker resumes without duplicating spend.
- Cache before spend always — check cache → miss → check budget → call → store.
- Concurrency capped per provider, not globally — rate limits are per-provider.
- Judge runs after execution, not inline — so rubric improvements re-judge history for free.

---

## Phases

### Phase 0 — Design (3–4 days) 🟢
- Pick target application
- Write eval methodology doc
- Schema and API contracts on paper
- **No code.**

**Milestone:** methodology doc exists. Schema drawn. Target app chosen.

---

### Phase 1 — Core replay engine (1.5 weeks) 🟢 MVP
CLI only. No FastAPI, no frontend, no queue, no cache.
Take a target + eval set + two prompt versions → run synchronously → print table.

🟢 schema, model wrapper, evaluator interface
🔴 CRUD boilerplate

**Milestone: quality difference between two prompts visible in terminal.**

---

### Phase 2 — Scoring + verdict (1.5 weeks) 🟢 MVP
LLM judge, judge panel with median, hand-labelled golden set, **calibration kill gate**, paired deltas, bootstrap CI, three-way verdict.

🟢 all of it

**Kill gate before Phase 3:** κ ≥ 0.6 or ≥ 80% agreement on golden set. Below → fix rubric, re-measure.

**Milestone: gate says INCONCLUSIVE when it should, instead of guessing.**

---

### Phase 3 — Async + cache + eval generation (1.5 weeks) 🟡
FastAPI, Redis exact-match cache, Redis-backed job queue, worker processes, budget enforcement, resumable runs.
Then: eval-set generator (LangGraph decision point here — see DECISIONS.md D4).

🟢 cache key design, idempotency, budget logic
🟡 FastAPI setup, worker pool, LangGraph structure if adopted

---

### Phase 4 — Model as second variable (1 week) 🟢
2×2 factorial, main effects, interaction term, attribution report.

🟢 entirely yours — the part that makes this project memorable

---

### Phase 5 — Frontend (1.5 weeks) 🟡 🔵
Run submission, live progress, verdict view, per-case diff, history.

🟡 agent-assisted with review
Strict TypeScript — zero `any`.

---

### Phase 6 — MCP + AWS (1 week) 🔵
Four MCP tools. Deploy: static frontend, FastAPI on compute, RDS, Redis, S3 for artifacts.

---

### Phase 7 — Docker (later)
Containerise workers when storage resolves. Stateless worker design means this is packaging, not redesign.

---

## Phase completion log

| Phase | Status | Notes |
|---|---|---|
| 0 | ⬜ not started | |
| 1 | ⬜ | |
| 2 | ⬜ | |
| 3 | ⬜ | |
| 4 | ⬜ | |
| 5 | ⬜ | |
| 6 | ⬜ | |

---

## Risks

| Risk | Mitigation |
|---|---|
| Judge too noisy → gate useless | Calibration kill gate in Phase 2, before anything is built on top |
| Replay costs spiral | Cache + hard budget ceiling; use cheap model as target during dev |
| Scope creep into observability | Gate answers one question. Production monitoring is a different product. |
| Sample too small to detect signal | Paired design + bootstrap; report CI width, prompt user to add cases |
| Provider rate limits stall runs | Per-provider concurrency caps + exponential backoff |
| Web layer built too early | MVP tier explicitly excludes FastAPI and frontend |
