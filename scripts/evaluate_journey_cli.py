#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Evaluate local external coding CLIs against repo-local journey-routing contracts."
        )
    )
    parser.add_argument(
        "--adapter",
        action="append",
        choices=["all", "fake", "kimi", "codex", "opencode", "hermes"],
        default=None,
        help="Adapter(s) to run. Repeatable. Defaults to all enabled adapters.",
    )
    parser.add_argument(
        "--adapter-config",
        type=Path,
        help="Optional override config path for adapter definitions.",
    )
    parser.add_argument(
        "--dataset",
        action="append",
        type=Path,
        default=[],
        help="Dataset path(s). Defaults to tests/evals/journey_cli/baseline.jsonl.",
    )
    parser.add_argument(
        "--split",
        action="append",
        choices=["train", "dev", "holdout", "redteam", "regression"],
        help="Optional split filter. Repeatable.",
    )
    parser.add_argument(
        "--case",
        action="append",
        help="Optional case id filter. Repeatable.",
    )
    parser.add_argument(
        "--include-tag",
        action="append",
        help="Require one or more tags. Repeatable.",
    )
    parser.add_argument(
        "--exclude-tag",
        action="append",
        help="Exclude one or more tags. Repeatable.",
    )
    parser.add_argument(
        "--require-adapters",
        action="store_true",
        help="Fail when a requested adapter is unavailable.",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help=(
            "Exit non-zero on scored failures, missing required adapters, or baseline regressions."
        ),
    )
    parser.add_argument(
        "--compare-baseline",
        type=Path,
        help="Optional prior summary.json to compare against.",
    )
    parser.add_argument(
        "--write-baseline",
        type=Path,
        help="Write the current summary as a baseline snapshot.",
    )
    parser.add_argument(
        "--cache-root",
        type=Path,
        help="Override the Journey CLI eval cache root.",
    )
    parser.add_argument(
        "--no-cache",
        action="store_true",
        help="Disable cache reads and writes.",
    )
    parser.add_argument(
        "--refresh",
        action="store_true",
        help="Ignore cached results and overwrite them with fresh runs.",
    )
    parser.add_argument(
        "--jobs",
        type=int,
        default=1,
        help="Reserved parallelism control. Phase 1 stays sequential. Default: 1.",
    )
    parser.add_argument(
        "--timeout-seconds",
        type=int,
        help="Optional adapter timeout override.",
    )
    parser.add_argument(
        "--max-output-bytes",
        type=int,
        help="Optional in-memory output cap for retained raw text.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Build prompts, manifests, and run directories without invoking subprocesses.",
    )
    parser.add_argument(
        "--report-json",
        type=Path,
        help="Write the summary JSON to an explicit path.",
    )
    parser.add_argument(
        "--report-md",
        type=Path,
        help="Write the markdown summary to an explicit path.",
    )
    parser.add_argument(
        "--trace-jsonl",
        type=Path,
        help="Write sanitized traces to an explicit path.",
    )
    parser.add_argument(
        "--ritual-eval",
        action="store_true",
        help="Run the ritual journey simulator, provider gate evaluator, and artifact audit mode.",
    )
    parser.add_argument(
        "--ritual-output-root",
        type=Path,
        help="Output root for ritual eval runs. Defaults to artifacts/journey_cli_eval/runs.",
    )
    parser.add_argument(
        "--ritual-render-root",
        type=Path,
        help=(
            "Artifact public root for rendered rituals. Defaults to Hermes Rituals "
            "public/artifacts."
        ),
    )
    parser.add_argument(
        "--ritual-plan-root",
        type=Path,
        help="Plan storage root for rendered rituals. Defaults to artifacts/rituals/plans.",
    )
    parser.add_argument(
        "--ritual-base-url",
        default="http://localhost:3000",
        help="Base URL used for artifact links and optional HTTP checks.",
    )
    parser.add_argument(
        "--ritual-provider-profile",
        default="mock",
        choices=[
            "mock",
            "chutes_speech",
            "chutes_audio",
            "chutes_image",
            "chutes_video",
            "chutes_all",
        ],
        help="Provider profile for accepted ritual renders in ritual eval mode.",
    )
    parser.add_argument(
        "--ritual-live-providers",
        action="store_true",
        help="Allow provider-backed accepted ritual renders when budget and gates pass.",
    )
    parser.add_argument(
        "--ritual-include-video",
        action="store_true",
        help="Request cinema in accepted ritual renders. Requires live providers and beta gates.",
    )
    parser.add_argument(
        "--ritual-allow-beta-video",
        action="store_true",
        help="Pass the beta video gate for accepted ritual renders.",
    )
    parser.add_argument(
        "--ritual-max-cost-usd",
        type=float,
        default=0.0,
        help="Budget guard for provider-backed accepted ritual renders.",
    )
    parser.add_argument(
        "--ritual-chutes-token-env",
        default="CHUTES_API_TOKEN",
        help="Environment variable name containing the Chutes token.",
    )
    parser.add_argument(
        "--ritual-http-check",
        action="store_true",
        help="Fetch artifact page URLs during the browser audit.",
    )
    parser.add_argument(
        "--ritual-request-timeout-seconds",
        type=int,
        default=180,
        help="Provider request timeout for accepted ritual renders.",
    )
    parser.add_argument(
        "--ritual-run-id",
        help="Optional explicit ritual eval run id.",
    )
    return parser.parse_args()


