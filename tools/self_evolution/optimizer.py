from __future__ import annotations

import asyncio
import subprocess
from dataclasses import asdict, dataclass
from pathlib import Path

from .artifacts import candidate_hashes, create_run_directory, stage_candidate_artifacts
from .dataset_builder import load_case_set
from .evaluator import evaluate_target, evaluate_targets
from .execution import ExecutionCaseOutput, ExecutionOptions
from .generation import GenerationContext, ReflectionGenerationEngine
from .judge import JudgeOptions
from .llm_client import EvolutionLlmClient, HermesEvolutionLlmClient
from .materializers import MaterializedCandidate, materializer_for_target
from .review import write_review_package
from .selection import CandidateScorecard, candidate_status, pareto_frontier, select_best_candidate
from .targets import REPO_ROOT, get_target
from .traces import JsonlTraceSink

SUPPORTED_STRATEGIES = ("manual", "reflection", "pareto_reflection")
DEFAULT_DETERMINISTIC_SPLITS = ("dev", "redteam", "regression")
DEFAULT_HOLDOUT_SPLITS = ("holdout",)


@dataclass(frozen=True)
class EvolutionGenerationConfig:
    iterations: int = 1
    population_size: int = 2
    max_generated_candidates: int | None = None
    temperature: float = 0.2
    max_tokens: int = 2200
    timeout_seconds: float | None = None
    provider: str | None = "auto"
    model: str | None = None
    trace_raw: bool = False
    strict_traces: bool = False
    create_review_branch: bool = False


@dataclass(frozen=True)
class StageEvaluation:
    name: str
    split_filter: tuple[str, ...]
    target_names: tuple[str, ...]
    status: str
    reports: list[dict[str, object]]
    baseline_reports: list[dict[str, object]]



def _manual_rationale(
    *,
    target_names: tuple[str, ...],
    source_paths: dict[str, Path],
    reports: list[dict[str, object]],
    stage_history: list[dict[str, object]],
) -> str:
    lines = [
        "# Candidate Rationale",
        "",
        "Manual candidate bundle staged for offline evaluation.",
        "",
    ]
    lines.append("## Targets")
    lines.append("")
    for target_name in target_names:
        source_path = source_paths.get(target_name)
        if source_path is None:
            continue
        report = next((item for item in reports if item.get("target") == target_name), None)
        lines.append(f"- `{target_name}` from `{source_path}`")
        if report is not None:
            lines.append(
                "- Result: "
                f"`{report.get('status')}` / regression `{report.get('regressionStatus')}` / "
                f"score {report.get('score')}/{report.get('maxScore')}"
            )
    lines.append("")
    lines.append("## Promotion Flow")
    lines.append("")
    for stage in stage_history:
        name = str(stage.get("name") or "<unknown>")
        status = str(stage.get("status") or "unknown")
        split_label = ", ".join(str(item) for item in list(stage.get("splitFilter", [])))
        if split_label:
            lines.append(f"- `{name}`: `{status}` ({split_label})")
        else:
            lines.append(f"- `{name}`: `{status}`")
    lines.append("")
    lines.append("## Notes")
    lines.append("")
    lines.append("- Candidate artifacts were copied into this run directory before evaluation.")
    lines.append("- No live runtime state or source files were mutated by the optimizer.")
    return "\n".join(lines)



def _automatic_rationale(
    *,
    selected_candidates: dict[str, MaterializedCandidate],
    candidate_index: list[dict[str, object]],
    stage_history: list[dict[str, object]],
) -> str:
    lines = ["# Candidate Rationale", "", "Automatic reflective search over offline artifacts.", ""]
    lines.append("## Selected Candidates")
    lines.append("")
    for target_name, candidate in selected_candidates.items():
        summary = ", ".join(candidate.edit_summary) or "no summary"
        lines.append(f"- `{target_name}` <= `{candidate.candidate_id}` ({summary})")
        if candidate.rationale:
            lines.append(f"- Why: {candidate.rationale}")
    lines.append("")
    lines.append("## Search Summary")
    lines.append("")
    lines.append(f"- Candidates generated: `{len(candidate_index)}`")
    lines.append(f"- Targets with selections: `{len(selected_candidates)}`")
    lines.append("")
    lines.append("## Promotion Flow")
    lines.append("")
    for stage in stage_history:
        name = str(stage.get("name") or "<unknown>")
        status = str(stage.get("status") or "unknown")
        split_label = ", ".join(str(item) for item in list(stage.get("splitFilter", [])))
        if split_label:
            lines.append(f"- `{name}`: `{status}` ({split_label})")
        else:
            lines.append(f"- `{name}`: `{status}`")
    lines.append("")
    lines.append("## Notes")
    lines.append("")
    lines.append("- Automatic generation stayed inside the target materializers.")
    lines.append("- No runtime or service mutation API was introduced.")
    return "\n".join(lines)



