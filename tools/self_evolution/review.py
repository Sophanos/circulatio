from __future__ import annotations

import json
import shlex
import stat
from collections.abc import Mapping
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .artifacts import build_diff_patch, candidate_hashes, current_git_sha
from .dataset_builder import load_case_set
from .targets import REPO_ROOT, get_target


def _normalize_text(value: object) -> str:
    return " ".join(str(value).split()).lower()



def _contains(haystack: object, needle: object) -> bool:
    return _normalize_text(needle) in _normalize_text(haystack)



def _string_list(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item) for item in value]



def _string_mapping_of_lists(value: object) -> dict[str, list[str]]:
    if not isinstance(value, Mapping):
        return {}
    result: dict[str, list[str]] = {}
    for key, item in value.items():
        result[str(key)] = _string_list(item)
    return result



def _final_evaluation_status(reports: list[dict[str, object]]) -> str:
    return "pass" if all(report.get("status") == "pass" for report in reports) else "fail"



def _guardrail_phrase_entries(case: dict[str, object]) -> list[dict[str, str]]:
    severity = str(case.get("severity") or "blocking")
    if severity == "minor":
        return []
    case_id = str(case.get("caseId") or "")
    entries: list[dict[str, str]] = []
    for key in ("requiredSubstrings", "requiredSystemSubstrings", "requiredUserSubstrings"):
        for phrase in _string_list(case.get(key)):
            entries.append(
                {
                    "caseId": case_id,
                    "severity": severity,
                    "location": key,
                    "expectation": "required",
                    "phrase": phrase,
                }
            )
    for key, values in _string_mapping_of_lists(case.get("requiredInstructionSubstrings")).items():
        for phrase in values:
            entries.append(
                {
                    "caseId": case_id,
                    "severity": severity,
                    "location": f"instructions.{key}",
                    "expectation": "required",
                    "phrase": phrase,
                }
            )
    for phrase in _string_list(case.get("forbiddenSubstrings")):
        entries.append(
            {
                "caseId": case_id,
                "severity": severity,
                "location": "forbiddenSubstrings",
                "expectation": "forbidden",
                "phrase": phrase,
            }
        )
    return entries



def analyze_guardrail_phrase_changes(
    *,
    target_names: tuple[str, ...] | list[str],
    candidate_paths: Mapping[str, Path],
) -> dict[str, list[dict[str, object]]]:
    phrase_changes: dict[str, list[dict[str, object]]] = {}
    for target_name in target_names:
        candidate_path = candidate_paths.get(target_name)
        if candidate_path is None:
            continue
        target = get_target(target_name)
        baseline_text = target.baseline_path.read_text()
        candidate_text = candidate_path.read_text()
        cases = load_case_set(target.dataset_paths)
        entries_by_key: dict[tuple[str, str, str, str], dict[str, str]] = {}
        for case in cases:
            for entry in _guardrail_phrase_entries(case):
                key = (
                    entry["caseId"],
                    entry["severity"],
                    entry["location"],
                    entry["phrase"],
                )
                entries_by_key.setdefault(key, entry)
        changes: list[dict[str, object]] = []
        for entry in entries_by_key.values():
            phrase = entry["phrase"]
            baseline_present = _contains(baseline_text, phrase)
            candidate_present = _contains(candidate_text, phrase)
            if baseline_present == candidate_present:
                continue
            changes.append(
                {
                    **entry,
                    "baselinePresent": baseline_present,
                    "candidatePresent": candidate_present,
                }
            )
        if changes:
            phrase_changes[target_name] = sorted(
                changes,
                key=lambda item: (
                    0 if item["severity"] == "blocking" else 1,
                    str(item["caseId"]),
                    str(item["location"]),
                    str(item["phrase"]),
                ),
            )
    return phrase_changes



def _phrase_change_label(change: Mapping[str, object]) -> str:
    expectation = str(change.get("expectation") or "required")
    baseline_present = bool(change.get("baselinePresent"))
    candidate_present = bool(change.get("candidatePresent"))
    if expectation == "forbidden":
        if not baseline_present and candidate_present:
            return "introduced forbidden phrase"
        return "removed forbidden phrase"
    if baseline_present and not candidate_present:
        return "removed required phrase"
    return "added required phrase"



