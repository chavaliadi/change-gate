from __future__ import annotations

from typing import Any, Callable, Dict, Optional, Protocol, Sequence
import uuid

from ai_change_gate.models import EvaluationCase, EvaluationResult, EvaluationRun
from ai_change_gate.pairwise_runner import BidirectionalPairwiseRunner



class Evaluator(Protocol):
    """Abstract interface/protocol for executing an evaluation case against an AI system."""

    def evaluate(self, case: EvaluationCase) -> EvaluationResult:
        """Evaluate a single test case and return an EvaluationResult."""
        ...


class MockEvaluator:
    """Deterministic mock evaluator for local testing and CI without external API calls.

    NOTE: Temporary infrastructure. This mock allows testing the domain pipeline,
    runner, and comparator without requiring LLM provider API keys or network calls.
    """

    def __init__(
        self,
        default_score: float = 7.0,
        default_feedback: str = "Mock evaluation feedback.",
        case_overrides: Optional[Dict[str, Dict[str, Any]]] = None,
        custom_grading_fn: Optional[Callable[[EvaluationCase], EvaluationResult]] = None,
    ):
        self.default_score = default_score
        self.default_feedback = default_feedback
        self.case_overrides = case_overrides or {}
        self.custom_grading_fn = custom_grading_fn

    def evaluate(self, case: EvaluationCase) -> EvaluationResult:
        if self.custom_grading_fn:
            return self.custom_grading_fn(case)

        if case.id in self.case_overrides:
            override = self.case_overrides[case.id]
            return EvaluationResult(
                case_id=case.id,
                score=override.get("score", self.default_score),
                feedback=override.get("feedback", self.default_feedback),
                metadata=override.get("metadata", {}),
            )

        return EvaluationResult(
            case_id=case.id,
            score=self.default_score,
            feedback=self.default_feedback,
        )


class EvaluationRunner:
    """Executes a sequence of evaluation cases against an Evaluator to produce an EvaluationRun."""

    def __init__(self, evaluator: Evaluator):
        self.evaluator = evaluator

    def run(
        self,
        cases: Sequence[EvaluationCase],
        version: str,
        run_id: Optional[str] = None,
    ) -> EvaluationRun:
        run_id = run_id or f"run_{uuid.uuid4().hex[:8]}"
        results = [self.evaluator.evaluate(case) for case in cases]
        return EvaluationRun(
            run_id=run_id,
            version=version,
            results=results,
        )
