#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))


def parse_args(default_target_order: tuple[str, ...]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Evaluate Circulatio prompt fragments, Hermes skill routing, and tool descriptions "
            "against the repo-local method-eval datasets."
        )
    )
    parser.add_argument(
        "--target",
        choices=["all", *default_target_order],
        default="all",
        help="Artifact target to evaluate.",
    )
    parser.add_argument(
        "--prompt-fragments",
        type=Path,
        help="Candidate prompt_fragments.py override for prompt target evaluation.",
    )
    parser.add_argument(
        "--skill-file",
        type=Path,
        help="Candidate SKILL.md override for skill target evaluation.",
    )
    parser.add_argument(
        "--schemas-file",
        type=Path,
        help="Candidate schemas.py override for tool-description evaluation.",
    )
    parser.add_argument(
        "--candidate-dir",
        type=Path,
        help=(
            "Evaluate a candidate bundle directory, optionally containing a "
            "candidates/ subdirectory."
        ),
    )
    parser.add_argument(
        "--dataset",
        action="append",
        type=Path,
        default=[],
        help="Optional replacement dataset path(s) when evaluating a single target.",
    )
    parser.add_argument(
        "--split",
        action="append",
        choices=["train", "dev", "holdout", "redteam", "regression"],
        help="Optional dataset split filter. May be passed multiple times.",
    )
    parser.add_argument(
        "--execution",
        action=argparse.BooleanOptionalAction,
        default=False,
        help="Enable execution-backed evaluation.",
    )
    parser.add_argument(
        "--judge",
        action=argparse.BooleanOptionalAction,
        default=False,
        help="Enable advisory judge scoring. Implies --execution.",
    )
    parser.add_argument(
        "--judge-mode",
        choices=["absolute", "pairwise"],
        default=None,
        help="Optional judge scoring mode override when advisory judging is enabled.",
    )
    parser.add_argument(
        "--trace-jsonl",
        type=Path,
        help="Optional path to write sanitized execution/judge traces.",
    )
    parser.add_argument(
        "--provider",
        help="Optional Hermes auxiliary-client provider override for execution/judge calls.",
    )
    parser.add_argument(
        "--model",
        help="Optional model override for execution/judge calls.",
    )
    parser.add_argument(
        "--timeout-seconds",
        type=float,
        help="Optional timeout override for execution/judge calls.",
    )
    parser.add_argument(
        "--report-json",
        type=Path,
        help="Write the full evaluation report to a JSON file.",
    )
    parser.add_argument(
        "--report-md",
        type=Path,
        help="Write a Markdown summary report.",
    )
    parser.add_argument(
        "--baseline-report",
        type=Path,
        help="Write the baseline comparison report to JSON when baseline comparison is enabled.",
    )
    parser.add_argument(
        "--fail-on-regression",
        action="store_true",
        help=(
            "Exit non-zero when the candidate regresses against the baseline "
            "report computed in-process."
        ),
    )
    parser.add_argument(
        "--min-score",
        type=float,
        help=(
            "Optional minimum per-target hard scorePercent threshold "
            "expressed as a 0..1 fraction."
        ),
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Exit non-zero when any target fails.",
    )
    return parser.parse_args()


def _candidate_path(target_name: str, args: argparse.Namespace) -> Path | None:
    if target_name == "prompt_fragments":
        return args.prompt_fragments
    if target_name == "skill":
        return args.skill_file
    if target_name == "tool_descriptions":
        return args.schemas_file
    return None


def _candidate_paths(target_names: list[str], args: argparse.Namespace) -> dict[str, Path]:
    paths: dict[str, Path] = {}
    for target_name in target_names:
        candidate_path = _candidate_path(target_name, args)
        if candidate_path is not None:
            paths[target_name] = candidate_path
    return paths


def _print_report(report: dict[str, object]) -> None:
    case_count = int(report["caseCount"])
    failed_cases = int(report["failedCases"])
    score = int(report["score"])
    max_score = int(report["maxScore"])
    parts = [
        f"[{report['status']}] {report['target']}: ",
        f"{case_count - failed_cases}/{case_count} hard cases, {score}/{max_score} hard points",
        f"blocking={report['blockingFailures']}",
        f"regression={report['regressionStatus']}",
    ]
    if int(report.get("executionMaxScore") or 0):
        parts.append(
            f"execution={report.get('executionScore')}/{report.get('executionMaxScore')}"
        )
    if int(report.get("judgeMaxScore") or 0):
        parts.append(f"judge={report.get('judgeScore')}/{report.get('judgeMaxScore')}")
    print(", ".join(parts))
    for finding in list(report.get("constraintFindings", [])):
        print(f"  constraint: {finding}")
    for case in list(report["cases"]):
        label = "ok" if case["passed"] else "fail"
        kind = str(case.get("result_kind") or "deterministic")
        print(
            f"  - [{label}] {case['case_id']} ({case['score']}/{case['max_score']}) "
            f"[{case['dataset']}] {case['split']} / {case['severity']} / "
            f"{case['gate_type']} / {kind}"
        )
        for finding in list(case.get("findings", [])):
            print(f"    {finding}")