def _normalized_split_filter(
    split_filter: tuple[str, ...] | list[str] | None,
) -> tuple[str, ...]:
    normalized: list[str] = []
    seen: set[str] = set()
    for item in split_filter or ():
        value = str(item).strip().lower()
        if not value or value in seen:
            continue
        seen.add(value)
        normalized.append(value)
    return tuple(normalized)



def _targets_with_cases(
    target_names: tuple[str, ...],
    *,
    split_filter: tuple[str, ...],
) -> tuple[str, ...]:
    applicable: list[str] = []
    for target_name in target_names:
        target = get_target(target_name)
        if load_case_set(target.dataset_paths, split_filter=split_filter):
            applicable.append(target_name)
    return tuple(applicable)



def _evaluate_stage(
    *,
    stage_name: str,
    target_names: tuple[str, ...],
    candidate_paths: dict[str, Path],
    split_filter: tuple[str, ...],
    execution_options: ExecutionOptions | None,
    judge_options: JudgeOptions | None,
    llm_client: EvolutionLlmClient | None,
    trace_sink: JsonlTraceSink | None,
) -> StageEvaluation:
    applicable_targets = _targets_with_cases(target_names, split_filter=split_filter)
    if not applicable_targets:
        return StageEvaluation(
            name=stage_name,
            split_filter=split_filter,
            target_names=(),
            status="skipped",
            reports=[],
            baseline_reports=[],
        )

    baseline_execution_outputs_by_target: dict[str, dict[str, ExecutionCaseOutput]] | None = (
        {} if judge_options is not None and judge_options.enabled else None
    )
    baseline_reports = evaluate_targets(
        applicable_targets,
        split_filter=split_filter,
        execution_options=execution_options,
        judge_options=judge_options,
        llm_client=llm_client,
        trace_sink=trace_sink,
        captured_execution_outputs_by_target=baseline_execution_outputs_by_target,
    )
    baseline_by_target = {
        str(report.get("target") or ""): report for report in baseline_reports
    }
    reports = evaluate_targets(
        applicable_targets,
        candidate_paths_by_target=candidate_paths or None,
        split_filter=split_filter,
        baseline_reports_by_target=baseline_by_target or None,
        execution_options=execution_options,
        judge_options=judge_options,
        llm_client=llm_client,
        trace_sink=trace_sink,
        baseline_execution_outputs_by_target=baseline_execution_outputs_by_target,
    )
    stage_status = (
        "passed"
        if all(report.get("status") == "pass" for report in reports)
        else "failed"
    )
    return StageEvaluation(
        name=stage_name,
        split_filter=split_filter,
        target_names=applicable_targets,
        status=stage_status,
        reports=reports,
        baseline_reports=baseline_reports,
    )



def _candidate_summary(candidate_record: dict[str, object]) -> str:
    return (
        f"{candidate_record['candidateId']} => {candidate_record['status']} / "
        f"det {float(candidate_record.get('deterministicScorePercent') or 0.0):.2%} / "
        f"exec {float(candidate_record.get('executionScorePercent') or 0.0):.2%} / "
        f"judge {float(candidate_record.get('judgeScore') or 0.0):.2f}"
    )



