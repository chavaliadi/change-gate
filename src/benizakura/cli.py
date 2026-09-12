from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import List

from benizakura.comparator import SimpleComparator
from benizakura.models import EvaluationCase
from benizakura.runner import EvaluationRunner, MockEvaluator


def load_cases(path: Path) -> List[EvaluationCase]:
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    raw_cases = data.get("cases", []) if isinstance(data, dict) else data
    cases = []
    for item in raw_cases:
        cases.append(
            EvaluationCase(
                id=item["id"],
                topic=item["topic"],
                question=item["question"],
                candidate_answer=item["candidate_answer"],
                mode=item.get("mode", "STANDARD"),
                rubric=item.get("rubric"),
                metadata=item.get("metadata", {}),
            )
        )
    return cases


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="benizakura",
        description="Benizakura: Regression testing change gate for AI behavior.",
    )
    parser.add_argument(
        "--cases",
        type=Path,
        default=Path("evals/conquer/cases.json"),
        help="Path to evaluation cases JSON file.",
    )
    parser.add_argument(
        "--demo",
        choices=["pass", "fail", "inconclusive"],
        default="pass",
        help="Simulate demonstration scenario (pass, fail, or inconclusive). Default: pass.",
    )
    parser.add_argument(
        "--baseline-version",
        default="v1",
        help="Baseline version identifier.",
    )
    parser.add_argument(
        "--candidate-version",
        default="v2",
        help="Candidate version identifier.",
    )

    args = parser.parse_args(argv)

    cases_path = args.cases
    if not cases_path.is_file():
        # Try relative to repo root if run from a different subfolder
        candidate_path = Path(__file__).resolve().parent.parent.parent / args.cases
        if candidate_path.is_file():
            cases_path = candidate_path
        else:
            print(f"Error: Evaluation cases file not found at {args.cases}", file=sys.stderr)
            return 1

    cases = load_cases(cases_path)

    # Setup mock evaluators based on requested demonstration mode
    if args.demo == "fail":
        baseline_evaluator = MockEvaluator(default_score=8.0)
        # Induce a critical drop on the first case
        critical_case_id = cases[0].id if cases else "case-1"
        candidate_evaluator = MockEvaluator(
            default_score=8.0,
            case_overrides={critical_case_id: {"score": 3.5, "feedback": "Critical regression."}},
        )
    elif args.demo == "inconclusive":
        baseline_evaluator = MockEvaluator(default_score=7.0)
        candidate_evaluator = MockEvaluator(default_score=7.05)
    else:  # "pass"
        baseline_evaluator = MockEvaluator(default_score=6.8)
        candidate_evaluator = MockEvaluator(default_score=8.2)

    baseline_runner = EvaluationRunner(baseline_evaluator)
    candidate_runner = EvaluationRunner(candidate_evaluator)

    baseline_run = baseline_runner.run(cases, version=args.baseline_version)
    candidate_run = candidate_runner.run(cases, version=args.candidate_version)

    comparator = SimpleComparator()
    comparison = comparator.compare(baseline_run, candidate_run)

    print("Benizakura")
    print("==========")
    print()
    print(f"Evaluation cases: {len(cases)}")
    print()
    print(f"Baseline:  {comparison.baseline_version} (avg: {comparison.baseline_avg_score:.2f})")
    print(f"Candidate: {comparison.candidate_version} (avg: {comparison.candidate_avg_score:.2f})")
    print()
    print(f"Verdict: {comparison.verdict.value}")
    print()
    print("Summary:")
    print(comparison.summary)

    if comparison.regressions:
        print()
        print("Detected Regressions:")
        for reg in comparison.regressions:
            print(f"  - [{reg['case_id']}] baseline={reg['baseline_score']} -> candidate={reg['candidate_score']} ({reg['reason']})")

    return 0 if comparison.verdict.value == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
