import pytest

from ai_change_gate.judge import MockPairwiseJudge
from ai_change_gate.models import (
    Criterion,
    EvaluationCase,
    NormalizedWinner,
    PairwiseJudgment,
    PairwiseWinner,
    Rubric,
    classify_consistency,
    ConsistencyOutcome,
)
from ai_change_gate.pairwise_runner import BidirectionalPairwiseRunner


def _create_sample_case(case_id: str = "case-1") -> EvaluationCase:
    return EvaluationCase(
        id=case_id,
        topic="Distributed Systems",
        question="What is the CAP theorem?",
        candidate_answer="Consistency, Availability, Partition tolerance trade offs.",
    )


def test_forward_pass_normalization_mappings():
    # Pass 1 presentation: A is Baseline, B is Candidate
    assert BidirectionalPairwiseRunner._normalize_pass1(PairwiseWinner.A) == NormalizedWinner.BASELINE
    assert BidirectionalPairwiseRunner._normalize_pass1(PairwiseWinner.B) == NormalizedWinner.CANDIDATE
    assert BidirectionalPairwiseRunner._normalize_pass1(PairwiseWinner.TIE) == NormalizedWinner.TIE


def test_reverse_pass_normalization_mappings():
    # Pass 2 presentation: A is Candidate, B is Baseline
    assert BidirectionalPairwiseRunner._normalize_pass2(PairwiseWinner.A) == NormalizedWinner.CANDIDATE
    assert BidirectionalPairwiseRunner._normalize_pass2(PairwiseWinner.B) == NormalizedWinner.BASELINE
    assert BidirectionalPairwiseRunner._normalize_pass2(PairwiseWinner.TIE) == NormalizedWinner.TIE


def test_judge_called_exactly_twice():
    j1 = PairwiseJudgment(winner=PairwiseWinner.A, reason="Pass 1 judgment")
    j2 = PairwiseJudgment(winner=PairwiseWinner.B, reason="Pass 2 judgment")
    mock_judge = MockPairwiseJudge(judgments=[j1, j2])

    runner = BidirectionalPairwiseRunner(mock_judge)
    case = _create_sample_case()

    runner.evaluate(
        case=case,
        baseline_output="Baseline response text",
        candidate_output="Candidate response text",
    )

    assert len(mock_judge.calls) == 2


def test_call_order_presentation_swap():
    j1 = PairwiseJudgment(winner=PairwiseWinner.A, reason="Pass 1 judgment")
    j2 = PairwiseJudgment(winner=PairwiseWinner.B, reason="Pass 2 judgment")
    mock_judge = MockPairwiseJudge(judgments=[j1, j2])

    runner = BidirectionalPairwiseRunner(mock_judge)
    case = _create_sample_case()
    baseline_text = "Baseline output text for comparison"
    candidate_text = "Candidate output text for comparison"

    runner.evaluate(
        case=case,
        baseline_output=baseline_text,
        candidate_output=candidate_text,
    )

    first_call = mock_judge.calls[0]
    second_call = mock_judge.calls[1]

    # Pass 1: output_a is baseline, output_b is candidate
    assert first_call.output_a == baseline_text
    assert first_call.output_b == candidate_text

    # Pass 2: output_a is candidate, output_b is baseline
    assert second_call.output_a == candidate_text
    assert second_call.output_b == baseline_text


def test_both_passes_receive_same_case_and_rubric():
    j1 = PairwiseJudgment(winner=PairwiseWinner.A, reason="Pass 1")
    j2 = PairwiseJudgment(winner=PairwiseWinner.B, reason="Pass 2")
    mock_judge = MockPairwiseJudge(judgments=[j1, j2])

    runner = BidirectionalPairwiseRunner(mock_judge)
    case = _create_sample_case(case_id="case-rubric-test")
    rubric = Rubric(
        name="System Design Criteria",
        criteria=[
            Criterion(name="Depth", description="Depth of architecture analysis.", weight=2.0),
        ],
    )

    runner.evaluate(
        case=case,
        baseline_output="Base",
        candidate_output="Cand",
        rubric=rubric,
    )

    call1 = mock_judge.calls[0]
    call2 = mock_judge.calls[1]

    assert call1.case == case
    assert call2.case == case
    assert call1.rubric == rubric
    assert call2.rubric == rubric


