from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path

from tools.self_evolution.artifacts import current_git_sha, default_run_id, sha256_file

from .adapters import (
    RawCliRun,
    adapter_available,
    adapter_requested_names,
    build_command,
    collect_adapter_version,
)
from .cache import JourneyEvalCache, build_cache_key
from .config import load_adapter_configs, redact_adapter_config
from .dataset import load_journey_cases
from .normalization import normalize_journey_output
from .process import execute_command
from .prompts import build_prompt_package
from .reporting import (
    build_summary,
    load_summary,
    render_findings_to_targets,
    render_summary_markdown,
)
from .scoring import JourneyCaseResult, score_journey_output
from .traces import JourneyTraceSink
from .workspace import compute_workspace_manifest, create_workspace, diff_manifests

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DATASET = REPO_ROOT / "tests" / "evals" / "journey_cli" / "baseline.jsonl"


def _created_at_now() -> str:
    return datetime.now(UTC).isoformat()


def _artifact_hashes() -> dict[str, str]:
    return {
        "SKILL.md": sha256_file(
            REPO_ROOT / "src" / "circulatio_hermes_plugin" / "skills" / "circulation" / "SKILL.md"
        ),
        "schemas.py": sha256_file(REPO_ROOT / "src" / "circulatio_hermes_plugin" / "schemas.py"),
        "JOURNEY_FAMILIES.md": sha256_file(
            REPO_ROOT / "tests" / "evals" / "journey_cli" / "JOURNEY_FAMILIES.md"
        ),
        "prompt_fragments.py": sha256_file(
            REPO_ROOT / "src" / "circulatio" / "llm" / "prompt_fragments.py"
        ),
    }


def _write_json(path: Path, payload: dict[str, object] | list[object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True, default=str))


def _command_config_hash(configs: dict[str, object]) -> str:
    encoded = json.dumps(configs, sort_keys=True, default=str).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _restore_cached_run(
    payload: dict[str, object],
    *,
    stdout_path: Path,
    stderr_path: Path,
) -> tuple[RawCliRun, dict[str, object], dict[str, object]]:
    stdout_text = str(payload.get("stdoutText") or "")
    stderr_text = str(payload.get("stderrText") or "")
    stdout_path.parent.mkdir(parents=True, exist_ok=True)
    stderr_path.parent.mkdir(parents=True, exist_ok=True)
    stdout_path.write_text(stdout_text)
    stderr_path.write_text(stderr_text)
    raw_run_payload = dict(payload.get("rawRun") or {})
    raw_run_payload["stdout_path"] = str(stdout_path)
    raw_run_payload["stderr_path"] = str(stderr_path)
    raw_run_payload["cache_hit"] = True
    raw_run = RawCliRun(**raw_run_payload)
    normalized = dict(payload.get("normalized") or {})
    score = dict(payload.get("score") or {})
    return raw_run, normalized, score


