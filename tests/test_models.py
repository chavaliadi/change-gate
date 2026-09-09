import pytest

from ai_change_gate.models import (
    BidirectionalEvaluationResult,
    BidirectionalResult,
    ComparisonIdentity,
    ComparisonResult,
    ConsistencyClassification,
    ConsistencyOutcome,
    Criterion,
    EvaluationCase,
    EvaluationResult,
    EvaluationRun,
    NormalizedWinner,
    PairwiseJudgment,
    PairwiseWinner,
    RawPositionWinner,
    Rubric,
    Verdict,
    classify_consistency,
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


def test_criterion_construction():
    c1 = Criterion(name="Correctness", description="Checks technical precision.")
    assert c1.name == "Correctness"
    assert c1.description == "Checks technical precision."
    assert c1.weight == 1.0

    c2 = Criterion(name="Depth", description="Evaluates system trade offs.", weight=2.5)
    assert c2.weight == 2.5

    with pytest.raises(ValueError, match="Criterion weight must be non negative"):
        Criterion(name="Invalid", description="Negative weight", weight=-0.5)


def test_rubric_construction():
    c1 = Criterion(name="Accuracy", description="Factual correctness.")
    c2 = Criterion(name="Clarity", description="Clear explanation.", weight=1.5)
    rubric = Rubric(name="Technical Interview Rubric", criteria=[c1, c2])

    assert rubric.name == "Technical Interview Rubric"
    assert len(rubric.criteria) == 2
    assert rubric.criteria[0].name == "Accuracy"
    assert rubric.criteria[1].weight == 1.5

    empty_rubric = Rubric(name="Empty")
    assert empty_rubric.criteria == []


def test_raw_pairwise_winner_enum():
    assert PairwiseWinner.A == "A"
    assert PairwiseWinner.B == "B"
    assert PairwiseWinner.TIE == "TIE"
    assert len(PairwiseWinner) == 3
    assert RawPositionWinner is PairwiseWinner


def test_pairwise_judgment_construction():
    judgment = PairwiseJudgment(
        winner=PairwiseWinner.A,
        reason="Model A provided concrete numbers and handled failure modes.",
        confidence=0.92,
        metadata={"tokens_used": 150},
    )
    assert judgment.winner == PairwiseWinner.A
    assert judgment.reason == "Model A provided concrete numbers and handled failure modes."
    assert judgment.confidence == 0.92
    assert judgment.metadata["tokens_used"] == 150

    judgment_defaults = PairwiseJudgment(
        winner=PairwiseWinner.TIE,
        reason="Both answers covered the basics identically.",
    )
    assert judgment_defaults.confidence is None
    assert judgment_defaults.metadata == {}


def test_normalized_winner_enum():
    assert NormalizedWinner.BASELINE == "BASELINE"
    assert NormalizedWinner.CANDIDATE == "CANDIDATE"
    assert NormalizedWinner.TIE == "TIE"
    assert len(NormalizedWinner) == 3
    assert ComparisonIdentity is NormalizedWinner

    # Normalized winner represents identity, separate from presented position
    assert NormalizedWinner.BASELINE != PairwiseWinner.A
    assert NormalizedWinner.CANDIDATE != PairwiseWinner.B


def test_bidirectional_evaluation_result_construction():
    pass1_judgment = PairwiseJudgment(
        winner=PairwiseWinner.B,
        reason="Position B had clearer failure recovery.",
        confidence=0.85,
    )
    pass2_judgment = PairwiseJudgment(
        winner=PairwiseWinner.A,
        reason="Position A had clearer failure recovery.",
        confidence=0.88,
    )

    # In pass 1 (A=Baseline, B=Candidate), position B winning means Candidate won
    # In pass 2 (A=Candidate, B=Baseline), position A winning also means Candidate won
    result = BidirectionalEvaluationResult(
        pass1_judgment=pass1_judgment,
        pass2_judgment=pass2_judgment,
        pass1_normalized_winner=NormalizedWinner.CANDIDATE,
        pass2_normalized_winner=NormalizedWinner.CANDIDATE,
        metadata={"judge_model": "mock"},
    )

    assert result.pass1_judgment == pass1_judgment
    assert result.pass2_judgment == pass2_judgment
    assert result.pass1_raw_judgment == pass1_judgment
    assert result.pass2_raw_judgment == pass2_judgment
    assert result.pass1_normalized_winner == NormalizedWinner.CANDIDATE
    assert result.pass2_normalized_winner == NormalizedWinner.CANDIDATE
    assert result.metadata["judge_model"] == "mock"
    assert BidirectionalResult is BidirectionalEvaluationResult


def test_consistency_outcome_enum_and_classification():
    assert ConsistencyOutcome.CONSISTENT_CANDIDATE_WIN == "CONSISTENT_CANDIDATE_WIN"
    assert ConsistencyOutcome.CONSISTENT_BASELINE_WIN == "CONSISTENT_BASELINE_WIN"
    assert ConsistencyOutcome.CONSISTENT_TIE == "CONSISTENT_TIE"
    assert ConsistencyOutcome.POSITION_UNSTABLE == "POSITION_UNSTABLE"
    assert len(ConsistencyOutcome) == 4
    assert ConsistencyClassification is ConsistencyOutcome

    # Both passes award candidate
    assert classify_consistency(
        NormalizedWinner.CANDIDATE,
        NormalizedWinner.CANDIDATE,
    ) == ConsistencyOutcome.CONSISTENT_CANDIDATE_WIN

    # Both passes award baseline
    assert classify_consistency(
        NormalizedWinner.BASELINE,
        NormalizedWinner.BASELINE,
    ) == ConsistencyOutcome.CONSISTENT_BASELINE_WIN

    # Both passes tie
    assert classify_consistency(
        NormalizedWinner.TIE,
        NormalizedWinner.TIE,
    ) == ConsistencyOutcome.CONSISTENT_TIE

    # Passes disagree (e.g. position bias where whichever output was presented first won)
    assert classify_consistency(
        NormalizedWinner.BASELINE,
        NormalizedWinner.CANDIDATE,
    ) == ConsistencyOutcome.POSITION_UNSTABLE