def _scorecard_from_report(
    *,
    candidate_id: str,
    target_name: str,
    candidate_path: Path,
    report: dict[str, object],
    trace_ids: list[str],
    llm_call_count: int,
) -> CandidateScorecard:
    _, staged_hashes = candidate_hashes(
        target_names=[target_name],
        candidate_paths={target_name: candidate_path},
    )
    target = get_target(target_name)
    baseline_size = len(target.baseline_path.read_bytes())
    candidate_size = len(candidate_path.read_bytes())
    scorecard = CandidateScorecard(
        candidate_id=candidate_id,
        target_names=[target_name],
        artifact_hashes=staged_hashes,
        deterministic_score_percent=float(report.get("scorePercent") or 0.0),
        deterministic_failed_cases=int(report.get("failedCases") or 0),
        blocking_failures=int(report.get("blockingFailures") or 0),
        execution_score_percent=float(report.get("executionScorePercent") or 0.0),
        judge_score=float(report.get("judgeScorePercent") or 0.0),
        regression_status=str(report.get("regressionStatus") or "same"),
        length_growth_bytes=candidate_size - baseline_size,
        constraint_findings=[str(item) for item in report.get("constraintFindings", [])],
        cost_signals={"llmCalls": llm_call_count},
        trace_ids=trace_ids,
        status="generated",
    )
    return CandidateScorecard(
        **{**scorecard.__dict__, "status": candidate_status(scorecard)}
    )



def _build_generation_context(
    *,
    target_name: str,
    baseline_report: dict[str, object],
    previous_candidate_summaries: list[str],
) -> GenerationContext:
    target = get_target(target_name)
    deterministic_failures = []
    for case in baseline_report.get("cases", []):
        if bool(case.get("passed")):
            continue
        for finding in case.get("findings", []):
            deterministic_failures.append(str(finding))
    return GenerationContext(
        target_name=target_name,
        baseline_text=target.baseline_path.read_text(),
        mutable_sections=target.mutable_sections,
        immutable_dependencies_summary=[
            str(path.relative_to(REPO_ROOT)) if path.is_relative_to(REPO_ROOT) else str(path)
            for path in target.immutable_dependencies
        ],
        deterministic_failures=deterministic_failures,
        previous_candidate_summaries=previous_candidate_summaries,
        hard_constraints=[
            "No runtime mutation.",
            "No service mutation API.",
            "No writes outside target materializer.",
        ],
    )



def _ensure_llm_client(
    *,
    strategy: str,
    run_dir: Path,
    generation_config: EvolutionGenerationConfig,
    llm_client: EvolutionLlmClient | None,
) -> EvolutionLlmClient:
    if llm_client is not None:
        return llm_client
    if strategy == "manual":
        raise ValueError("Automatic LLM client creation is only valid for non-manual strategies.")
    return HermesEvolutionLlmClient(
        provider=generation_config.provider,
        model=generation_config.model,
        temperature=generation_config.temperature,
        timeout_seconds=generation_config.timeout_seconds,
        cache_root=run_dir / "cache",
    )



def _run_branch_script(script_path: Path) -> None:
    subprocess.run([str(script_path)], check=True)



