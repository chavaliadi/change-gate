from ai_change_gate.models import (
    ComparisonResult,
    EvaluationCase,
    EvaluationResult,
    EvaluationRun,
    Verdict,
)


def test_verdict_enum():
    assert Verdict.PASS == "PASS"
    assert Verdict.FAIL == "FAIL"
    assert Verdict.INCONCLUSIVE == "INCONCLUSIVE"
    assert len(Verdict) == 3


def test_evaluation_case_construction():
    case = EvaluationCase(
        id="case-001",
        topic="System Design",
        question="Explain horizontal vs vertical scaling.",
        candidate_answer="Vertical adds more RAM/CPU to one machine. Horizontal adds more machines.",
        mode="STANDARD",
        metadata={"difficulty": "Medium"},
    )
    assert case.id == "case-001"
    assert case.topic == "System Design"
    assert case.mode == "STANDARD"
    assert case.rubric is None
    assert case.metadata["difficulty"] == "Medium"


def test_evaluation_result_construction():
    result = EvaluationResult(
        case_id="case-001",
        score=8.5,
        feedback="Strong concise answer.",
        metadata={"latency_ms": 120},
    )
    assert result.case_id == "case-001"
    assert result.score == 8.5
    assert result.feedback == "Strong concise answer."
    assert result.metadata["latency_ms"] == 120


def test_evaluation_run_properties():
    r1 = EvaluationResult(case_id="c1", score=6.0, feedback="OK")
    r2 = EvaluationResult(case_id="c2", score=8.0, feedback="Good")

    run = EvaluationRun(
        run_id="run-1",
        version="v1.0",
        results=[r1, r2],
    )
    assert run.run_id == "run-1"
    assert run.version == "v1.0"
    assert run.case_count == 2
    assert run.average_score == 7.0
    assert run.get_result("c1") == r1
    assert run.get_result("c2") == r2
    assert run.get_result("non-existent") is None


def test_evaluation_run_empty():
    run = EvaluationRun(run_id="run-empty", version="v0")
    assert run.case_count == 0
    assert run.average_score == 0.0


def test_comparison_result_construction():
    comp = ComparisonResult(
        verdict=Verdict.PASS,
        summary="Clear improvement with no regressions.",
        baseline_version="v1",
        candidate_version="v2",
        baseline_avg_score=6.5,
        candidate_avg_score=8.0,
        score_diff=1.5,
        regressions=[],
        improvements=[{"case_id": "c1", "diff": 1.5}],
    )
    assert comp.verdict == Verdict.PASS
    assert comp.score_diff == 1.5
    assert len(comp.improvements) == 1
    assert len(comp.regressions) == 0