def run_journey_cli_eval(
    *,
    adapters_requested: str | list[str] = "all",
    adapter_config_path: Path | None = None,
    dataset_paths: list[Path] | None = None,
    split_filter: list[str] | None = None,
    case_ids: list[str] | None = None,
    include_tags: list[str] | None = None,
    exclude_tags: list[str] | None = None,
    require_adapters: bool = False,
    compare_baseline_path: Path | None = None,
    write_baseline_path: Path | None = None,
    cache_root: Path | None = None,
    use_cache: bool = True,
    refresh: bool = False,
    jobs: int = 1,
    timeout_seconds: int | None = None,
    max_output_bytes: int | None = None,
    dry_run: bool = False,
    report_json_path: Path | None = None,
    report_md_path: Path | None = None,
    trace_jsonl_path: Path | None = None,
) -> dict[str, object]:
    del jobs  # phase-1 implementation is intentionally sequential and reproducible
    run_id = default_run_id()
    created_at = _created_at_now()
    run_dir = REPO_ROOT / "artifacts" / "journey_cli_eval" / "runs" / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    trace_sink = JourneyTraceSink(run_dir / "traces")
    configs = load_adapter_configs(adapter_config_path)
    requested_names = adapter_requested_names(adapters_requested, configs)
    missing_required_adapters: list[str] = []
    adapters_run: list[str] = []
    adapters_skipped: dict[str, str] = {}
    adapter_versions: dict[str, str | None] = {}
    artifact_hashes = _artifact_hashes()
    git_sha = current_git_sha()
    command_config_hash = _command_config_hash(
        {name: redact_adapter_config(config) for name, config in configs.items()}
    )
    datasets = dataset_paths or [DEFAULT_DATASET]
    cases = load_journey_cases(
        datasets,
        split_filter=split_filter,
        case_ids=case_ids,
        include_tags=include_tags,
        exclude_tags=exclude_tags,
    )
    cases_by_id = {str(case.get("caseId") or ""): case for case in cases}
    cache = JourneyEvalCache(cache_root or (REPO_ROOT / "artifacts" / "journey_cli_eval" / "cache"))
    results: list[JourneyCaseResult] = []

    for adapter_name in requested_names:
        config = configs.get(adapter_name)
        if config is None:
            adapters_skipped[adapter_name] = "unknown_adapter"
            if require_adapters:
                missing_required_adapters.append(adapter_name)
            continue
        available = adapter_available(config)
        version = collect_adapter_version(config)
        adapter_versions[adapter_name] = version
        if not available:
            adapters_skipped[adapter_name] = "missing_binary"
            if require_adapters:
                missing_required_adapters.append(adapter_name)
            continue
        adapters_run.append(adapter_name)
        adapter_result_payloads: list[dict[str, object]] = []
        for case in cases:
            case_id = str(case.get("caseId") or "")
            case_packet_path = run_dir / "case_packets" / f"{case_id}.json"
            _write_json(case_packet_path, case)
            prompt_package = build_prompt_package(case)
            prompt_path = run_dir / "prompts" / adapter_name / f"{case_id}.txt"
            prompt_path.parent.mkdir(parents=True, exist_ok=True)
            prompt_path.write_text(prompt_package.prompt_text)
            if dry_run:
                trace_sink.record(
                    "runner_event",
                    {
                        "eventType": "dry_run_prompt_built",
                        "adapter": adapter_name,
                        "caseId": case_id,
                    },
                )
                continue
            workspace = create_workspace(
                run_id=run_id,
                adapter=adapter_name,
                case=case,
                prompt_text=prompt_package.prompt_text,
                case_packet=case,
                references={
                    "SKILL.md": prompt_package.skill_text,
                    "tool_schemas_compact.json": prompt_package.tool_schemas_json,
                    "JOURNEY_FAMILIES_excerpt.md": prompt_package.journey_excerpt,
                },
            )
            command = build_command(
                config,
                prompt_text=prompt_package.prompt_text,
                workspace_dir=workspace.root,
                case=case,
                timeout_override=timeout_seconds,
            )
            stdout_path = run_dir / "raw" / adapter_name / f"{case_id}.stdout"
            stderr_path = run_dir / "raw" / adapter_name / f"{case_id}.stderr"
            cache_key = build_cache_key(
                adapter_name=adapter_name,
                adapter_config=redact_adapter_config(config),
                adapter_version=version,
                case=case,
                prompt_text=prompt_package.prompt_text,
                artifact_hashes=artifact_hashes,
                git_sha=git_sha,
            )
            cached = None if refresh or not use_cache else cache.get(cache_key)
            if cached is not None:
                raw_run, normalized_payload, score_payload = _restore_cached_run(
                    cached,
                    stdout_path=stdout_path,
                    stderr_path=stderr_path,
                )
            else:
                raw_run = execute_command(
                    command,
                    stdout_path=stdout_path,
                    stderr_path=stderr_path,
                    version=version,
                    max_output_bytes=max_output_bytes,
                )
                after_manifest = compute_workspace_manifest(workspace.root)
                raw_run.workspace_diff = diff_manifests(workspace.before_manifest, after_manifest)
                normalized = normalize_journey_output(
                    raw_run.stdout_text, case=case, adapter=adapter_name
                )
                trace_id = trace_sink.record(
                    "adapter_run",
                    {
                        "adapter": adapter_name,
                        "caseId": case_id,
                        "rawRun": raw_run.as_dict(),
                        "parseStatus": normalized.parse_status,
                    },
                )
                score = score_journey_output(case, normalized, trace_ids=[trace_id])
                trace_sink.record(
                    "scoring",
                    {
                        "adapter": adapter_name,
                        "caseId": case_id,
                        "score": score.as_dict(),
                    },
                )
                normalized_payload = normalized.as_dict()
                score_payload = score.as_dict()
                if use_cache:
                    cache.put(
                        cache_key,
                        {
                            "rawRun": raw_run.as_dict(),
                            "stdoutText": raw_run.stdout_text,
                            "stderrText": raw_run.stderr_text,
                            "normalized": normalized_payload,
                            "score": score_payload,
                        },
                    )
            _write_json(
                run_dir / "normalized" / adapter_name / f"{case_id}.json", normalized_payload
            )
            _write_json(run_dir / "scores" / adapter_name / f"{case_id}.json", score_payload)
            result = JourneyCaseResult(**score_payload)
            results.append(result)
            adapter_result_payloads.append(score_payload)
        if not dry_run:
            _write_json(run_dir / "scores" / f"{adapter_name}.json", adapter_result_payloads)

    baseline_summary = load_summary(compare_baseline_path) if compare_baseline_path else None
    summary = build_summary(
        run_id=run_id,
        created_at=created_at,
        git_sha=git_sha,
        repo_root=REPO_ROOT,
        datasets=[str(path) for path in datasets],
        split_filter=list(split_filter or []),
        case_ids=[str(case.get("caseId") or "") for case in cases],
        adapters_requested=requested_names,
        adapters_run=adapters_run,
        adapters_skipped=adapters_skipped,
        adapter_versions=adapter_versions,
        artifact_hashes=artifact_hashes,
        command_config_hash=command_config_hash,
        results=results,
        run_dir=run_dir,
        compare_baseline=baseline_summary,
    )
    summary["missingRequiredAdapters"] = missing_required_adapters
    summary["dryRun"] = dry_run
    _write_json(
        run_dir / "manifest.json", {key: summary[key] for key in summary if key != "results"}
    )
    _write_json(run_dir / "summary.json", summary)
    if "baselineComparison" in summary:
        _write_json(run_dir / "regressions.json", dict(summary["baselineComparison"]))
    (run_dir / "summary.md").write_text(render_summary_markdown(summary))
    (run_dir / "findings_to_targets.md").write_text(
        render_findings_to_targets(summary, cases_by_id)
    )

    if write_baseline_path is not None:
        _write_json(write_baseline_path, summary)
    if report_json_path is not None:
        _write_json(report_json_path, summary)
    if report_md_path is not None:
        report_md_path.parent.mkdir(parents=True, exist_ok=True)
        report_md_path.write_text(render_summary_markdown(summary))
    if trace_jsonl_path is not None:
        trace_jsonl_path.parent.mkdir(parents=True, exist_ok=True)
        trace_jsonl_path.write_text(
            trace_sink.trace_paths()["sanitized_traces"].read_text()
            if trace_sink.trace_paths()["sanitized_traces"].exists()
            else ""
        )
    return summary
