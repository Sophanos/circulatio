from __future__ import annotations

import asyncio
import importlib.util
from collections.abc import Mapping
from dataclasses import asdict, dataclass
from pathlib import Path
from types import ModuleType

from circulatio.llm import prompt_builder
from circulatio_hermes_plugin import schemas as plugin_schemas

from .artifacts import load_candidate_bundle_paths
from .constraints import (
    validate_candidate_bundle_paths,
    validate_candidate_path,
    validate_dataset_coverage,
    validate_prompt_fragments_module,
    validate_skill_size,
    validate_tool_descriptions,
)
from .dataset_builder import load_case_set
from .execution import ExecutionCaseOutput, ExecutionOptions, run_execution_cases
from .fitness import (
    CaseResult,
    evaluate_prompt_case,
    evaluate_skill_case,
    evaluate_tool_description_case,
)
from .judge import JudgeOptions, run_judge_cases
from .llm_client import EvolutionLlmClient
from .targets import EvolutionTarget, get_target
from .traces import JsonlTraceSink


@dataclass
class EvaluationReport:
    target: str
    kind: str
    description: str
    baselinePath: str
    candidatePath: str | None
    datasetPaths: list[str]
    status: str
    regressionStatus: str
    judgeRegressionStatus: str
    blockingFailures: int
    caseCount: int
    failedCases: int
    score: int
    maxScore: int
    scorePercent: float
    executionScore: int
    executionMaxScore: int
    executionScorePercent: float
    judgeScore: int
    judgeMaxScore: int
    judgeScorePercent: float
    judgeCaseCount: int
    judgeConcernCount: int
    criticalJudgeConcernCount: int
    constraintFindings: list[str]
    cases: list[dict[str, object]]

    def as_dict(self) -> dict[str, object]:
        return asdict(self)



def _object_mapping(value: object) -> dict[str, object]:
    if not isinstance(value, Mapping):
        return {}
    return {str(key): item for key, item in value.items()}



def _int_value(value: object) -> int:
    return value if isinstance(value, int) else 0



def _float_value(value: object) -> float:
    return value if isinstance(value, float) else float(value or 0.0)



