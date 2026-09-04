# Development Rules — AI Change Gate

How code gets written in this project. The agent reads this on every prompt.

---

## Build split

This project exists so the human learns systems engineering, not so it ships fast.

| Mark | Meaning |
|---|---|
| 🟢 | Human writes this. Agent does not implement it. |
| 🟡 | Agent-assisted. Human reviews and must explain every decision. |
| 🔴 | Agent handles it. Boilerplate, CRUD, config, migrations, docs. |

### 🟢 — do not implement these

| Component | Why it's yours |
|---|---|
| Eval methodology + thresholds | Core product design |
| Target selection + first eval set | Requires domain judgment |
| Database schema + index design | Postgres-depth learning target |
| API contracts | System design learning |
| Paired comparison + bootstrap CI | The intellectual core |
| Judge calibration | Everything sits on top of this |
| Cache key design + idempotency | Reproducibility is the product |
| Model wrapper | Needs to be fully visible for debugging |
| Factorial attribution (Phase 4) | The memorable differentiator |

**When asked about a 🟢 component:** explain concepts, discuss trade-offs, review what the human wrote, point out bugs, answer questions. Pseudocode for a concept is fine when asked. Do not produce the finished implementation.

If the human explicitly asks the agent to write a 🟢 component: ask once whether they want to write it themselves, then comply only if they confirm.

### 🟡 — assist, then explain

Eval generator, worker pool, frontend, MCP server.

When handing back 🟡 work: include a short note on why it was built that way — the alternative rejected and the reason. The human will ask; save them the round trip.

### 🔴 — just do it

CRUD endpoints, migrations, config loading, obvious-case tests, docstrings, README updates.

---

## Phase discipline

Do not implement features from a later phase during earlier work. Current phases:

| Phase | What | Tier |
|---|---|---|
| 0 | Design, no code. Target app, methodology doc, schema on paper. | 🟢 |
| 1 | CLI: two prompt versions → eval set → scores → verdict | 🟢 MVP |
| 2 | LLM judge + calibration kill gate + bootstrap CI | 🟢 MVP |
| 3 | FastAPI + Redis cache/queue + workers + eval generator | 🟡 |
| 4 | Model as second variable + factorial attribution | 🟢 |
| 5 | Next.js frontend, strict TypeScript | 🟡 🔵 |
| 6 | MCP server + AWS deploy | 🔵 |

**Phase 1–2 have no FastAPI and no frontend.** Do not scaffold them early.

---

## Code conventions

### Python
- 3.11+, type hints on all function signatures — no bare untyped functions
- `ruff` for lint and format
- Pydantic for all boundary data: API request/response, LLM structured outputs, config
- `pytest` for tests, fixtures for external dependencies
- No bare `except:` — catch specific exceptions
- `async` for anything doing I/O concurrently

### SQL / PostgreSQL
- Migrations for every schema change — never manual DDL in production
- Explicit column lists — never `SELECT *`
- Every index gets a comment explaining which query it serves
- Money stored as integer cents, never float

### TypeScript (Phase 5 only)
- `strict: true`, zero `any` — TypeScript depth is an explicit learning target here
- Types derived from a shared schema, not hand-duplicated from the backend

---

## Cost discipline

This project makes real paid API calls in normal operation. That's unusual — guard it.

- Use the cheapest available model as the *target* during development
- Always check the cache before any provider call
- Never write a loop calling a provider without a hard iteration bound
- When adding a feature that increases call volume, say so explicitly
- Never call a provider from a test in the normal test sweep — mark provider tests separately and run them deliberately

---

## What to flag rather than fix

Raise these to the human instead of resolving silently:

- A rule in this file or `DECISIONS.md` that appears wrong or contradicts the spec
- A statistical or methodological choice that looks incorrect
- A request that belongs to a later phase (scope creep)
- Anything that would make replays non-reproducible
- A schema change that would need a data backfill
- A new dependency without an obvious reason

Raising conflicts is more useful than quietly working around them.

---

## Non-negotiable constraints (short form)

Full reasoning in `DECISIONS.md`. These are the rules, not the arguments:

- Cache is **exact-match** — `sha256(rendered_prompt + model + params_json + input_json)`. Never semantic.
- **No LangChain.** Hand-written model wrapper only.
- **Paired comparison** — `delta_i = score(candidate, case_i) − score(baseline, case_i)`. Never compare independent means.
- **INCONCLUSIVE** is a real verdict — never round it to PASS or FAIL.
- **Judge runs as a separate stage**, not inline with execution.
- **Executions are idempotent**, keyed `(variant_id, eval_case_id, repetition_no)`.
- Every run has a **budget ceiling** — estimate first, refuse if over, abort if exceeded mid-run.
