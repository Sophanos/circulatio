from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class CandidateScorecard:
    candidate_id: str
    target_names: list[str]
    artifact_hashes: dict[str, str]
    deterministic_score_percent: float
    deterministic_failed_cases: int
    blocking_failures: int
    execution_score_percent: float
    judge_score: float
    regression_status: str
    length_growth_bytes: int
    constraint_findings: list[str] = field(default_factory=list)
    guardrail_phrase_changes: list[dict[str, object]] = field(default_factory=list)
    cost_signals: dict[str, object] = field(default_factory=dict)
    trace_ids: list[str] = field(default_factory=list)
    status: str = "generated"

    @property
    def eligible(self) -> bool:
        return (
            self.blocking_failures == 0
            and self.deterministic_failed_cases == 0
            and self.regression_status != "regressed"
            and not self.constraint_findings
        )



def candidate_status(scorecard: CandidateScorecard) -> str:
    if scorecard.constraint_findings:
        return "constraint_failed"
    if scorecard.blocking_failures > 0 or scorecard.deterministic_failed_cases > 0:
        return "deterministic_failed"
    if scorecard.regression_status == "regressed":
        return "holdout_failed"
    return "eligible"



def dominates(left: CandidateScorecard, right: CandidateScorecard) -> bool:
    if left.eligible and not right.eligible:
        return True
    if not left.eligible:
        return False
    left_cost = _cost(left)
    right_cost = _cost(right)
    no_worse = (
        left.deterministic_score_percent >= right.deterministic_score_percent
        and left.execution_score_percent >= right.execution_score_percent
        and left.judge_score >= right.judge_score
        and left.blocking_failures <= right.blocking_failures
        and left.length_growth_bytes <= right.length_growth_bytes
        and left_cost <= right_cost
    )
    strictly_better = (
        left.deterministic_score_percent > right.deterministic_score_percent
        or left.execution_score_percent > right.execution_score_percent
        or left.judge_score > right.judge_score
        or left.blocking_failures < right.blocking_failures
        or left.length_growth_bytes < right.length_growth_bytes
        or left_cost < right_cost
    )
    return no_worse and strictly_better



def pareto_frontier(scorecards: list[CandidateScorecard]) -> list[CandidateScorecard]:
    eligible = [card for card in scorecards if card.eligible]
    frontier: list[CandidateScorecard] = []
    for candidate in eligible:
        if any(
            dominates(other, candidate)
            for other in eligible
            if other.candidate_id != candidate.candidate_id
        ):
            continue
        frontier.append(candidate)
    return sorted(frontier, key=_selection_sort_key)



def select_best_candidate(scorecards: list[CandidateScorecard]) -> CandidateScorecard | None:
    frontier = pareto_frontier(scorecards)
    if frontier:
        return frontier[0]
    eligible = [card for card in scorecards if card.eligible]
    if eligible:
        return sorted(eligible, key=_selection_sort_key)[0]
    return None



def _selection_sort_key(scorecard: CandidateScorecard) -> tuple[float, float, float, int, int, str]:
    return (
        -scorecard.deterministic_score_percent,
        -scorecard.execution_score_percent,
        -scorecard.judge_score,
        scorecard.length_growth_bytes,
        _cost(scorecard),
        scorecard.candidate_id,
    )



def _cost(scorecard: CandidateScorecard) -> int:
    token_cost = int(scorecard.cost_signals.get("llmCalls", 0))
    return token_cost + len(scorecard.constraint_findings) + len(scorecard.guardrail_phrase_changes)
