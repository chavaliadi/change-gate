from ai_change_gate.models import EvaluationCase, EvaluationResult
from ai_change_gate.runner import EvaluationRunner, MockEvaluator


def test_mock_evaluator_default():
    evaluator = MockEvaluator(default_score=7.5, default_feedback="Standard test score")
    case = EvaluationCase(
        id="case-1",
        topic="Algorithms",
        question="What is binary search?",
        candidate_answer="O(log n) divide and conquer on sorted data.",
    )
    res = evaluator.evaluate(case)
    assert res.case_id == "case-1"
    assert res.score == 7.5
    assert res.feedback == "Standard test score"


def test_mock_evaluator_overrides():
    overrides = {
        "case-special": {"score": 9.5, "feedback": "Exceptional"}
    }
    evaluator = MockEvaluator(default_score=5.0, case_overrides=overrides)

    case1 = EvaluationCase(id="case-special", topic="T", question="Q", candidate_answer="A")
    case2 = EvaluationCase(id="case-normal", topic="T", question="Q", candidate_answer="A")

    assert evaluator.evaluate(case1).score == 9.5
    assert evaluator.evaluate(case2).score == 5.0


def test_evaluation_runner_flow():
    cases = [
        EvaluationCase(id="c1", topic="T", question="Q1", candidate_answer="A1"),
        EvaluationCase(id="c2", topic="T", question="Q2", candidate_answer="A2"),
    ]
    evaluator = MockEvaluator(default_score=8.0)
    runner = EvaluationRunner(evaluator)

    run = runner.run(cases, version="test-v1", run_id="run-fixed-1")
    assert run.run_id == "run-fixed-1"
    assert run.version == "test-v1"
    assert run.case_count == 2
    assert run.average_score == 8.0
