from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class Verdict(str, Enum):
    """Evaluation outcome verdict for comparing baseline vs candidate AI behavior."""
    PASS = "PASS"
    FAIL = "FAIL"
    INCONCLUSIVE = "INCONCLUSIVE"


@dataclass
class EvaluationCase:
    """Represents a single evaluation test case input.

    Attributes:
        id: Unique identifier for the test case.
        topic: Domain/track topic (e.g., 'System Design', 'Algorithms').
        question: The interview question or prompt presented to the candidate.
        candidate_answer: The candidate's response text being graded.
        mode: Interview mode (e.g., 'STANDARD', 'QUICK_FIRE', 'DEEP_DIVE').
        rubric: Optional placeholder for case-specific grading rubric criteria.
        metadata: Optional dictionary for additional metadata (tags, expected level, etc.).
    """
    id: str
    topic: str
    question: str
    candidate_answer: str
    mode: str = "STANDARD"
    rubric: Optional[Dict[str, Any]] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class EvaluationResult:
    """Represents the evaluation output produced for one evaluation case.

    Attributes:
        case_id: Reference identifier matching the evaluated EvaluationCase.id.
        score: Numerical evaluation score (typically 0.0 to 10.0 in Conquer).
        feedback: Qualitative feedback or critique generated for the response.
        metadata: Optional dictionary for auxiliary output (e.g. latency, token count, profile delta).
    """
    case_id: str
    score: float
    feedback: str
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class EvaluationRun:
    """Represents the collected results from executing an evaluation set against a target version.

    Attributes:
        run_id: Unique identifier for this execution run.
        version: Version or configuration identifier of the AI feature/prompt tested (e.g., 'baseline-v1', 'candidate-v2').
        results: Collection of EvaluationResult objects for each executed case.
        metadata: Optional run-level metadata (timestamp, model name, provider).
    """
    run_id: str
    version: str
    results: List[EvaluationResult] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def case_count(self) -> int:
        return len(self.results)

    @property
    def average_score(self) -> float:
        if not self.results:
            return 0.0
        return sum(r.score for r in self.results) / len(self.results)

    def get_result(self, case_id: str) -> Optional[EvaluationResult]:
        for res in self.results:
            if res.case_id == case_id:
                return res
        return None


@dataclass
class ComparisonResult:
    """Represents the structured comparison outcome between baseline and candidate runs.

    Attributes:
        verdict: Final gate determination (PASS, FAIL, INCONCLUSIVE).
        summary: Human-readable narrative explanation of the decision.
        baseline_version: Identifier of baseline configuration.
        candidate_version: Identifier of candidate configuration.
        baseline_avg_score: Average score across baseline evaluation run.
        candidate_avg_score: Average score across candidate evaluation run.
        score_diff: Net difference (candidate_avg_score - baseline_avg_score).
        regressions: List of identified case-level regressions or negative anomalies.
        improvements: List of identified case-level improvements.
        metadata: Additional diagnostic details or statistical evidence.
    """
    verdict: Verdict
    summary: str
    baseline_version: str
    candidate_version: str
    baseline_avg_score: float
    candidate_avg_score: float
    score_diff: float
    regressions: List[Dict[str, Any]] = field(default_factory=list)
    improvements: List[Dict[str, Any]] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


# ============================================================================
# Pairwise Evaluation Domain Models
# ============================================================================


@dataclass
class Criterion:
    """Represents an individual evaluation criterion within a rubric.

    Attributes:
        name: Name or title of the criterion.
        description: Detailed guidance on what this criterion evaluates.
        weight: Numeric weight of the criterion, defaults to 1.0.
    """
    name: str
    description: str
    weight: float = 1.0

    def __post_init__(self) -> None:
        if self.weight < 0.0:
            raise ValueError("Criterion weight must be non negative.")


@dataclass
class Rubric:
    """Represents a structured evaluation rubric composed of multiple criteria.

    Attributes:
        name: Name of the rubric.
        criteria: List of Criterion objects.
    """
    name: str
    criteria: List[Criterion] = field(default_factory=list)


class PairwiseWinner(str, Enum):
    """Raw outcome from a pairwise comparison judge referring strictly to presented positions."""
    A = "A"
    B = "B"
    TIE = "TIE"


RawPositionWinner = PairwiseWinner


@dataclass
class PairwiseJudgment:
    """Represents a raw judgment returned by a judge comparing two presented positions.

    Attributes:
        winner: Raw position winner (A, B, or TIE).
        reason: Qualitative rationale explaining the decision.
        confidence: Optional confidence score between 0.0 and 1.0.
        metadata: Optional auxiliary details from the judge.
    """
    winner: PairwiseWinner
    reason: str
    confidence: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class NormalizedWinner(str, Enum):
    """Underlying candidate versus baseline comparison identity after position normalization."""
    BASELINE = "BASELINE"
    CANDIDATE = "CANDIDATE"
    TIE = "TIE"


ComparisonIdentity = NormalizedWinner


@dataclass
class BidirectionalEvaluationResult:
    """Represents the results of evaluating a Baseline versus Candidate pair across both presentation orders.

    Pass 1 (forward): A is Baseline, B is Candidate
    Pass 2 (reverse): A is Candidate, B is Baseline

    Attributes:
        pass1_judgment: Raw judgment from pass 1.
        pass2_judgment: Raw judgment from pass 2.
        pass1_normalized_winner: Normalized comparison identity for pass 1.
        pass2_normalized_winner: Normalized comparison identity for pass 2.
        metadata: Optional dictionary for execution metadata.
    """
    pass1_judgment: PairwiseJudgment
    pass2_judgment: PairwiseJudgment
    pass1_normalized_winner: NormalizedWinner
    pass2_normalized_winner: NormalizedWinner
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def pass1_raw_judgment(self) -> PairwiseJudgment:
        return self.pass1_judgment

    @property
    def pass2_raw_judgment(self) -> PairwiseJudgment:
        return self.pass2_judgment


BidirectionalResult = BidirectionalEvaluationResult


class ConsistencyOutcome(str, Enum):
    """Possible outcomes when analyzing consistency across bidirectional evaluation passes."""
    CONSISTENT_CANDIDATE_WIN = "CONSISTENT_CANDIDATE_WIN"
    CONSISTENT_BASELINE_WIN = "CONSISTENT_BASELINE_WIN"
    CONSISTENT_TIE = "CONSISTENT_TIE"
    POSITION_UNSTABLE = "POSITION_UNSTABLE"


ConsistencyClassification = ConsistencyOutcome


def classify_consistency(
    pass1_winner: NormalizedWinner,
    pass2_winner: NormalizedWinner,
) -> ConsistencyOutcome:
    """Classify consistency between two normalized bidirectional evaluation passes.

    If both passes agree on the normalized winner, the outcome is consistent.
    If the passes conflict, the outcome is classified as POSITION_UNSTABLE.
    """
    if pass1_winner == pass2_winner:
        if pass1_winner == NormalizedWinner.CANDIDATE:
            return ConsistencyOutcome.CONSISTENT_CANDIDATE_WIN
        if pass1_winner == NormalizedWinner.BASELINE:
            return ConsistencyOutcome.CONSISTENT_BASELINE_WIN
        return ConsistencyOutcome.CONSISTENT_TIE
    return ConsistencyOutcome.POSITION_UNSTABLE

