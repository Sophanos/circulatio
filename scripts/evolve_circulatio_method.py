#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))


def parse_args(default_target_order: tuple[str, ...]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Stage and evaluate offline Circulatio self-evolution candidate bundles."
    )
    parser.add_argument(
        "--target",
        choices=["all", *default_target_order],
        default="all",
        help="Artifact target to evolve.",
    )
    parser.add_argument(
        "--strategy",
        choices=["manual", "reflection", "pareto_reflection"],
        default="manual",
        help="Offline candidate-generation strategy.",
    )
    parser.add_argument(
        "--budget",
        type=int,
        help="Backward-compatible alias for --max-generated-candidates.",
    )
    parser.add_argument(
        "--iterations",
        type=int,
        default=1,
        help="Automatic-strategy iteration count.",
    )
    parser.add_argument(
        "--population-size",
        type=int,
        default=2,
        help="Automatic-strategy candidate count per iteration.",
    )
    parser.add_argument(
        "--max-generated-candidates",
        type=int,
        help="Maximum number of generated candidates across the run.",
    )
    parser.add_argument(
        "--execution",
        action=argparse.BooleanOptionalAction,
        default=None,
        help="Enable execution-backed evaluation. Defaults on for automatic strategies.",
    )
    parser.add_argument(
        "--judge",
        action=argparse.BooleanOptionalAction,
        default=None,
        help="Enable advisory judge scoring. Defaults on for automatic strategies.",
    )
    parser.add_argument(
        "--judge-mode",
        choices=["absolute", "pairwise"],
        default=None,
        help="Optional judge scoring mode override when advisory judging is enabled.",
    )
    parser.add_argument(
        "--provider",
        help="Optional Hermes auxiliary-client provider override.",
    )
    parser.add_argument(
        "--model",
        help="Optional model override for automatic generation/execution/judge.",
    )
    parser.add_argument(
        "--timeout-seconds",
        type=float,
        help="Optional timeout override for automatic generation/execution/judge.",
    )
    parser.add_argument(
        "--trace-raw",
        action="store_true",
        help="Include raw trace payloads in run-local trace artifacts.",
    )
    parser.add_argument(
        "--create-review-branch",
        action="store_true",
        help="Apply the selected candidate into a new review branch after the run completes.",
    )
    parser.add_argument(
        "--prompt-fragments",
        type=Path,
        help="Manual prompt_fragments.py candidate input.",
    )
    parser.add_argument(
        "--skill-file",
        type=Path,
        help="Manual SKILL.md candidate input.",
    )
    parser.add_argument(
        "--schemas-file",
        type=Path,
        help="Manual schemas.py candidate input.",
    )
    parser.add_argument(
        "--split",
        action="append",
        choices=["train", "dev", "holdout", "redteam", "regression"],
        help="Optional dataset split filter. May be passed multiple times.",
    )
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=REPO_ROOT / "artifacts" / "self_evolution" / "runs",
        help="Directory for generated review packages.",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Exit non-zero when the staged candidate bundle fails evaluation.",
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


def main() -> int:
    from tools.self_evolution import (
        DEFAULT_TARGET_ORDER,
        EvolutionGenerationConfig,
        ExecutionOptions,
        HermesEvolutionLlmClient,
        JudgeOptions,
        evolve_candidates,
    )

    args = parse_args(DEFAULT_TARGET_ORDER)
    target_names = list(DEFAULT_TARGET_ORDER) if args.target == "all" else [args.target]
    candidate_paths: dict[str, Path] = {}
    for target_name in target_names:
        candidate_path = _candidate_path(target_name, args)
        if candidate_path is not None:
            candidate_paths[target_name] = candidate_path

    if args.strategy == "manual" and not candidate_paths:
        raise SystemExit("--strategy manual requires candidate paths for the selected targets.")
    if args.strategy == "manual" and set(candidate_paths) != set(target_names):
        missing_targets = [name for name in target_names if name not in candidate_paths]
        missing_label = ", ".join(missing_targets)
        raise SystemExit(
            "--strategy manual requires candidate paths for every selected target. "
            f"Missing: {missing_label}"
        )
    if args.strategy != "manual" and candidate_paths:
        raise SystemExit("Automatic strategies do not accept manual candidate-path overrides.")

    execution_enabled = (
        bool(args.execution)
        if args.execution is not None
        else args.strategy != "manual"
    )
    judge_enabled = (
        bool(args.judge)
        if args.judge is not None
        else args.strategy != "manual"
    )
    if judge_enabled:
        execution_enabled = True

    generation_config = EvolutionGenerationConfig(
        iterations=args.iterations,
        population_size=args.population_size,
        max_generated_candidates=args.max_generated_candidates or args.budget,
        provider=args.provider or "auto",
        model=args.model,
        timeout_seconds=args.timeout_seconds,
        trace_raw=args.trace_raw,
        create_review_branch=args.create_review_branch,
    )
    execution_options = ExecutionOptions(
        enabled=execution_enabled,
        timeout_seconds=args.timeout_seconds,
        stage_name="optimize",
    )
    judge_options = JudgeOptions(
        enabled=judge_enabled,
        timeout_seconds=args.timeout_seconds,
        mode=args.judge_mode,
    )
    llm_client = None
    if execution_enabled and args.strategy == "manual":
        llm_client = HermesEvolutionLlmClient(
            provider=args.provider,
            model=args.model,
            timeout_seconds=args.timeout_seconds,
            cache_root=args.out_dir / ".cache",
        )

    result = evolve_candidates(
        target_names=target_names,
        strategy=args.strategy,
        candidate_paths=candidate_paths,
        out_dir=args.out_dir,
        split_filter=args.split,
        generation_config=generation_config,
        execution_options=execution_options,
        judge_options=judge_options,
        llm_client=llm_client,
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    if args.strict and result["status"] != "pass":
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
