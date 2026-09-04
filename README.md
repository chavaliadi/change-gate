# AI Change Gate

**CI for AI behaviour.**

You change a prompt, your tests still pass, and you find out from a user that quality dropped. The AI Change Gate sits in front of that change — replay old vs new, compare quality / cost / latency, return PASS / FAIL / INCONCLUSIVE with a per-case diff.

Not an observability dashboard. Not an LLM gateway. Not a prompt playground.

---

## Stack

| Layer | Choice |
|---|---|
| Language | Python 3.11+ |
| Interface | CLI (Phase 1–2) → FastAPI (Phase 3+) |
| DB | PostgreSQL |
| LLM access | Provider SDKs + hand-written wrapper. No LangChain. |
| Cache / queue | Redis (Phase 3+) |
| Frontend | Next.js + strict TypeScript + Tailwind (Phase 5) |
| Orchestration | LangGraph — eval generator only, decided Phase 3 |
| Tool interface | MCP (Phase 6) |
| Cloud | AWS (Phase 6) |

## Portfolio story

**AI Engineering** — evaluation methodology, statistics, LLMOps, MCP, Postgres depth.

---

## Current phase

**Phase 0 — design, no code.**

Open items before Phase 1 starts:
- [ ] Pick the target application — Conceptra / Conquer / KnowledgeHub
- [ ] Write eval methodology: regression threshold, case count, repetitions, verdict definitions
- [ ] Confirm schema and API contracts on paper

---

## Docs

| File | What it covers |
|---|---|
| `docs/PROJECT_PLAN.md` | MVP scope, phases, schema, API, system design, risks |
| `docs/DECISIONS.md` | Every architectural decision + rejected alternative |
| `docs/DEVELOPMENT_RULES.md` | Build split, code conventions, what agent does / doesn't write |

---

## Rules for the coding agent

- Read `docs/PROJECT_PLAN.md` before implementing any new component
- Sections marked 🟢 are written by the human — explain and review, do not implement
- Do not introduce Phase 3+ technology during Phase 1–2 work
- Cache is exact-match only — never semantic
- When a suggestion conflicts with `docs/DECISIONS.md`, surface the conflict rather than routing around it