def _optimize_target(
    *,
    strategy: str,
    target_name: str,
    run_dir: Path,
    llm_client: EvolutionLlmClient,
    generation_config: EvolutionGenerationConfig,
    execution_options: ExecutionOptions,
    judge_options: JudgeOptions,
    trace_sink: JsonlTraceSink,
    split_filter: tuple[str, ...],
) -> tuple[MaterializedCandidate | None, list[dict[str, object]], list[dict[str, object]]]:
    target = get_target(target_name)
    baseline_execution_outputs: dict[str, ExecutionCaseOutput] | None = (
        {} if judge_options.enabled else None
    )
    baseline_report = evaluate_target(
        target_name,
        split_filter=split_filter,
        execution_options=execution_options,
        judge_options=judge_options,
        llm_client=llm_client,
        trace_sink=trace_sink,
        captured_execution_outputs=baseline_execution_outputs,
    )
    max_candidates = generation_config.max_generated_candidates
    total_budget = (
        max_candidates
        if max_candidates is not None
        else generation_config.population_size * generation_config.iterations
    )
    engine = ReflectionGenerationEngine(
        llm_client,
        trace_sink=trace_sink,
        temperature=generation_config.temperature,
        max_tokens=generation_config.max_tokens,
        timeout_seconds=generation_config.timeout_seconds,
    )
    previous_candidate_summaries: list[str] = []
    candidate_records: list[dict[str, object]] = []
    scorecards: list[CandidateScorecard] = []
    selected_candidate: MaterializedCandidate | None = None
    generated_so_far = 0
    for iteration in range(generation_config.iterations):
        if generated_so_far >= total_budget:
            break
        batch_size = (
            1
            if strategy == "reflection"
            else min(generation_config.population_size, total_budget - generated_so_far)
        )
        context = _build_generation_context(
            target_name=target_name,
            baseline_report=baseline_report,
            previous_candidate_summaries=previous_candidate_summaries,
        )
        proposals = asyncio.run(
            engine.generate_candidates(
                target=target,
                context=context,
                max_candidates=batch_size,
                candidate_offset=generated_so_far,
            )
        )
        if not proposals:
            break
        for proposal in proposals:
            generated_so_far += 1
            try:
                materialized = materializer_for_target(target_name).materialize(
                    candidate_id=proposal.candidate_id,
                    proposal=proposal.as_dict(),
                    output_dir=run_dir,
                )
            except Exception as exc:
                trace_sink.warning(
                    "Candidate materialization failed.",
                    {
                        "target": target_name,
                        "candidateId": proposal.candidate_id,
                        "error": str(exc),
                    },
                )
                candidate_records.append(
                    {
                        **proposal.as_dict(),
                        "status": "constraint_failed",
                        "deterministicScorePercent": 0.0,
                        "executionScorePercent": 0.0,
                        "judgeScore": 0.0,
                        "constraintFindings": [str(exc)],
                    }
                )
                continue
            report = evaluate_target(
                target_name,
                candidate_path=materialized.candidate_path,
                split_filter=split_filter,
                baseline_report=baseline_report,
                execution_options=ExecutionOptions(
                    **{**asdict(execution_options), "candidate_id": proposal.candidate_id}
                ),
                judge_options=JudgeOptions(
                    **{**asdict(judge_options), "candidate_id": proposal.candidate_id}
                ),
                llm_client=llm_client,
                trace_sink=trace_sink,
                baseline_execution_outputs=baseline_execution_outputs,
            )
            scorecard = _scorecard_from_report(
                candidate_id=proposal.candidate_id,
                target_name=target_name,
                candidate_path=materialized.candidate_path,
                report=report,
                trace_ids=list(materialized.source_trace_ids),
                llm_call_count=2,
            )
            scorecards.append(scorecard)
            record = {
                **proposal.as_dict(),
                "candidatePath": str(materialized.candidate_path),
                "status": scorecard.status,
                "deterministicScorePercent": scorecard.deterministic_score_percent,
                "executionScorePercent": scorecard.execution_score_percent,
                "judgeScore": scorecard.judge_score,
                "constraintFindings": list(scorecard.constraint_findings),
                "report": report,
            }
            candidate_records.append(record)
            previous_candidate_summaries.append(_candidate_summary(record))
        if strategy == "reflection":
            break

    best_scorecard = select_best_candidate(scorecards)
    if best_scorecard is not None:
        for record in candidate_records:
            if record.get("candidateId") == best_scorecard.candidate_id:
                selected_candidate = MaterializedCandidate(
                    candidate_id=best_scorecard.candidate_id,
                    target_name=target_name,
                    candidate_path=Path(str(record["candidatePath"])),
                    relative_path=target.baseline_relative_path,
                    rationale=str(record.get("rationale") or ""),
                    source_trace_ids=[
                        str(value) for value in record.get("sourceTraceIds", []) if str(value)
                    ],
                    edit_summary=[
                        str(
                            item.get("constantName")
                            or item.get("heading")
                            or item.get("toolName")
                            or ""
                        )
                        for key in (record.get("editSet") or {})
                        for item in (record["editSet"].get(key) or [])
                        if isinstance(item, dict)
                        and str(
                            item.get("constantName")
                            or item.get("heading")
                            or item.get("toolName")
                            or ""
                        )
                    ],
                )
                break
    frontier = [
        {
            "candidateId": card.candidate_id,
            "status": card.status,
            "deterministicScorePercent": card.deterministic_score_percent,
            "executionScorePercent": card.execution_score_percent,
            "judgeScore": card.judge_score,
        }
        for card in pareto_frontier(scorecards)
    ]
    return selected_candidate, candidate_records, frontier



