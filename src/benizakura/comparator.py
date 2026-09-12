from __future__ import annotations

from typing import Protocol

from benizakura.models import ComparisonResult, EvaluationRun, Verdict


# PROVISIONAL:
# This comparator intentionally uses placeholder logic.
# The final evaluation methodology will be determined after
# literature review and benchmark design.


class Comparator(Protocol):
    """Protocol for comparing baseline and candidate evaluation runs."""

    def compare(self, baseline: EvaluationRun, candidate: EvaluationRun) -> ComparisonResult:
        ...


class SimpleComparator:
    """Provisional comparator applying basic heuristic thresholds to baseline vs candidate runs.

    Rules (Provisional):
    - FAIL: Triggered if any single test case suffers a critical regression
      (e.g., case score drops by >= 2.0 points or candidate score < 4.0 when baseline was >= 7.0),
      or if overall candidate average score drops significantly below baseline.
    - PASS: Triggered if candidate demonstrates clear net improvement (average score diff >= improvement_threshold)
      with zero critical regressions.
    - INCONCLUSIVE: Triggered if the score difference is negligible (within noise_threshold) or evidence
      is balanced/mixed without meeting clear pass/fail criteria.
    """

    def __init__(
        self,
        critical_regression_drop: float = 2.0,
        critical_failure_floor: float = 4.0,
        baseline_competence_threshold: float = 7.0,
        improvement_threshold: float = 0.5,
        noise_threshold: float = 0.2,
    ):
        self.critical_regression_drop = critical_regression_drop
        self.critical_failure_floor = critical_failure_floor
        self.baseline_competence_threshold = baseline_competence_threshold
        self.improvement_threshold = improvement_threshold
        self.noise_threshold = noise_threshold

    def compare(self, baseline: EvaluationRun, candidate: EvaluationRun) -> ComparisonResult:
        if baseline.case_count == 0 or candidate.case_count == 0:
            return ComparisonResult(
                verdict=Verdict.INCONCLUSIVE,
                summary="Insufficient evaluation cases to perform comparison.",
                baseline_version=baseline.version,
                candidate_version=candidate.version,
                baseline_avg_score=baseline.average_score,
                candidate_avg_score=candidate.average_score,
                score_diff=0.0,
            )

        regressions = []
        improvements = []

        baseline_map = {r.case_id: r for r in baseline.results}
        candidate_map = {r.case_id: r for r in candidate.results}
        shared_case_ids = [cid for cid in baseline_map if cid in candidate_map]

        for case_id in shared_case_ids:
            b_res = baseline_map[case_id]
            c_res = candidate_map[case_id]
            delta = c_res.score - b_res.score

            is_critical = (
                (delta <= -self.critical_regression_drop)
                or (
                    b_res.score >= self.baseline_competence_threshold
                    and c_res.score < self.critical_failure_floor
                )
            )

            if is_critical:
                regressions.append({
                    "case_id": case_id,
                    "baseline_score": b_res.score,
                    "candidate_score": c_res.score,
                    "diff": round(delta, 2),
                    "reason": "Score dropped past critical regression threshold",
                })
            elif delta <= -self.noise_threshold:
                regressions.append({
                    "case_id": case_id,
                    "baseline_score": b_res.score,
                    "candidate_score": c_res.score,
                    "diff": round(delta, 2),
                    "reason": "Minor score regression",
                })
            elif delta >= self.improvement_threshold:
                improvements.append({
                    "case_id": case_id,
                    "baseline_score": b_res.score,
                    "candidate_score": c_res.score,
                    "diff": round(delta, 2),
                    "reason": "Clear score improvement",
                })

        b_avg = baseline.average_score
        c_avg = candidate.average_score
        diff = round(c_avg - b_avg, 2)

        has_critical_regression = any(
            r["reason"] == "Score dropped past critical regression threshold"
            for r in regressions
        )

        # Decision tree
        if has_critical_regression:
            verdict = Verdict.FAIL
            summary = (
                f"Critical regression detected in {len(regressions)} case(s). "
                f"Candidate average score {c_avg:.2f} vs baseline {b_avg:.2f} (diff: {diff:+.2f})."
            )
        elif diff < -self.noise_threshold:
            verdict = Verdict.FAIL
            summary = (
                f"Candidate average score degraded to {c_avg:.2f} compared to baseline {b_avg:.2f} "
                f"(diff: {diff:+.2f})."
            )
        elif diff >= self.improvement_threshold and len(regressions) == 0:
            verdict = Verdict.PASS
            summary = (
                f"Candidate shows clear improvement (avg {c_avg:.2f} vs baseline {b_avg:.2f}, "
                f"diff: {diff:+.2f}) with zero detected regressions."
            )
        else:
            verdict = Verdict.INCONCLUSIVE
            summary = (
                f"Difference between candidate ({c_avg:.2f}) and baseline ({b_avg:.2f}) "
                f"is within threshold (diff: {diff:+.2f}); insufficient evidence for definitive pass/fail."
            )

        return ComparisonResult(
            verdict=verdict,
            summary=summary,
            baseline_version=baseline.version,
            candidate_version=candidate.version,
            baseline_avg_score=round(b_avg, 2),
            candidate_avg_score=round(c_avg, 2),
            score_diff=diff,
            regressions=regressions,
            improvements=improvements,
        )