def _render_report_block(
    lines: list[str],
    reports: list[dict[str, object]],
    *,
    baseline_reports: list[dict[str, object]] | None = None,
    guardrail_phrase_changes: Mapping[str, list[dict[str, object]]] | None = None,
) -> None:
    baseline_by_target = {
        str(report.get("target") or ""): report for report in baseline_reports or []
    }
    for report in reports:
        target = str(report.get("target") or "<unknown>")
        baseline = baseline_by_target.get(target)
        lines.append(f"## {target}")
        lines.append("")
        lines.append(f"- Status: `{report.get('status')}`")
        lines.append(f"- Regression: `{report.get('regressionStatus')}`")
        lines.append(
            "- Hard score: "
            f"`{report.get('score')}` / `{report.get('maxScore')}` "
            f"({float(report.get('scorePercent') or 0.0):.2%})"
        )
        if report.get("executionMaxScore"):
            lines.append(
                "- Execution score: "
                f"`{report.get('executionScore')}` / `{report.get('executionMaxScore')}` "
                f"({float(report.get('executionScorePercent') or 0.0):.2%})"
            )
        if report.get("judgeMaxScore"):
            lines.append(
                "- Advisory judge: "
                f"`{report.get('judgeScore')}` / `{report.get('judgeMaxScore')}` "
                f"({float(report.get('judgeScorePercent') or 0.0):.2%})"
            )
            lines.append(
                "- Judge concerns: "
                f"`{report.get('judgeConcernCount')}` total / "
                f"`{report.get('criticalJudgeConcernCount')}` critical"
            )
        lines.append(f"- Blocking failures: `{report.get('blockingFailures')}`")
        lines.append(f"- Failed cases: `{report.get('failedCases')}` / `{report.get('caseCount')}`")
        if baseline is not None:
            lines.append(
                "- Baseline hard score: "
                f"`{baseline.get('score')}` / `{baseline.get('maxScore')}` "
                f"({float(baseline.get('scorePercent') or 0.0):.2%})"
            )
        constraint_findings = list(report.get("constraintFindings", []))
        if constraint_findings:
            lines.append("- Constraint findings:")
            for finding in constraint_findings:
                lines.append(f"  - {finding}")
        failed_cases = [
            case
            for case in list(report.get("cases", []))
            if not bool(case.get("passed"))
            and str(case.get("result_kind") or "deterministic") != "judge"
        ]
        if failed_cases:
            lines.append("- Failed cases:")
            for case in failed_cases:
                lines.append(
                    "  - "
                    f"`{case.get('case_id')}` [{case.get('dataset')}] "
                    f"`{case.get('severity')}` / `{case.get('gate_type')}`"
                )
                for finding in list(case.get("findings", [])):
                    lines.append(f"    - {finding}")
        judge_cases = [
            case
            for case in list(report.get("cases", []))
            if str(case.get("result_kind")) == "judge"
        ]
        if judge_cases:
            lines.append("- Advisory judge notes:")
            for case in judge_cases:
                if not list(case.get("findings", [])):
                    continue
                lines.append(f"  - `{case.get('case_id')}`")
                for finding in list(case.get("findings", [])):
                    lines.append(f"    - {finding}")
        phrase_changes = list((guardrail_phrase_changes or {}).get(target, []))
        if phrase_changes:
            lines.append("- Changed guardrail-critical phrases:")
            for change in phrase_changes:
                lines.append(
                    "  - "
                    f"`{change.get('caseId')}` [{change.get('severity')}] "
                    f"{_phrase_change_label(change)} in `{change.get('location')}`: "
                    f"{change.get('phrase')}"
                )
        lines.append("")