def test_result_preserves_raw_judgments_and_normalized_winners():
    j1 = PairwiseJudgment(
        winner=PairwiseWinner.B,
        reason="Pass 1 raw reason: position B was more specific.",
        confidence=0.91,
    )
    j2 = PairwiseJudgment(
        winner=PairwiseWinner.A,
        reason="Pass 2 raw reason: position A was more specific.",
        confidence=0.88,
    )
    mock_judge = MockPairwiseJudge(judgments=[j1, j2])

    runner = BidirectionalPairwiseRunner(mock_judge)
    case = _create_sample_case()

    result = runner.evaluate(
        case=case,
        baseline_output="Base",
        candidate_output="Cand",
    )

    # Raw judgments preserved
    assert result.pass1_judgment == j1
    assert result.pass2_judgment == j2
    assert result.pass1_raw_judgment == j1
    assert result.pass2_raw_judgment == j2

    # Normalized winners preserved
    assert result.pass1_normalized_winner == NormalizedWinner.CANDIDATE
    assert result.pass2_normalized_winner == NormalizedWinner.CANDIDATE


def test_position_bias_raw_winner_a_in_both_passes():
    # Simulated position bias: evaluator always chooses whichever response appears in position A
    j1 = PairwiseJudgment(winner=PairwiseWinner.A, reason="Position A favored in pass 1")
    j2 = PairwiseJudgment(winner=PairwiseWinner.A, reason="Position A favored in pass 2")
    mock_judge = MockPairwiseJudge(judgments=[j1, j2])

    runner = BidirectionalPairwiseRunner(mock_judge)
    case = _create_sample_case()

    result = runner.evaluate(
        case=case,
        baseline_output="Base",
        candidate_output="Cand",
    )

    # Raw position winners are identical (both A)
    assert result.pass1_judgment.winner == PairwiseWinner.A
    assert result.pass2_judgment.winner == PairwiseWinner.A

    # Normalized identities disagree because presentation positions swapped
    assert result.pass1_normalized_winner == NormalizedWinner.BASELINE
    assert result.pass2_normalized_winner == NormalizedWinner.CANDIDATE

    # The disagreement exposes position instability
    outcome = classify_consistency(result.pass1_normalized_winner, result.pass2_normalized_winner)
    assert outcome == ConsistencyOutcome.POSITION_UNSTABLE


def test_consistent_candidate_win():
    # Candidate wins both passes:
    # Pass 1: A=Baseline, B=Candidate -> B wins
    # Pass 2: A=Candidate, B=Baseline -> A wins
    j1 = PairwiseJudgment(winner=PairwiseWinner.B, reason="Candidate in position B is superior")
    j2 = PairwiseJudgment(winner=PairwiseWinner.A, reason="Candidate in position A is superior")
    mock_judge = MockPairwiseJudge(judgments=[j1, j2])

    runner = BidirectionalPairwiseRunner(mock_judge)
    case = _create_sample_case()

    result = runner.evaluate(
        case=case,
        baseline_output="Base",
        candidate_output="Cand",
    )

    assert result.pass1_normalized_winner == NormalizedWinner.CANDIDATE
    assert result.pass2_normalized_winner == NormalizedWinner.CANDIDATE

    outcome = classify_consistency(result.pass1_normalized_winner, result.pass2_normalized_winner)
    assert outcome == ConsistencyOutcome.CONSISTENT_CANDIDATE_WIN


def test_consistent_baseline_win():
    # Baseline wins both passes:
    # Pass 1: A=Baseline, B=Candidate -> A wins
    # Pass 2: A=Candidate, B=Baseline -> B wins
    j1 = PairwiseJudgment(winner=PairwiseWinner.A, reason="Baseline in position A is superior")
    j2 = PairwiseJudgment(winner=PairwiseWinner.B, reason="Baseline in position B is superior")
    mock_judge = MockPairwiseJudge(judgments=[j1, j2])

    runner = BidirectionalPairwiseRunner(mock_judge)
    case = _create_sample_case()

    result = runner.evaluate(
        case=case,
        baseline_output="Base",
        candidate_output="Cand",
    )

    assert result.pass1_normalized_winner == NormalizedWinner.BASELINE
    assert result.pass2_normalized_winner == NormalizedWinner.BASELINE

    outcome = classify_consistency(result.pass1_normalized_winner, result.pass2_normalized_winner)
    assert outcome == ConsistencyOutcome.CONSISTENT_BASELINE_WIN


def test_consistent_tie():
    j1 = PairwiseJudgment(winner=PairwiseWinner.TIE, reason="Both equivalent on pass 1")
    j2 = PairwiseJudgment(winner=PairwiseWinner.TIE, reason="Both equivalent on pass 2")
    mock_judge = MockPairwiseJudge(judgments=[j1, j2])

    runner = BidirectionalPairwiseRunner(mock_judge)
    case = _create_sample_case()

    result = runner.evaluate(
        case=case,
        baseline_output="Base",
        candidate_output="Cand",
    )

    assert result.pass1_normalized_winner == NormalizedWinner.TIE
    assert result.pass2_normalized_winner == NormalizedWinner.TIE

    outcome = classify_consistency(result.pass1_normalized_winner, result.pass2_normalized_winner)
    assert outcome == ConsistencyOutcome.CONSISTENT_TIE
