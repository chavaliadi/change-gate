from __future__ import annotations

from typing import Any, Dict, Optional

from ai_change_gate.judge import PairwiseJudge
from ai_change_gate.models import (
    BidirectionalEvaluationResult,
    EvaluationCase,
    NormalizedWinner,
    PairwiseWinner,
    Rubric,
)


class BidirectionalPairwiseRunner:
    """Executes bidirectional pairwise evaluation between baseline and candidate outputs.

    Presentation order:
    Pass 1 (forward):
        output_a is baseline_output
        output_b is candidate_output
    Pass 2 (reverse):
        output_a is candidate_output
        output_b is baseline_output

    Normalizes raw presentation winners (A, B, TIE) to system identities (BASELINE, CANDIDATE, TIE).
    """

    def __init__(self, judge: PairwiseJudge):
        self.judge = judge

    def evaluate(
        self,
        case: EvaluationCase,
        baseline_output: str,
        candidate_output: str,
        rubric: Optional[Rubric] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> BidirectionalEvaluationResult:
        """Run forward and reverse passes, normalize raw winners, and return BidirectionalEvaluationResult."""
        # Pass 1: Forward pass (A is Baseline, B is Candidate)
        pass1_judgment = self.judge.judge(
            case=case,
            output_a=baseline_output,
            output_b=candidate_output,
            rubric=rubric,
        )
        pass1_normalized = self._normalize_pass1(pass1_judgment.winner)

        # Pass 2: Reverse pass (A is Candidate, B is Baseline)
        pass2_judgment = self.judge.judge(
            case=case,
            output_a=candidate_output,
            output_b=baseline_output,
            rubric=rubric,
        )
        pass2_normalized = self._normalize_pass2(pass2_judgment.winner)

        return BidirectionalEvaluationResult(
            pass1_judgment=pass1_judgment,
            pass2_judgment=pass2_judgment,
            pass1_normalized_winner=pass1_normalized,
            pass2_normalized_winner=pass2_normalized,
            metadata=metadata or {},
        )

    @staticmethod
    def _normalize_pass1(winner: PairwiseWinner) -> NormalizedWinner:
        """Normalize raw winner for Pass 1 (A is Baseline, B is Candidate)."""
        if winner == PairwiseWinner.A:
            return NormalizedWinner.BASELINE
        if winner == PairwiseWinner.B:
            return NormalizedWinner.CANDIDATE
        return NormalizedWinner.TIE

    @staticmethod
    def _normalize_pass2(winner: PairwiseWinner) -> NormalizedWinner:
        """Normalize raw winner for Pass 2 (A is Candidate, B is Baseline)."""
        if winner == PairwiseWinner.A:
            return NormalizedWinner.CANDIDATE
        if winner == PairwiseWinner.B:
            return NormalizedWinner.BASELINE
        return NormalizedWinner.TIE