def render_report_markdown(
    reports: list[dict[str, object]],
    *,
    baseline_reports: list[dict[str, object]] | None = None,
    include_checklist: bool = False,
    stage_reports: Mapping[str, list[dict[str, object]]] | None = None,
    baseline_stage_reports: Mapping[str, list[dict[str, object]]] | None = None,
    evaluation_status: str | None = None,
    promotion_status: str | None = None,
    stage_history: list[dict[str, object]] | None = None,
    guardrail_phrase_changes: Mapping[str, list[dict[str, object]]] | None = None,
    candidate_index: list[dict[str, object]] | None = None,
    frontier: list[dict[str, object]] | None = None,
    selected_candidate_id: str | None = None,
) -> str:
    lines = ["# Evolution OS Review Report", ""]
    if evaluation_status is not None:
        lines.append(f"- Evaluation status: `{evaluation_status}`")
    if promotion_status is not None:
        lines.append(f"- Promotion status: `{promotion_status}`")
    if selected_candidate_id is not None:
        lines.append(f"- Selected candidate: `{selected_candidate_id}`")
    if candidate_index is not None:
        lines.append(f"- Candidate count: `{len(candidate_index)}`")
    if frontier is not None:
        lines.append(f"- Frontier size: `{len(frontier)}`")
    if evaluation_status is not None or promotion_status is not None:
        lines.append("")

    if candidate_index:
        lines.append("## Candidate Search Summary")
        lines.append("")
        for candidate in candidate_index[:10]:
            lines.append(
                "- "
                f"`{candidate.get('candidateId')}` / `{candidate.get('status')}` / "
                f"det `{float(candidate.get('deterministicScorePercent') or 0.0):.2%}` / "
                f"exec `{float(candidate.get('executionScorePercent') or 0.0):.2%}` / "
                f"judge `{float(candidate.get('judgeScore') or 0.0):.2f}`"
            )
        lines.append("")

    if stage_history:
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

    if stage_reports:
        for stage_name, stage_items in stage_reports.items():
            if not stage_items:
                continue
            lines.append(f"## {stage_name.title()} Stage")
            lines.append("")
            _render_report_block(
                lines,
                stage_items,
                baseline_reports=(baseline_stage_reports or {}).get(stage_name),
                guardrail_phrase_changes=guardrail_phrase_changes,
            )
    else:
        _render_report_block(
            lines,
            reports,
            baseline_reports=baseline_reports,
            guardrail_phrase_changes=guardrail_phrase_changes,
        )

    if include_checklist:
        lines.extend(
            [
                "## Reviewer Checklist",
                "",
                "- Confirm only `prompt_fragments.py`, `SKILL.md`, or descriptive text in "
                "`schemas.py` changed.",
                "- Confirm no immutable guardrail files are present in the candidate bundle.",
                "- Confirm safety, consent, evidence, and approval-boundary cases stayed green.",
                "- Confirm judge concerns are acceptable or promoted into deterministic "
                "checks before merge.",
                "- Confirm holdout was not used during generation feedback.",
                "- Confirm no runtime/service mutation API was introduced.",
                "- Confirm tool schema structure did not change.",
                "- Confirm normal repo tests still pass before merge.",
                "",
            ]
        )

    return "\n".join(lines).rstrip() + "\n"



def _write_branch_artifacts(
    *,
    run_dir: Path,
    selected_candidate_id: str | None,
    selected_candidate_paths: Mapping[str, Path],
) -> tuple[Path, Path]:
    branch_plan_path = run_dir / "branch_plan.md"
    script_path = run_dir / "apply_candidate_branch.sh"
    lines = ["# Branch Plan", "", "This package is offline-only and requires human review.", ""]
    if selected_candidate_id is not None:
        lines.append(f"Selected candidate: `{selected_candidate_id}`")
        lines.append("")
    lines.append("Changed files:")
    lines.append("")
    for target_name, path in selected_candidate_paths.items():
        target = get_target(target_name)
        lines.append(f"- `{target.baseline_relative_path}` <= `{path}`")
    lines.append("")
    lines.append("Suggested flow:")
    lines.append("")
    lines.append("1. Review `report.md`, `report.json`, and `diff.patch`.")
    lines.append("2. Run the local apply script on a clean working tree.")
    lines.append("3. Re-run repo tests before committing anything.")
    branch_plan_path.write_text("\n".join(lines).rstrip() + "\n")

    script_lines = [
        "#!/usr/bin/env bash",
        "set -euo pipefail",
        "BRANCH_NAME=${1:-evolution-review-$(date -u +%Y%m%dT%H%M%SZ)}",
        f"REPO_ROOT={shlex.quote(str(REPO_ROOT))}",
        "cd \"$REPO_ROOT\"",
        "if [[ -n \"$(git status --porcelain)\" ]]; then",
        '  echo "Working tree must be clean before applying review candidate." >&2',
        "  exit 1",
        "fi",
        "git checkout -b \"$BRANCH_NAME\"",
    ]
    for target_name, path in selected_candidate_paths.items():
        target = get_target(target_name)
        script_lines.append(
            f"cp {shlex.quote(str(path))} {shlex.quote(str(target.baseline_path))}"
        )
    script_lines.append('echo "Applied review candidate onto branch: $BRANCH_NAME"')
    script_path.write_text("\n".join(script_lines) + "\n")
    script_path.chmod(script_path.stat().st_mode | stat.S_IXUSR)
    return branch_plan_path, script_path



