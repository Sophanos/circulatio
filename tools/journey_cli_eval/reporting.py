from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path

from .scoring import JourneyCaseResult, build_adapter_summaries, build_case_consensus


def load_summary(path: Path) -> dict[str, object]:
    payload = json.loads(path.read_text())
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must contain a JSON object.")
    return {str(key): value for key, value in payload.items()}


def build_summary(
    *,
    run_id: str,
    created_at: str,
    git_sha: str | None,
    repo_root: Path,
    datasets: list[str],
    split_filter: list[str],
    case_ids: list[str],
    adapters_requested: list[str],
    adapters_run: list[str],
    adapters_skipped: dict[str, str],
    adapter_versions: dict[str, str | None],
    artifact_hashes: dict[str, str],
    command_config_hash: str,
    results: list[JourneyCaseResult],
    run_dir: Path,
    compare_baseline: dict[str, object] | None = None,
) -> dict[str, object]:
    adapter_summaries = build_adapter_summaries(results)
    case_consensus = build_case_consensus(results)
    summary = {
        "runId": run_id,
        "createdAt": created_at,
        "gitSha": git_sha,
        "repoRoot": str(repo_root),
        "datasets": datasets,
        "splitFilter": split_filter,
        "caseIds": case_ids,
        "adaptersRequested": adapters_requested,
        "adaptersRun": adapters_run,
        "adaptersSkipped": adapters_skipped,
        "adapterVersions": adapter_versions,
        "artifactHashes": artifact_hashes,
        "commandConfigHash": command_config_hash,
        "runDir": str(run_dir),
        "adapterSummaries": adapter_summaries,
        "caseConsensus": case_consensus,
        "results": [result.as_dict() for result in results],
    }
    if compare_baseline is not None:
        summary["baselineComparison"] = compare_against_baseline(summary, compare_baseline)
    return summary


def compare_against_baseline(
    current: dict[str, object],
    baseline: dict[str, object],
) -> dict[str, object]:
    baseline_results = {
        (str(item.get("adapter") or ""), str(item.get("case_id") or "")): item
        for item in list(baseline.get("results", []))
        if isinstance(item, dict)
    }
    regressions: list[dict[str, object]] = []
    for item in list(current.get("results", [])):
        if not isinstance(item, dict):
            continue
        key = (str(item.get("adapter") or ""), str(item.get("case_id") or ""))
        baseline_item = baseline_results.get(key)
        if baseline_item is None:
            continue
        current_passed = bool(item.get("passed"))
        baseline_passed = bool(baseline_item.get("passed"))
        current_score = int(item.get("score") or 0)
        baseline_score = int(baseline_item.get("score") or 0)
        if (baseline_passed and not current_passed) or current_score < baseline_score:
            regressions.append(
                {
                    "adapter": key[0],
                    "caseId": key[1],
                    "baselinePassed": baseline_passed,
                    "currentPassed": current_passed,
                    "baselineScore": baseline_score,
                    "currentScore": current_score,
                }
            )
    return {
        "regressions": regressions,
        "hasRegression": bool(regressions),
    }


def render_summary_markdown(summary: dict[str, object]) -> str:
    lines = ["# Journey CLI Evaluation Summary", ""]
    lines.append(f"- Run: `{summary.get('runId')}`")
    lines.append(f"- Created: `{summary.get('createdAt')}`")
    lines.append(f"- Git SHA: `{summary.get('gitSha')}`")
    lines.append("")
    lines.append("## Adapter Summary")
    lines.append("")
    for adapter, stats in dict(summary.get("adapterSummaries", {})).items():
        score_percent = float(stats.get("scorePercent") or 0.0)
        lines.append(
            "- "
            f"`{adapter}`: pass `{stats.get('passCount')}`, fail `{stats.get('failCount')}`, "
            f"blocking `{stats.get('blockingFailures')}`, score `{score_percent:.2%}`"
        )
    lines.append("")
    lines.append("## Failed Cases")
    lines.append("")
    for item in list(summary.get("results", [])):
        if not isinstance(item, dict) or bool(item.get("passed")):
            continue
        lines.append(
            "- "
            f"`{item.get('adapter')}` / `{item.get('case_id')}` "
            f"[{item.get('severity')}] {item.get('score')}/{item.get('max_score')}"
        )
        for finding in list(item.get("findings", [])):
            lines.append(f"  - {finding}")
    baseline = summary.get("baselineComparison")
    if isinstance(baseline, dict):
        lines.append("")
        lines.append("## Baseline Comparison")
        lines.append("")
        regressions = list(baseline.get("regressions", []))
        if regressions:
            for entry in regressions:
                lines.append(
                    "- "
                    f"`{entry.get('adapter')}` / `{entry.get('caseId')}` regressed "
                    f"({entry.get('baselineScore')} -> {entry.get('currentScore')})"
                )
        else:
            lines.append("- No regressions against the supplied baseline.")
    return "\n".join(lines).rstrip() + "\n"


def render_findings_to_targets(
    summary: dict[str, object], cases_by_id: dict[str, dict[str, object]]
) -> str:
    groups: dict[str, list[str]] = defaultdict(list)
    for item in list(summary.get("results", [])):
        if not isinstance(item, dict) or bool(item.get("passed")):
            continue
        case = cases_by_id.get(str(item.get("case_id") or ""), {})
        feedback = (
            case.get("methodEvalFeedback")
            if isinstance(case.get("methodEvalFeedback"), dict)
            else {}
        )
        target_kinds = [str(kind) for kind in list(feedback.get("targetKinds", []))]
        datasets = ", ".join(str(name) for name in list(feedback.get("suggestedDatasets", [])))
        line = (
            f"- {item.get('case_id')} / {item.get('adapter')}: "
            f"{'; '.join(str(finding) for finding in list(item.get('findings', []))[:2])}"
        )
        if datasets:
            line += f" Suggested datasets: {datasets}"
        if "skill" in target_kinds:
            groups["Skill routing candidates"].append(line)
        elif "tool_descriptions" in target_kinds:
            groups["Tool description candidates"].append(line)
        elif "prompt_fragments" in target_kinds:
            groups["Prompt fragment candidates"].append(line)
        elif "backend" in list(case.get("testLayers", [])):
            groups["Backend truth candidates"].append(line)
        elif "hermes_bridge" in list(case.get("testLayers", [])):
            groups["Bridge candidates"].append(line)
        elif "real_host_smoke" in list(case.get("testLayers", [])):
            groups["Real host smoke candidates"].append(line)
        else:
            groups["Unmapped findings"].append(line)
    lines = ["# Findings To Targets", ""]
    if not groups:
        lines.append("- No failing cases to map.")
        return "\n".join(lines).rstrip() + "\n"
    for heading, entries in groups.items():
        lines.append(f"## {heading}")
        lines.append("")
        lines.extend(entries)
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"