def main() -> int:
    from tools.self_evolution import (
        DEFAULT_TARGET_ORDER,
        ExecutionOptions,
        HermesEvolutionLlmClient,
        JudgeOptions,
        evaluate_candidate_bundle,
        evaluate_targets,
    )
    from tools.self_evolution.review import render_report_markdown
    from tools.self_evolution.traces import JsonlTraceSink

    args = parse_args(DEFAULT_TARGET_ORDER)
    target_names = list(DEFAULT_TARGET_ORDER) if args.target == "all" else [args.target]
    if args.dataset and len(target_names) != 1:
        raise SystemExit("--dataset can only be used when evaluating a single target.")
    if args.candidate_dir and any(
        value is not None for value in (args.prompt_fragments, args.skill_file, args.schemas_file)
    ):
        raise SystemExit(
            "Use either --candidate-dir or individual candidate override flags, not both."
        )

    execution_enabled = bool(args.execution or args.judge)
    judge_enabled = bool(args.judge)
    dataset_paths_by_target = {target_names[0]: tuple(args.dataset)} if args.dataset else None
    candidate_paths = _candidate_paths(target_names, args)
    compare_to_baseline = bool(
        args.candidate_dir or candidate_paths or args.fail_on_regression or args.baseline_report
    )

    with tempfile.TemporaryDirectory(prefix="circulatio-eval-") as tmp_dir:
        temp_root = Path(tmp_dir)
        trace_sink = (
            JsonlTraceSink(temp_root / "traces")
            if execution_enabled and args.trace_jsonl is not None
            else None
        )
        llm_client = (
            HermesEvolutionLlmClient(
                provider=args.provider,
                model=args.model,
                timeout_seconds=args.timeout_seconds,
                cache_root=temp_root / "cache",
            )
            if execution_enabled
            else None
        )
        execution_options = ExecutionOptions(
            enabled=execution_enabled,
            timeout_seconds=args.timeout_seconds,
            stage_name="evaluate",
        )
        judge_options = JudgeOptions(
            enabled=judge_enabled,
            timeout_seconds=args.timeout_seconds,
            mode=args.judge_mode,
        )
        baseline_execution_outputs_by_target = {} if judge_enabled else None
        baseline_reports = (
            evaluate_targets(
                target_names,
                dataset_paths_by_target=dataset_paths_by_target,
                split_filter=args.split,
                execution_options=execution_options,
                judge_options=judge_options,
                llm_client=llm_client,
                trace_sink=trace_sink,
                captured_execution_outputs_by_target=baseline_execution_outputs_by_target,
            )
            if compare_to_baseline
            else []
        )
        baseline_by_target = {
            str(report.get("target") or ""): report for report in baseline_reports
        }

        if args.candidate_dir is not None:
            reports = evaluate_candidate_bundle(
                target_names,
                candidate_dir=args.candidate_dir,
                dataset_paths_by_target=dataset_paths_by_target,
                split_filter=args.split,
                baseline_reports_by_target=baseline_by_target or None,
                execution_options=execution_options,
                judge_options=judge_options,
                llm_client=llm_client,
                trace_sink=trace_sink,
                baseline_execution_outputs_by_target=baseline_execution_outputs_by_target,
            )
        else:
            reports = evaluate_targets(
                target_names,
                candidate_paths_by_target=candidate_paths or None,
                dataset_paths_by_target=dataset_paths_by_target,
                split_filter=args.split,
                baseline_reports_by_target=baseline_by_target or None,
                execution_options=execution_options,
                judge_options=judge_options,
                llm_client=llm_client,
                trace_sink=trace_sink,
                baseline_execution_outputs_by_target=baseline_execution_outputs_by_target,
            )

        if args.trace_jsonl is not None and trace_sink is not None:
            args.trace_jsonl.parent.mkdir(parents=True, exist_ok=True)
            sanitized_path = trace_sink.trace_paths()["sanitized_traces"]
            args.trace_jsonl.write_text(
                sanitized_path.read_text() if sanitized_path.exists() else ""
            )

    for report in reports:
        _print_report(report)

    if args.report_json is not None:
        args.report_json.write_text(
            json.dumps(
                {
                    "reports": reports,
                    "baselineReports": baseline_reports,
                },
                indent=2,
                sort_keys=True,
            )
        )
    if args.report_md is not None:
        args.report_md.write_text(
            render_report_markdown(reports, baseline_reports=baseline_reports or None)
        )
    if args.baseline_report is not None:
        args.baseline_report.write_text(
            json.dumps({"baselineReports": baseline_reports}, indent=2, sort_keys=True)
        )

    if args.strict and any(report["status"] != "pass" for report in reports):
        return 1
    if args.fail_on_regression and any(
        report["regressionStatus"] == "regressed" for report in reports
    ):
        return 1
    if args.min_score is not None and any(
        float(report["scorePercent"]) < args.min_score for report in reports
    ):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