def _print_summary(summary: dict[str, object]) -> None:
    adapters_run = ", ".join(str(item) for item in list(summary.get("adaptersRun", []))) or "none"
    print(f"run={summary.get('runId')} adapters={adapters_run}")
    for adapter, stats in dict(summary.get("adapterSummaries", {})).items():
        score_percent = float(stats.get("scorePercent") or 0.0)
        print(
            f"[{adapter}] pass={stats.get('passCount')} fail={stats.get('failCount')} "
            f"blocking={stats.get('blockingFailures')} score={score_percent:.2%}"
        )
    skipped = dict(summary.get("adaptersSkipped", {}))
    for adapter, reason in skipped.items():
        print(f"[skip] {adapter}: {reason}")
    missing = list(summary.get("missingRequiredAdapters", []))
    for adapter in missing:
        print(f"[missing-required] {adapter}")
    for item in list(summary.get("results", [])):
        if not isinstance(item, dict):
            continue
        label = "ok" if bool(item.get("passed")) else "fail"
        print(
            f"  - [{label}] {item.get('adapter')} / {item.get('case_id')} "
            f"{item.get('score')}/{item.get('max_score')}"
        )
        for finding in list(item.get("findings", [])):
            print(f"    {finding}")


def _print_ritual_summary(report: dict[str, object]) -> None:
    print(f"run={report.get('runId')} mode=ritual_eval passed={report.get('passed')}")
    print(f"report={report.get('runDir')}/report.md")
    for finding in list(report.get("findings", [])):
        print(f"  - {finding}")


def main() -> int:
    args = parse_args()
    if args.ritual_eval:
        from tools.journey_cli_eval.ritual_mode import run_ritual_journey_eval

        report = run_ritual_journey_eval(
            output_root=args.ritual_output_root,
            render_artifact_root=args.ritual_render_root,
            plan_root=args.ritual_plan_root,
            base_url=args.ritual_base_url,
            provider_profile=args.ritual_provider_profile,
            live_providers=args.ritual_live_providers,
            include_video=args.ritual_include_video,
            allow_beta_video=args.ritual_allow_beta_video,
            max_cost_usd=args.ritual_max_cost_usd,
            chutes_token_env=args.ritual_chutes_token_env,
            http_check=args.ritual_http_check,
            request_timeout_seconds=args.ritual_request_timeout_seconds,
            run_id=args.ritual_run_id,
        )
        _print_ritual_summary(report)
        return 0 if (not args.strict or bool(report.get("passed"))) else 1

    from tools.journey_cli_eval.runner import run_journey_cli_eval

    summary = run_journey_cli_eval(
        adapters_requested=args.adapter or ["all"],
        adapter_config_path=args.adapter_config,
        dataset_paths=args.dataset or None,
        split_filter=args.split,
        case_ids=args.case,
        include_tags=args.include_tag,
        exclude_tags=args.exclude_tag,
        require_adapters=args.require_adapters,
        compare_baseline_path=args.compare_baseline,
        write_baseline_path=args.write_baseline,
        cache_root=args.cache_root,
        use_cache=not args.no_cache,
        refresh=args.refresh,
        jobs=args.jobs,
        timeout_seconds=args.timeout_seconds,
        max_output_bytes=args.max_output_bytes,
        dry_run=args.dry_run,
        report_json_path=args.report_json,
        report_md_path=args.report_md,
        trace_jsonl_path=args.trace_jsonl,
    )
    _print_summary(summary)
    if not args.strict:
        return 0
    if list(summary.get("missingRequiredAdapters", [])):
        return 1
    if any(
        not bool(item.get("passed"))
        for item in list(summary.get("results", []))
        if isinstance(item, dict)
    ):
        return 1
    baseline = summary.get("baselineComparison")
    if isinstance(baseline, dict) and bool(baseline.get("hasRegression")):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