def evolve_candidates(
    *,
    target_names: tuple[str, ...] | list[str],
    strategy: str,
    candidate_paths: dict[str, Path],
    out_dir: Path,
    split_filter: tuple[str, ...] | list[str] | None = None,
    generation_config: EvolutionGenerationConfig | None = None,
    execution_options: ExecutionOptions | None = None,
    judge_options: JudgeOptions | None = None,
    llm_client: EvolutionLlmClient | None = None,
) -> dict[str, object]:
    selected_targets = tuple(target_names)
    if strategy not in SUPPORTED_STRATEGIES:
        known = ", ".join(SUPPORTED_STRATEGIES)
        raise ValueError(f"Unsupported strategy '{strategy}'. Known strategies: {known}")

    generation_config = generation_config or EvolutionGenerationConfig()
    execution_options = execution_options or ExecutionOptions(enabled=False)
    judge_options = judge_options or JudgeOptions(enabled=False)

    run_dir = create_run_directory(out_dir)
    trace_sink = JsonlTraceSink(
        run_dir,
        trace_raw=generation_config.trace_raw,
        strict=generation_config.strict_traces,
    )

    selected_materialized_candidates: dict[str, MaterializedCandidate] = {}
    candidate_index: list[dict[str, object]] = []
    frontier_records: list[dict[str, object]] = []

    if strategy == "manual":
        if not candidate_paths:
            raise ValueError("Manual evolution requires candidate paths for the selected targets.")
        missing_targets = [
            target_name for target_name in selected_targets if target_name not in candidate_paths
        ]
        if missing_targets:
            missing_label = ", ".join(missing_targets)
            raise ValueError(
                "Manual evolution requires candidate paths for every selected target. "
                f"Missing: {missing_label}"
            )
        staged_bundle = stage_candidate_artifacts(
            target_names=selected_targets,
            candidate_paths=candidate_paths,
            run_dir=run_dir,
        )
    else:
        llm_client = _ensure_llm_client(
            strategy=strategy,
            run_dir=run_dir,
            generation_config=generation_config,
            llm_client=llm_client,
        )
        normalized_search_split = (
            _normalized_split_filter(split_filter) or DEFAULT_DETERMINISTIC_SPLITS
        )
        for target_name in selected_targets:
            selected_candidate, candidate_records, frontier = _optimize_target(
                strategy=strategy,
                target_name=target_name,
                run_dir=run_dir,
                llm_client=llm_client,
                generation_config=generation_config,
                execution_options=execution_options,
                judge_options=judge_options,
                trace_sink=trace_sink,
                split_filter=normalized_search_split,
            )
            candidate_index.extend(candidate_records)
            frontier_records.extend(frontier)
            if selected_candidate is not None:
                selected_materialized_candidates[target_name] = selected_candidate
        staged_bundle = type(
            "Bundle",
            (),
            {
                "candidate_paths": {
                    name: candidate.candidate_path
                    for name, candidate in selected_materialized_candidates.items()
                }
            },
        )()
        candidate_paths = {
            name: candidate.candidate_path
            for name, candidate in selected_materialized_candidates.items()
        }

    normalized_split_filter = _normalized_split_filter(split_filter)
    if normalized_split_filter:
        stage_plan = (("custom", normalized_split_filter),)
    else:
        stage_plan = (
            ("deterministic", DEFAULT_DETERMINISTIC_SPLITS),
            ("holdout", DEFAULT_HOLDOUT_SPLITS),
        )

    stage_reports: dict[str, list[dict[str, object]]] = {}
    baseline_stage_reports: dict[str, list[dict[str, object]]] = {}
    stage_history: list[dict[str, object]] = [
        {"name": "generated", "status": "completed", "splitFilter": []}
    ]
    evaluations: list[StageEvaluation] = []

    evaluation_status = "pass"
    promotion_status = "generated"
    missing_targets = [
        target_name
        for target_name in selected_targets
        if target_name not in staged_bundle.candidate_paths
    ]
    if strategy != "manual" and missing_targets:
        evaluation_status = "fail"
        promotion_status = "failed"
        stage_history.append(
            {
                "name": "selection",
                "status": "failed",
                "splitFilter": [],
                "missingTargets": missing_targets,
            }
        )
    else:
        for stage_name, stage_splits in stage_plan:
            if evaluation_status == "fail" and stage_name == "holdout":
                stage_history.append(
                    {
                        "name": stage_name,
                        "status": "skipped",
                        "splitFilter": list(stage_splits),
                    }
                )
                continue
            evaluation = _evaluate_stage(
                stage_name=stage_name,
                target_names=selected_targets,
                candidate_paths=staged_bundle.candidate_paths,
                split_filter=stage_splits,
                execution_options=execution_options,
                judge_options=judge_options,
                llm_client=llm_client,
                trace_sink=trace_sink,
            )
            evaluations.append(evaluation)
            stage_reports[stage_name] = evaluation.reports
            baseline_stage_reports[stage_name] = evaluation.baseline_reports
            stage_history.append(
                {
                    "name": stage_name,
                    "status": evaluation.status,
                    "splitFilter": list(stage_splits),
                    "targets": list(evaluation.target_names),
                }
            )
            if evaluation.status == "failed":
                evaluation_status = "fail"
                promotion_status = "failed"
                break
            if stage_name == "deterministic" or stage_name == "custom":
                promotion_status = "deterministic_passed"
            elif stage_name == "holdout":
                promotion_status = "holdout_passed"

    if evaluation_status == "pass" and promotion_status == "generated":
        promotion_status = "deterministic_passed"
    stage_history.append(
        {
            "name": "human_review",
            "status": "pending" if evaluation_status == "pass" else "blocked",
            "splitFilter": [],
        }
    )

    primary_stage = next(
        (
            evaluation
            for evaluation in evaluations
            if evaluation.name in {"deterministic", "custom"}
        ),
        None,
    )
    primary_reports = primary_stage.reports if primary_stage is not None else []
    primary_baseline_reports = primary_stage.baseline_reports if primary_stage is not None else []

    if strategy == "manual":
        rationale_text = _manual_rationale(
            target_names=selected_targets,
            source_paths=candidate_paths,
            reports=primary_reports,
            stage_history=stage_history,
        )
        selected_materialized_candidates = {
            name: MaterializedCandidate(
                candidate_id=name,
                target_name=name,
                candidate_path=path,
                relative_path=get_target(name).baseline_relative_path,
                rationale="manual candidate",
                source_trace_ids=[],
                edit_summary=[],
            )
            for name, path in staged_bundle.candidate_paths.items()
        }
    else:
        rationale_text = _automatic_rationale(
            selected_candidates=selected_materialized_candidates,
            candidate_index=candidate_index,
            stage_history=stage_history,
        )

    selected_candidate_id = (
        ",".join(
            sorted(
                candidate.candidate_id
                for candidate in selected_materialized_candidates.values()
            )
        )
        or None
    )
    package_paths = write_review_package(
        run_dir=run_dir,
        target_names=selected_targets,
        candidate_paths=staged_bundle.candidate_paths,
        reports=primary_reports,
        baseline_reports=primary_baseline_reports,
        stage_reports=stage_reports,
        baseline_stage_reports=baseline_stage_reports,
        evaluation_status=evaluation_status,
        promotion_status=promotion_status,
        stage_history=stage_history,
        generator_strategy=strategy,
        rationale_text=rationale_text,
        immutable_files_checked=True,
        candidate_index=candidate_index if strategy != "manual" else [],
        frontier=frontier_records if strategy != "manual" else [],
        selected_candidate_id=selected_candidate_id,
        trace_paths=trace_sink.trace_paths(),
    )
    if (
        generation_config.create_review_branch
        and package_paths.get("apply_candidate_branch") is not None
    ):
        _run_branch_script(package_paths["apply_candidate_branch"])
    return {
        "runDir": str(run_dir),
        "status": evaluation_status,
        "promotionStatus": promotion_status,
        "reports": primary_reports,
        "baselineReports": primary_baseline_reports,
        "stageReports": stage_reports,
        "baselineStageReports": baseline_stage_reports,
        "stageHistory": stage_history,
        "paths": {key: str(value) for key, value in package_paths.items()},
    }
