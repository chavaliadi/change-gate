import pytest

from ai_change_gate.judge import MockPairwiseJudge, PairwiseJudge, PairwiseJudgeCall
from ai_change_gate.models import (
    Criterion,
    EvaluationCase,
    PairwiseJudgment,
    PairwiseWinner,
    Rubric,
)


def _create_sample_case(case_id: str = "case-1") -> EvaluationCase:
    return EvaluationCase(
        id=case_id,
        topic="Databases",
        question="Explain ACID properties in relational databases.",
        candidate_answer="ACID stands for Atomicity, Consistency, Isolation, Durability.",
    )


def test_mock_judge_returns_configured_a_winner():
    judgment_a = PairwiseJudgment(
        winner=PairwiseWinner.A,
        reason="Answer A provided concrete real world examples.",
        confidence=0.9,
    )
    judge = MockPairwiseJudge(default_judgment=judgment_a)
    case = _create_sample_case()

    result = judge.judge(case, output_a="Detailed answer", output_b="Brief answer")

    assert result.winner == PairwiseWinner.A
    assert result.reason == "Answer A provided concrete real world examples."
    assert result.confidence == 0.9


def test_mock_judge_returns_configured_b_winner():
    judgment_b = PairwiseJudgment(
        winner=PairwiseWinner.B,
        reason="Answer B identified edge cases and failure modes.",
        confidence=0.85,
    )
    judge = MockPairwiseJudge(default_judgment=judgment_b)
    case = _create_sample_case()

    result = judge.judge(case, output_a="Basic answer", output_b="Thorough answer")

    assert result.winner == PairwiseWinner.B
    assert result.reason == "Answer B identified edge cases and failure modes."
    assert result.confidence == 0.85


def test_mock_judge_returns_configured_tie():
    # When no explicit judgment is supplied, mock judge defaults to neutral tie
    judge_default = MockPairwiseJudge()
    case = _create_sample_case()

    result_default = judge_default.judge(case, output_a="Answer 1", output_b="Answer 2")
    assert result_default.winner == PairwiseWinner.TIE

    # Explicit tie judgment
    explicit_tie = PairwiseJudgment(
        winner=PairwiseWinner.TIE,
        reason="Both answers are substantively equivalent.",
    )
    judge_explicit = MockPairwiseJudge(default_judgment=explicit_tie)
    result_explicit = judge_explicit.judge(case, output_a="Answer 1", output_b="Answer 2")
    assert result_explicit.winner == PairwiseWinner.TIE
    assert result_explicit.reason == "Both answers are substantively equivalent."


def test_mock_judge_multiple_responses_in_order():
    j1 = PairwiseJudgment(winner=PairwiseWinner.A, reason="First call: A won.")
    j2 = PairwiseJudgment(winner=PairwiseWinner.B, reason="Second call: B won.")
    j3 = PairwiseJudgment(winner=PairwiseWinner.TIE, reason="Third call: Tie.")

    judge = MockPairwiseJudge(judgments=[j1, j2, j3])
    case = _create_sample_case()

    res1 = judge.judge(case, output_a="A1", output_b="B1")
    res2 = judge.judge(case, output_a="A2", output_b="B2")
    res3 = judge.judge(case, output_a="A3", output_b="B3")

    assert res1 == j1
    assert res2 == j2
    assert res3 == j3
    assert len(judge.calls) == 3


def test_mock_judge_queue_exhaustion_raises_index_error():
    j1 = PairwiseJudgment(winner=PairwiseWinner.A, reason="Only one judgment.")
    judge = MockPairwiseJudge(judgments=[j1])
    case = _create_sample_case()

    first_res = judge.judge(case, output_a="A1", output_b="B1")
    assert first_res == j1

    with pytest.raises(IndexError, match="Configured mock pairwise judgments are exhausted"):
        judge.judge(case, output_a="A2", output_b="B2")


def test_mock_judge_queue_exhaustion_fallback_to_default():
    j1 = PairwiseJudgment(winner=PairwiseWinner.A, reason="First call only.")
    fallback = PairwiseJudgment(winner=PairwiseWinner.TIE, reason="Fallback after queue.")

    judge = MockPairwiseJudge(judgments=[j1], default_judgment=fallback)
    case = _create_sample_case()

    first_res = judge.judge(case, output_a="A1", output_b="B1")
    second_res = judge.judge(case, output_a="A2", output_b="B2")

    assert first_res == j1
    assert second_res == fallback


def test_judge_receives_correct_evaluation_case():
    judge = MockPairwiseJudge()
    case = _create_sample_case(case_id="case-42")

    judge.judge(case, output_a="Answer A", output_b="Answer B")

    assert len(judge.calls) == 1
    call: PairwiseJudgeCall = judge.calls[0]
    assert call.case.id == "case-42"
    assert call.case.topic == "Databases"
    assert call.case.question == "Explain ACID properties in relational databases."


def test_judge_receives_output_a_and_output_b_preserved():
    judge = MockPairwiseJudge()
    case = _create_sample_case()
    text_a = "Distinctive text for presentation position A"
    text_b = "Distinctive text for presentation position B"

    judge.judge(case, output_a=text_a, output_b=text_b)

    assert len(judge.calls) == 1
    call = judge.calls[0]
    assert call.output_a == text_a
    assert call.output_b == text_b


def test_judge_receives_supplied_rubric():
    judge = MockPairwiseJudge()
    case = _create_sample_case()
    rubric = Rubric(
        name="Database Engineering Rubric",
        criteria=[
            Criterion(name="Accuracy", description="Correctness of explanation.", weight=2.0),
            Criterion(name="Clarity", description="Ease of understanding.", weight=1.0),
        ],
    )

    judge.judge(case, output_a="Ans A", output_b="Ans B", rubric=rubric)

    assert len(judge.calls) == 1
    call = judge.calls[0]
    assert call.rubric is not None
    assert call.rubric.name == "Database Engineering Rubric"
    assert len(call.rubric.criteria) == 2


def test_mock_judge_case_overrides():
    special_judgment = PairwiseJudgment(
        winner=PairwiseWinner.B,
        reason="Special case override winner B.",
    )
    judge = MockPairwiseJudge(
        default_judgment=PairwiseJudgment(winner=PairwiseWinner.A, reason="Standard A"),
        case_overrides={"special-case": special_judgment},
    )

    special_case = _create_sample_case(case_id="special-case")
    normal_case = _create_sample_case(case_id="normal-case")

    assert judge.judge(special_case, output_a="A", output_b="B") == special_judgment
    assert judge.judge(normal_case, output_a="A", output_b="B").winner == PairwiseWinner.A


def test_pairwise_judge_protocol_compliance():
    judge = MockPairwiseJudge()
    # Verify that MockPairwiseJudge conforms to PairwiseJudge protocol
    assert isinstance(judge, PairwiseJudge)