def _load_python_module(path: Path, *, module_name: str) -> ModuleType:
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise ValueError(f"Unable to load Python module from {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module



def _prompt_messages(
    prompt_kind: str,
    input_data: dict[str, object],
    *,
    fragments: ModuleType | None = None,
) -> list[dict[str, str]]:
    if prompt_kind == "analysis_packet":
        return prompt_builder.build_analysis_packet_messages(input_data, fragments=fragments)
    if prompt_kind == "interpretation":
        return prompt_builder.build_interpretation_messages(input_data, fragments=fragments)
    if prompt_kind == "living_myth_review":
        return prompt_builder.build_living_myth_review_messages(input_data, fragments=fragments)
    if prompt_kind == "method_state_routing":
        return prompt_builder.build_method_state_routing_messages(input_data, fragments=fragments)
    if prompt_kind == "practice":
        return prompt_builder.build_practice_messages(input_data, fragments=fragments)
    if prompt_kind == "rhythmic_brief":
        return prompt_builder.build_rhythmic_brief_messages(input_data, fragments=fragments)
    if prompt_kind == "threshold_review":
        return prompt_builder.build_threshold_review_messages(input_data, fragments=fragments)
    if prompt_kind == "weekly_review":
        return prompt_builder.build_weekly_review_messages(input_data, fragments=fragments)
    known = ", ".join(
        [
            "analysis_packet",
            "interpretation",
            "living_myth_review",
            "method_state_routing",
            "practice",
            "rhythmic_brief",
            "threshold_review",
            "weekly_review",
        ]
    )
    raise ValueError(f"Unknown promptKind '{prompt_kind}'. Known kinds: {known}")



def _regression_status(
    *,
    baseline_report: dict[str, object] | None,
    score: int,
    failed_cases: int,
    blocking_failures: int,
) -> str:
    if baseline_report is None:
        return "same"
    baseline_score = _int_value(baseline_report.get("score"))
    baseline_failed = _int_value(baseline_report.get("failedCases"))
    baseline_blocking = _int_value(baseline_report.get("blockingFailures"))
    if (
        score < baseline_score
        or failed_cases > baseline_failed
        or blocking_failures > baseline_blocking
    ):
        return "regressed"
    if (
        score > baseline_score
        or failed_cases < baseline_failed
        or blocking_failures < baseline_blocking
    ):
        return "improved"
    return "same"



def _judge_regression_status(
    *,
    baseline_report: dict[str, object] | None,
    judge_score_percent: float,
) -> str:
    if baseline_report is None:
        return "same"
    baseline_score_percent = _float_value(baseline_report.get("judgeScorePercent"))
    if judge_score_percent < baseline_score_percent:
        return "regressed"
    if judge_score_percent > baseline_score_percent:
        return "improved"
    return "same"



def _evaluate_deterministic_cases(
    *,
    target: EvolutionTarget,
    candidate_path: Path | None,
    cases: list[dict[str, object]],
) -> tuple[list[str], list[CaseResult]]:
    constraint_findings: list[str] = []
    case_results: list[CaseResult] = []

    if target.kind == "prompt_fragments":
        fragments_module = (
            _load_python_module(candidate_path, module_name="circulatio_candidate_prompt_fragments")
            if candidate_path is not None
            else prompt_builder.prompt_fragments
        )
        constraint_findings.extend(validate_prompt_fragments_module(fragments_module))
        for case in cases:
            prompt_kind = str(case.get("promptKind") or "")
            input_data = _object_mapping(case.get("input"))
            messages = _prompt_messages(prompt_kind, input_data, fragments=fragments_module)
            case_results.append(evaluate_prompt_case(case, messages))
    elif target.kind == "skill":
        active_path = candidate_path or target.baseline_path
        skill_text = active_path.read_text()
        constraint_findings.extend(validate_skill_size(skill_text))
        for case in cases:
            case_results.append(evaluate_skill_case(case, skill_text))
    elif target.kind == "tool_descriptions":
        tool_module = (
            _load_python_module(candidate_path, module_name="circulatio_candidate_schemas")
            if candidate_path is not None
            else plugin_schemas
        )
        tool_schemas = list(getattr(tool_module, "TOOL_SCHEMAS", []))
        constraint_findings.extend(
            validate_tool_descriptions(tool_schemas, profile=target.constraint_profile)
        )
        for case in cases:
            case_results.append(evaluate_tool_description_case(case, tool_schemas))
    else:
        raise ValueError(f"Unsupported target kind: {target.kind}")

    return constraint_findings, case_results



def evaluate_targets(
    target_names: tuple[str, ...] | list[str],
    *,
    candidate_paths_by_target: Mapping[str, Path] | None = None,
    dataset_paths_by_target: Mapping[str, tuple[Path, ...] | list[Path]] | None = None,
    split_filter: tuple[str, ...] | list[str] | None = None,
    baseline_reports_by_target: Mapping[str, dict[str, object]] | None = None,
    execution_options: ExecutionOptions | None = None,
    judge_options: JudgeOptions | None = None,
    llm_client: EvolutionLlmClient | None = None,
    trace_sink: JsonlTraceSink | None = None,
    baseline_execution_outputs_by_target: Mapping[str, dict[str, ExecutionCaseOutput]] | None = None,
    captured_execution_outputs_by_target: dict[str, dict[str, ExecutionCaseOutput]] | None = None,
) -> list[dict[str, object]]:
    reports: list[dict[str, object]] = []
    for target_name in target_names:
        target = get_target(target_name)
        candidate_path = None
        if candidate_paths_by_target is not None:
            candidate_path = candidate_paths_by_target.get(target_name)
        active_dataset_paths = tuple(
            (dataset_paths_by_target or {}).get(target_name, target.dataset_paths)
        )
        cases = load_case_set(active_dataset_paths, split_filter=split_filter)
        deterministic_cases = [
            case
            for case in cases
            if str(case.get("gateType")) not in {"execution", "judge"}
        ]
        execution_cases = [
            case for case in cases if str(case.get("gateType")) == "execution"
        ]
        constraint_findings = []
        constraint_findings.extend(validate_candidate_path(candidate_path))
        constraint_findings.extend(validate_dataset_coverage(cases, active_dataset_paths))

        deterministic_results: list[CaseResult] = []
        execution_results: list[CaseResult] = []
        judge_results: list[CaseResult] = []
        execution_outputs: dict[str, ExecutionCaseOutput] = {}
        if not any("Candidate path" in finding for finding in constraint_findings):
            extra_constraints, deterministic_results = _evaluate_deterministic_cases(
                target=target,
                candidate_path=candidate_path,
                cases=deterministic_cases,
            )
            constraint_findings.extend(extra_constraints)
            if execution_options is not None and execution_options.enabled and execution_cases:
                if llm_client is None:
                    raise ValueError("Execution evaluation requires an EvolutionLlmClient.")
                execution_results, execution_outputs = asyncio.run(
                    run_execution_cases(
                        target=target,
                        candidate_path=candidate_path,
                        cases=execution_cases,
                        llm_client=llm_client,
                        options=execution_options,
                        trace_sink=trace_sink,
                    )
                )
                if captured_execution_outputs_by_target is not None and execution_outputs:
                    captured_execution_outputs_by_target[target_name] = dict(execution_outputs)
            if judge_options is not None and judge_options.enabled and execution_outputs:
                if llm_client is None:
                    raise ValueError("Judge evaluation requires an EvolutionLlmClient.")
                baseline_execution_outputs = (
                    baseline_execution_outputs_by_target or {}
                ).get(target_name)
                judge_results, _ = asyncio.run(
                    run_judge_cases(
                        target=target,
                        execution_outputs=execution_outputs,
                        llm_client=llm_client,
                        options=judge_options,
                        trace_sink=trace_sink,
                        baseline_outputs=baseline_execution_outputs,
                    )
                )

        hard_results = [*deterministic_results, *execution_results]
        failed_cases = sum(1 for result in hard_results if not result.passed)
        blocking_failures = sum(
            1 for result in hard_results if not result.passed and result.severity == "blocking"
        )
        total_score = sum(result.score for result in hard_results)
        total_max_score = sum(result.max_score for result in hard_results)
        execution_score = sum(result.score for result in execution_results)
        execution_max_score = sum(result.max_score for result in execution_results)
        judge_score = sum(result.score for result in judge_results)
        judge_max_score = sum(result.max_score for result in judge_results)
        judge_concern_count = sum(1 for result in judge_results if result.findings)
        critical_judge_concern_count = sum(
            len(list(result.signals.get("criticalConcerns", []))) for result in judge_results
        )
        regression_status = _regression_status(
            baseline_report=(baseline_reports_by_target or {}).get(target_name),
            score=total_score,
            failed_cases=failed_cases,
            blocking_failures=blocking_failures,
        )
        judge_score_percent = (judge_score / judge_max_score) if judge_max_score else 0.0
        status = "pass" if failed_cases == 0 and not constraint_findings else "fail"
        report = EvaluationReport(
            target=target.name,
            kind=target.kind,
            description=target.description,
            baselinePath=str(target.baseline_path),
            candidatePath=str(candidate_path) if candidate_path is not None else None,
            datasetPaths=[str(path) for path in active_dataset_paths],
            status=status,
            regressionStatus=regression_status,
            judgeRegressionStatus=_judge_regression_status(
                baseline_report=(baseline_reports_by_target or {}).get(target_name),
                judge_score_percent=judge_score_percent,
            ),
            blockingFailures=blocking_failures,
            caseCount=len(hard_results),
            failedCases=failed_cases,
            score=total_score,
            maxScore=total_max_score,
            scorePercent=(total_score / total_max_score) if total_max_score else 0.0,
            executionScore=execution_score,
            executionMaxScore=execution_max_score,
            executionScorePercent=(
                (execution_score / execution_max_score) if execution_max_score else 0.0
            ),
            judgeScore=judge_score,
            judgeMaxScore=judge_max_score,
            judgeScorePercent=judge_score_percent,
            judgeCaseCount=len(judge_results),
            judgeConcernCount=judge_concern_count,
            criticalJudgeConcernCount=critical_judge_concern_count,
            constraintFindings=constraint_findings,
            cases=[result.as_dict() for result in [*hard_results, *judge_results]],
        )
        reports.append(report.as_dict())
    return reports



def evaluate_candidate_bundle(
    target_names: tuple[str, ...] | list[str],
    *,
    candidate_dir: Path,
    dataset_paths_by_target: Mapping[str, tuple[Path, ...] | list[Path]] | None = None,
    split_filter: tuple[str, ...] | list[str] | None = None,
    baseline_reports_by_target: Mapping[str, dict[str, object]] | None = None,
    execution_options: ExecutionOptions | None = None,
    judge_options: JudgeOptions | None = None,
    llm_client: EvolutionLlmClient | None = None,
    trace_sink: JsonlTraceSink | None = None,
    baseline_execution_outputs_by_target: Mapping[str, dict[str, ExecutionCaseOutput]] | None = None,
    captured_execution_outputs_by_target: dict[str, dict[str, ExecutionCaseOutput]] | None = None,
) -> list[dict[str, object]]:
    bundle = load_candidate_bundle_paths(candidate_dir, target_names=target_names)
    reports = evaluate_targets(
        target_names,
        candidate_paths_by_target=bundle.candidate_paths,
        dataset_paths_by_target=dataset_paths_by_target,
        split_filter=split_filter,
        baseline_reports_by_target=baseline_reports_by_target,
        execution_options=execution_options,
        judge_options=judge_options,
        llm_client=llm_client,
        trace_sink=trace_sink,
        baseline_execution_outputs_by_target=baseline_execution_outputs_by_target,
        captured_execution_outputs_by_target=captured_execution_outputs_by_target,
    )
    bundle_findings = validate_candidate_bundle_paths(
        target_names=target_names,
        candidate_relative_paths=bundle.relative_paths,
        extra_relative_paths=bundle.extra_relative_paths,
    )
    if bundle_findings:
        for report in reports:
            report["constraintFindings"] = [
                *bundle_findings,
                *list(report.get("constraintFindings", [])),
            ]
            report["status"] = "fail"
            report["regressionStatus"] = "regressed"
    return reports



def evaluate_target(
    target_name: str,
    *,
    candidate_path: Path | None = None,
    dataset_paths: list[Path] | tuple[Path, ...] | None = None,
    split_filter: tuple[str, ...] | list[str] | None = None,
    baseline_report: dict[str, object] | None = None,
    execution_options: ExecutionOptions | None = None,
    judge_options: JudgeOptions | None = None,
    llm_client: EvolutionLlmClient | None = None,
    trace_sink: JsonlTraceSink | None = None,
    baseline_execution_outputs: dict[str, ExecutionCaseOutput] | None = None,
    captured_execution_outputs: dict[str, ExecutionCaseOutput] | None = None,
) -> dict[str, object]:
    candidate_paths_by_target = (
        {target_name: candidate_path} if candidate_path is not None else None
    )
    dataset_paths_by_target = (
        {target_name: tuple(dataset_paths)} if dataset_paths is not None else None
    )
    baseline_reports_by_target = (
        {target_name: baseline_report} if baseline_report is not None else None
    )
    captured_by_target = {} if captured_execution_outputs is not None else None
    reports = evaluate_targets(
        [target_name],
        candidate_paths_by_target=candidate_paths_by_target,
        dataset_paths_by_target=dataset_paths_by_target,
        split_filter=split_filter,
        baseline_reports_by_target=baseline_reports_by_target,
        execution_options=execution_options,
        judge_options=judge_options,
        llm_client=llm_client,
        trace_sink=trace_sink,
        baseline_execution_outputs_by_target=(
            {target_name: baseline_execution_outputs}
            if baseline_execution_outputs is not None
            else None
        ),
        captured_execution_outputs_by_target=captured_by_target,
    )
    if captured_execution_outputs is not None:
        captured_execution_outputs.clear()
        captured_execution_outputs.update((captured_by_target or {}).get(target_name, {}))
    return reports[0]
