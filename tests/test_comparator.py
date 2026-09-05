from ai_change_gate.comparator import SimpleComparator
from ai_change_gate.models import EvaluationResult, EvaluationRun, Verdict


def test_comparator_pass_clear_improvement():
    comparator = SimpleComparator(improvement_threshold=0.5)

    baseline = EvaluationRun(
        run_id="b1",
        version="baseline-v1",
        results=[
            EvaluationResult(case_id="c1", score=6.0, feedback="Basic"),
            EvaluationResult(case_id="c2", score=6.5, feedback="Adequate"),
        ],
    )

    candidate = EvaluationRun(
        run_id="c1",
        version="candidate-v2",
        results=[
            EvaluationResult(case_id="c1", score=8.0, feedback="Great"),
            EvaluationResult(case_id="c2", score=8.5, feedback="Excellent"),
        ],
    )

    comparison = comparator.compare(baseline, candidate)

    assert comparison.verdict == Verdict.PASS
    assert comparison.score_diff > 0
    assert len(comparison.regressions) == 0
    assert len(comparison.improvements) == 2
    assert "Clear improvement" in comparison.summary or "improvement" in comparison.summary.lower()


def test_comparator_fail_critical_regression():
    comparator = SimpleComparator(critical_regression_drop=2.0)

    baseline = EvaluationRun(
        run_id="b1",
        version="baseline-v1",
        results=[
            EvaluationResult(case_id="c1", score=8.5, feedback="Strong"),
            EvaluationResult(case_id="c2", score=8.0, feedback="Solid"),
        ],
    )

    # c1 suffers a major drop from 8.5 to 3.5
    candidate = EvaluationRun(
        run_id="c1",
        version="candidate-v2",
        results=[
            EvaluationResult(case_id="c1", score=3.5, feedback="Hallucinated incorrect answer"),
            EvaluationResult(case_id="c2", score=8.0, feedback="Solid"),
        ],
    )

    comparison = comparator.compare(baseline, candidate)

    assert comparison.verdict == Verdict.FAIL
    assert len(comparison.regressions) >= 1
    assert comparison.regressions[0]["case_id"] == "c1"
    assert "regression" in comparison.summary.lower()


def test_comparator_inconclusive_tiny_difference():
    comparator = SimpleComparator(noise_threshold=0.2, improvement_threshold=0.5)

    baseline = EvaluationRun(
        run_id="b1",
        version="baseline-v1",
        results=[
            EvaluationResult(case_id="c1", score=7.0, feedback="Good"),
            EvaluationResult(case_id="c2", score=7.0, feedback="Good"),
        ],
    )

    # Candidate has negligible delta (+0.05 average)
    candidate = EvaluationRun(
        run_id="c1",
        version="candidate-v2",
        results=[
            EvaluationResult(case_id="c1", score=7.1, feedback="Good"),
            EvaluationResult(case_id="c2", score=7.0, feedback="Good"),
        ],
    )

    comparison = comparator.compare(baseline, candidate)

    assert comparison.verdict == Verdict.INCONCLUSIVE
    assert len(comparison.regressions) == 0


def test_comparator_multiple_evaluation_cases():
    comparator = SimpleComparator()

    cases = [f"case-{i}" for i in range(1, 6)]
    b_results = [EvaluationResult(case_id=cid, score=6.0, feedback="Baseline") for cid in cases]
    c_results = [EvaluationResult(case_id=cid, score=7.5, feedback="Candidate improved") for cid in cases]

    baseline = EvaluationRun(run_id="b-multi", version="v1", results=b_results)
    candidate = EvaluationRun(run_id="c-multi", version="v2", results=c_results)

    comparison = comparator.compare(baseline, candidate)

    assert comparison.verdict == Verdict.PASS
    assert comparison.baseline_avg_score == 6.0
    assert comparison.candidate_avg_score == 7.5
    assert comparison.score_diff == 1.5
    assert len(comparison.improvements) == 5
    assert len(comparison.regressions) == 0


def test_comparator_empty_runs():
    comparator = SimpleComparator()
    baseline = EvaluationRun(run_id="b0", version="v1", results=[])
    candidate = EvaluationRun(run_id="c0", version="v2", results=[])

    comparison = comparator.compare(baseline, candidate)
    assert comparison.verdict == Verdict.INCONCLUSIVE
    assert "Insufficient" in comparison.summary