def write_review_package(
    *,
    run_dir: Path,
    target_names: tuple[str, ...] | list[str],
    candidate_paths: Mapping[str, Path],
    reports: list[dict[str, object]],
    baseline_reports: list[dict[str, object]] | None = None,
    generator_strategy: str,
    rationale_text: str,
    immutable_files_checked: bool,
    stage_reports: Mapping[str, list[dict[str, object]]] | None = None,
    baseline_stage_reports: Mapping[str, list[dict[str, object]]] | None = None,
    evaluation_status: str | None = None,
    promotion_status: str | None = None,
    stage_history: list[dict[str, object]] | None = None,
    candidate_index: list[dict[str, object]] | None = None,
    frontier: list[dict[str, object]] | None = None,
    selected_candidate_id: str | None = None,
    trace_paths: Mapping[str, Path] | None = None,
    suggested_eval_cases: list[dict[str, object]] | None = None,
) -> dict[str, Path]:
    report_path = run_dir / "report.json"
    report_md_path = run_dir / "report.md"
    diff_path = run_dir / "diff.patch"
    rationale_path = run_dir / "rationale.md"
    manifest_path = run_dir / "manifest.json"
    candidate_manifest_path = run_dir / "candidate_manifest.json"
    traces_path = run_dir / "sanitized_traces.jsonl"
    candidate_index_path = run_dir / "candidate_index.json"
    frontier_path = run_dir / "frontier.json"
    generation_trace_path = run_dir / "generation_trace.jsonl"
    execution_trace_path = run_dir / "execution_traces.jsonl"
    judge_score_path = run_dir / "judge_scores.jsonl"
    run_events_path = run_dir / "run_events.jsonl"
    suggested_eval_cases_path = run_dir / "suggested_eval_cases.jsonl"

    resolved_evaluation_status = evaluation_status or _final_evaluation_status(reports)
    resolved_promotion_status = promotion_status or (
        "deterministic_passed"
        if resolved_evaluation_status == "pass"
        else "failed"
    )
    guardrail_phrase_changes = analyze_guardrail_phrase_changes(
        target_names=target_names,
        candidate_paths=candidate_paths,
    )

    report_payload = {
        "reports": reports,
        "baselineReports": baseline_reports or [],
        "stageReports": dict(stage_reports or {}),
        "baselineStageReports": dict(baseline_stage_reports or {}),
        "status": resolved_evaluation_status,
        "promotionStatus": resolved_promotion_status,
        "stageHistory": list(stage_history or []),
        "guardrailPhraseChanges": guardrail_phrase_changes,
        "candidateIndex": candidate_index or [],
        "frontier": frontier or [],
        "selectedCandidateId": selected_candidate_id,
    }
    report_path.write_text(json.dumps(report_payload, indent=2, sort_keys=True))
    report_md_path.write_text(
        render_report_markdown(
            reports,
            baseline_reports=baseline_reports,
            include_checklist=True,
            stage_reports=stage_reports,
            baseline_stage_reports=baseline_stage_reports,
            evaluation_status=resolved_evaluation_status,
            promotion_status=resolved_promotion_status,
            stage_history=stage_history,
            guardrail_phrase_changes=guardrail_phrase_changes,
            candidate_index=candidate_index,
            frontier=frontier,
            selected_candidate_id=selected_candidate_id,
        )
    )
    rationale_path.write_text(rationale_text.rstrip() + "\n")
    diff_path.write_text(
        build_diff_patch(target_names=target_names, candidate_paths=dict(candidate_paths))
    )

    for path in [
        traces_path,
        generation_trace_path,
        execution_trace_path,
        judge_score_path,
        run_events_path,
    ]:
        if not path.exists():
            path.write_text("")
    if trace_paths:
        path_map = {
            "sanitized_traces": traces_path,
            "generation_trace": generation_trace_path,
            "execution_trace": execution_trace_path,
            "judge_trace": judge_score_path,
            "candidate_event": run_events_path,
        }
        for key, source_path in trace_paths.items():
            destination = path_map.get(key)
            if (
                destination is None
                or not source_path.exists()
                or source_path.resolve() == destination.resolve()
            ):
                continue
            destination.write_text(source_path.read_text())

    candidate_index_path.write_text(json.dumps(candidate_index or [], indent=2, sort_keys=True))
    frontier_path.write_text(json.dumps(frontier or [], indent=2, sort_keys=True))
    if suggested_eval_cases:
        suggested_eval_cases_path.write_text(
            "\n".join(json.dumps(item, sort_keys=True) for item in suggested_eval_cases) + "\n"
        )
    elif suggested_eval_cases_path.exists():
        suggested_eval_cases_path.write_text("")

    base_hashes, staged_hashes = candidate_hashes(
        target_names=target_names,
        candidate_paths=dict(candidate_paths),
    )
    dataset_paths = sorted(
        {
            str(dataset_path)
            for report_group in [reports, *list((stage_reports or {}).values())]
            for report in report_group
            for dataset_path in list(report.get("datasetPaths", []))
        }
    )
    branch_plan_path, branch_script_path = _write_branch_artifacts(
        run_dir=run_dir,
        selected_candidate_id=selected_candidate_id,
        selected_candidate_paths=candidate_paths,
    )
    manifest_payload: dict[str, Any] = {
        "schemaVersion": 1,
        "runId": run_dir.name,
        "createdAt": datetime.now(tz=UTC).isoformat(),
        "baseGitSha": current_git_sha(),
        "targetNames": list(target_names),
        "generatorStrategy": generator_strategy,
        "baseArtifactHashes": base_hashes,
        "candidateArtifactHashes": staged_hashes,
        "datasetPaths": dataset_paths,
        "changedFiles": sorted(staged_hashes.keys()),
        "diffPaths": [diff_path.name],
        "rationalePath": rationale_path.name,
        "evaluationReportPath": report_path.name,
        "status": resolved_promotion_status,
        "evaluationStatus": resolved_evaluation_status,
        "promotionStages": list(stage_history or []),
        "immutableFilesChecked": immutable_files_checked,
        "humanReviewRequired": True,
        "liveRuntimeMutated": False,
        "serviceMutationApiUsed": False,
        "selectedCandidateId": selected_candidate_id,
        "candidateCount": len(candidate_index or []),
        "frontierPath": frontier_path.name,
        "candidateIndexPath": candidate_index_path.name,
        "generationTracePath": generation_trace_path.name,
        "executionTracePath": execution_trace_path.name,
        "judgeScorePath": judge_score_path.name,
        "branchPlanPath": branch_plan_path.name,
        "applyBranchScriptPath": branch_script_path.name,
    }
    manifest_text = json.dumps(manifest_payload, indent=2, sort_keys=True)
    manifest_path.write_text(manifest_text)
    candidate_manifest_path.write_text(manifest_text)

    result = {
        "report_json": report_path,
        "report_md": report_md_path,
        "diff_patch": diff_path,
        "manifest": manifest_path,
        "candidate_manifest": candidate_manifest_path,
        "rationale": rationale_path,
        "sanitized_traces": traces_path,
        "candidate_index": candidate_index_path,
        "frontier": frontier_path,
        "generation_trace": generation_trace_path,
        "execution_traces": execution_trace_path,
        "judge_scores": judge_score_path,
        "run_events": run_events_path,
        "branch_plan": branch_plan_path,
        "apply_candidate_branch": branch_script_path,
    }
    if suggested_eval_cases_path.exists():
        result["suggested_eval_cases"] = suggested_eval_cases_path
    return result
