# AI Change Gate

> **CI for AI behaviour.**

**AI Change Gate** is an experimental regression-testing and evaluation-gating framework for AI-powered applications.

When a developer changes an application prompt, model configuration, or evaluation rubric, conventional unit tests often still pass while conversational or grading quality silently degrades. AI Change Gate sits directly in front of those changes: it replays baseline vs candidate configurations against the same standardized evaluation set, compares behavior and scores, detects regressions, and issues an automated gate verdict:

```text
Baseline AI behavior
        ↓
Same evaluation set
        ↓
Candidate AI behavior
        ↓
Compare
        ↓
PASS / FAIL / INCONCLUSIVE
```

---

## Target Application & Target Feature

The initial real-world target application for AI Change Gate is **Conquer** (an AI-powered technical interview preparation simulator).

Specifically, the first target feature being gated is Conquer's:
**Per-Question Answer Scorer & Profile Generator** (`POST /api/interview/score`)

This feature scores candidate answers on a 0.0–10.0 scale using an LLM grading rubric, applies deterministic checks (length, STAR compliance, code formatting), updates running candidate skill profile deltas, and drives adaptive difficulty transitions. Gating this feature ensures that prompt adjustments or model upgrades do not cause scoring drift, leniency/harshness anomalies, or rubric hallucinations.

---

## Status: Initial Implementation Spike

> **Note on Evaluation Methodology**:
> This repository represents an **initial implementation spike** establishing the project skeleton, typed domain models, execution runner, and CLI interface.
>
> The evaluation methodology, statistical significance testing, and LLM-as-a-Judge protocols are **intentionally provisional**. Final scoring formulas and benchmark datasets will be revised following our literature review on judge bias, calibration, and LLM evaluation benchmarks.

---

## Project Structure

```text
ai-change-gate/
├── README.md
├── pyproject.toml
├── src/
│   └── ai_change_gate/
│       ├── __init__.py
│       ├── models.py       # Domain models (EvaluationCase, Result, Run, Verdict)
│       ├── runner.py       # Execution runner & MockEvaluator abstraction
│       ├── comparator.py   # Provisional comparison & gating logic
│       └── cli.py          # Command-line interface
├── evals/
│   └── conquer/
│       └── cases.json      # 5 placeholder development cases (not final benchmark)
├── tests/
│   ├── test_models.py      # Domain model unit tests
│   ├── test_comparator.py  # Gate comparison rule tests (PASS, FAIL, INCONCLUSIVE)
│   └── test_runner.py      # Runner & mock evaluator tests
└── docs/
    ├── NOTES.md            # Research agenda, current status, and roadmap
    ├── DECISIONS.md        # Architectural decision records
    ├── PROJECT_PLAN-2.md   # Overall master plan
    └── DEVELOPMENT_RULES-2.md # Development guidelines
```

---

## Quickstart

### 1. Installation

Requires Python 3.11+. Install in editable mode:

```bash
pip install -e .
```

To install test dependencies:

```bash
pip install -e ".[dev]"
```

### 2. Run Tests

Execute the unit test suite using `pytest`:

```bash
pytest
```

### 3. Run the CLI

Run the CLI gate on the default Conquer development evaluation cases:

```bash
# Default demonstration (PASS)
ai-change-gate

# Or using Python module execution:
python3 -m ai_change_gate.cli

# Simulate a critical regression detection (FAIL):
ai-change-gate --demo fail

# Simulate a negligible difference (INCONCLUSIVE):
ai-change-gate --demo inconclusive
```

---

## Next Steps

Before implementing the production LLM evaluators and database persistence, we will conduct a literature review covering:
- **LLM-as-a-Judge** (Zheng et al., 2023)
- **G-Eval & Rubric-based Scoring** (Liu et al., 2023)
- **Mitigating Judge Biases** (position bias, verbosity bias, self-enhancement)
- **Bootstrap Confidence Intervals & Paired Difference Tests**
- **Benchmark Design for Software Engineering Q&A**
