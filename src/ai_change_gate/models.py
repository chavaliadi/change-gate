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
