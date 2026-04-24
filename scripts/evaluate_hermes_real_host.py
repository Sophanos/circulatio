#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATASET = REPO_ROOT / "tests" / "evals" / "hermes_real_host" / "baseline.jsonl"
ANSI_RE = re.compile(r"\x1b(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])")
SESSION_ID_RE = re.compile(r"session_id:\s*(\S+)")
TOOL_CALL_RE = re.compile(r"Tool call: (\S+)")
SUSPICIOUS_ID_RE = re.compile(
    r"\b(?:dream|reflection|event|symbolic_note|body_state|journey|run|review|"
    r"practice_session|practice|brief|goal|threshold)_[A-Za-z0-9_]+\b"
)
SUSPICIOUS_FIELD_RE = re.compile(
    r"\b(?:continuationState|llmInterpretationHealth|depthEngineHealth|"
    r"affectedEntityIds|requestId|idempotencyKey|materialId|runId|captureRunId|"
    r"proposalRefs|proposalRef|status)\b"
)
SUSPICIOUS_TOOL_RE = re.compile(r"\bcirculatio_[a-z_]+\b")
JSON_LIKE_RE = re.compile(r'"\w+"\s*:\s*')
SUSPICIOUS_REASONING_RE = re.compile(
    r"(?:Let's go with:|I think it's fine|to be safe,? I'll|Actually, the system message|"
    r"I can just translate|I'll just acknowledge)",
    re.IGNORECASE,
)
REPLY_REGEX_FLAGS = re.IGNORECASE | re.MULTILINE | re.DOTALL


@dataclass
class TurnSpec:
    case_id: str
    turn_id: str | None
    title: str
    session_label: str | None
    story_id: str | None
    story_title: str | None
    turn_index: int | None
    resume_from_case_id: str | None
    user_turn: str
    expected: dict[str, Any]
    max_turns: int | None
    dataset_path: str
    line_number: int

    def display_id(self) -> str:
        if self.turn_id is None:
            return self.case_id
        return f"{self.case_id}/{self.turn_id}"

    def location(self) -> str:
        return f"{self.dataset_path}:{self.line_number}"


@dataclass
class TurnResult:
    case_id: str
    turn_id: str | None
    title: str
    session_label: str | None
    session_id: str | None
    story_id: str | None
    story_title: str | None
    turn_index: int | None
    user_turn: str
    tool_calls: list[str]
    host_reply: str
    findings: list[str]
    passed: bool
    timed_out: bool
    return_code: int
    raw_output: str
    executed: bool

    def display_id(self) -> str:
        if self.turn_id is None:
            return self.case_id
        return f"{self.case_id}/{self.turn_id}"

    def to_summary_dict(self) -> dict[str, Any]:
        return {
            "caseId": self.case_id,
            "turnId": self.turn_id,
            "title": self.title,
            "sessionLabel": self.session_label,
            "sessionId": self.session_id,
            "storyId": self.story_id,
            "storyTitle": self.story_title,
            "turnIndex": self.turn_index,
            "userTurn": self.user_turn,
            "toolCalls": self.tool_calls,
            "hostReply": self.host_reply,
            "findings": self.findings,
            "passed": self.passed,
            "timedOut": self.timed_out,
            "returnCode": self.return_code,
            "executed": self.executed,
        }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Run a real Hermes-to-Circulatio host harness from JSONL cases against "
            "the actual hermes chat CLI."
        )
    )
    parser.add_argument(
        "--dataset",
        action="append",
        type=Path,
        default=[],
        help=(
            "Dataset path(s). Defaults to tests/evals/hermes_real_host/baseline.jsonl."
        ),
    )
    parser.add_argument(
        "--case",
        action="append",
        help="Optional case id filter. Repeatable.",
    )
    parser.add_argument(
        "--split",
        action="append",
        choices=["train", "dev", "holdout", "redteam", "regression"],
        help="Optional split filter. Repeatable.",
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
        "--hermes-bin",
        default="hermes",
        help="Hermes CLI binary to execute.",
    )
    parser.add_argument(
        "--toolset",
        default="circulatio",
        help="Toolset passed to hermes chat. Default: circulatio.",
    )
    parser.add_argument(
        "--max-turns",
        type=int,
        default=6,
        help="Default --max-turns for each hermes chat turn. Default: 6.",
    )
    parser.add_argument(
        "--timeout-seconds",
        type=int,
        default=120,
        help="Per-turn subprocess timeout in seconds. Default: 120.",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Exit non-zero if any turn fails.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Load and print matching cases without invoking hermes chat.",
    )
    parser.add_argument(
        "--report-json",
        type=Path,
        help="Optional JSON summary output path.",
    )
    parser.add_argument(
        "--report-md",
        type=Path,
        help="Optional markdown summary output path.",
    )
    parser.add_argument(
        "--trace-jsonl",
        type=Path,
        help="Optional sanitized raw trace JSONL output path.",
    )
    return parser.parse_args()


def sanitize_output(text: str | bytes) -> str:
    if isinstance(text, bytes):
        text = text.decode("utf-8", errors="replace")
    text = ANSI_RE.sub("", text)
    text = text.replace("\r\n", "\n").replace("\r", "\n").replace("\x00", "")
    text = text.replace("\u001b[2004h", "").replace("\u001b[2004l", "")
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def load_cases(dataset_paths: list[Path]) -> list[dict[str, Any]]:
    cases: list[dict[str, Any]] = []
    case_order = 0
    for dataset_path in dataset_paths:
        raw = dataset_path.read_text(encoding="utf-8")
        for line_number, line in enumerate(raw.splitlines(), start=1):
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue
            payload = json.loads(stripped)
            payload["_dataset_path"] = str(dataset_path)
            payload["_line_number"] = line_number
            payload["_case_order"] = case_order
            case_order += 1
            cases.append(payload)
    return cases


def filter_cases(
    cases: list[dict[str, Any]],
    *,
    case_ids: set[str],
    split_filter: set[str],
    include_tags: set[str],
    exclude_tags: set[str],
) -> list[dict[str, Any]]:
    selected: list[dict[str, Any]] = []
    for case in cases:
        if case_ids and str(case.get("caseId")) not in case_ids:
            continue
        if split_filter and str(case.get("split")) not in split_filter:
            continue
        tags = {str(item) for item in case.get("tags", [])}
        if include_tags and not include_tags.issubset(tags):
            continue
        if exclude_tags and tags.intersection(exclude_tags):
            continue
        selected.append(case)
    return selected


def _extract_host_reply(raw_output: str) -> tuple[str | None, str]:
    session_matches = list(SESSION_ID_RE.finditer(raw_output))
    if session_matches:
        session_match = session_matches[-1]
        return session_match.group(1), raw_output[session_match.end() :].strip()
    lines: list[str] = []
    for line in raw_output.splitlines():
        if re.match(r"^\d{2}:\d{2}:\d{2}\s+-\s+", line):
            continue
        if line.startswith("  [thinking]"):
            continue
        if line.startswith(("🤖", "🔗", "🔑", "✅", "🛠", "⚠", "📊")):
            continue
        if line.startswith("   ✅"):
            continue
        lines.append(line)
    return None, "\n".join(lines).strip()


def _sentence_count(text: str) -> int:
    pieces = [piece.strip() for piece in re.split(r"[.!?]+", text) if piece.strip()]
    return len(pieces)


def _question_count(text: str) -> int:
    return text.count("?")


def _looks_like_internal_leak(text: str) -> bool:
    if not text:
        return False
    return bool(
        SUSPICIOUS_ID_RE.search(text)
        or SUSPICIOUS_FIELD_RE.search(text)
        or SUSPICIOUS_TOOL_RE.search(text)
        or JSON_LIKE_RE.search(text)
        or SUSPICIOUS_REASONING_RE.search(text)
    )


def _optional_string(payload: dict[str, Any], key: str) -> str | None:
    value = payload.get(key)
    if value is None:
        return None
    return str(value)


def _optional_int(payload: dict[str, Any], key: str) -> int | None:
    value = payload.get(key)
    if value is None:
        return None
    return int(value)


def normalize_execution_turns(cases: list[dict[str, Any]]) -> list[TurnSpec]:
    turn_specs: list[TurnSpec] = []
    for case in cases:
        if "turns" in case:
            for turn in case.get("turns", []):
                turn_specs.append(
                    TurnSpec(
                        case_id=str(case["caseId"]),
                        turn_id=_optional_string(turn, "turnId"),
                        title=str(case.get("title", case["caseId"])),
                        session_label=_optional_string(turn, "sessionLabel"),
                        story_id=_optional_string(case, "storyId"),
                        story_title=_optional_string(case, "storyTitle"),
                        turn_index=(
                            _optional_int(turn, "turnIndex")
                            if turn.get("turnIndex") is not None
                            else _optional_int(case, "turnIndex")
                        ),
                        resume_from_case_id=(
                            _optional_string(turn, "resumeFromCaseId")
                            if turn.get("resumeFromCaseId") is not None
                            else _optional_string(case, "resumeFromCaseId")
                        ),
                        user_turn=str(turn["userTurn"]),
                        expected=dict(turn.get("expected", {})),
                        max_turns=(
                            _optional_int(turn, "maxTurns")
                            if turn.get("maxTurns") is not None
                            else _optional_int(case, "maxTurns")
                        ),
                        dataset_path=str(case["_dataset_path"]),
                        line_number=int(case["_line_number"]),
                    )
                )
            continue

        turn_specs.append(
            TurnSpec(
                case_id=str(case["caseId"]),
                turn_id=_optional_string(case, "turnId"),
                title=str(case.get("title", case["caseId"])),
                session_label=_optional_string(case, "sessionLabel"),
                story_id=_optional_string(case, "storyId"),
                story_title=_optional_string(case, "storyTitle"),
                turn_index=_optional_int(case, "turnIndex"),
                resume_from_case_id=_optional_string(case, "resumeFromCaseId"),
                user_turn=str(case["userTurn"]),
                expected=dict(case.get("expected", {})),
                max_turns=_optional_int(case, "maxTurns"),
                dataset_path=str(case["_dataset_path"]),
                line_number=int(case["_line_number"]),
            )
        )
    return turn_specs


def _validate_expected_regexes(
    turn_spec: TurnSpec, expected: dict[str, Any], field_name: str
) -> list[str]:
    errors: list[str] = []
    for pattern in expected.get(field_name, []):
        try:
            re.compile(str(pattern), REPLY_REGEX_FLAGS)
        except re.error as exc:
            errors.append(
                f"{turn_spec.location()} {turn_spec.display_id()}: invalid "
                f"{field_name} pattern {pattern!r}: {exc}"
            )
    return errors


def _validate_turn_spec(
    turn_spec: TurnSpec,
    *,
    case_order_by_id: dict[str, int],
) -> list[str]:
    errors: list[str] = []
    expected = turn_spec.expected
    if expected.get("toolSequencePrefix") and expected.get("allowedToolSequences"):
        errors.append(
            f"{turn_spec.location()} {turn_spec.display_id()}: "
            "toolSequencePrefix and allowedToolSequences are mutually exclusive"
        )
    errors.extend(_validate_expected_regexes(turn_spec, expected, "requiredReplyRegexes"))
    errors.extend(_validate_expected_regexes(turn_spec, expected, "forbiddenReplyRegexes"))
    if turn_spec.resume_from_case_id is not None:
        dependency_order = case_order_by_id.get(turn_spec.resume_from_case_id)
        if dependency_order is None:
            errors.append(
                f"{turn_spec.location()} {turn_spec.display_id()}: "
                f"resumeFromCaseId {turn_spec.resume_from_case_id!r} does not exist"
            )
        elif dependency_order >= case_order_by_id[turn_spec.case_id]:
            errors.append(
                f"{turn_spec.location()} {turn_spec.display_id()}: "
                "resumeFromCaseId must point to an earlier caseId"
            )
    return errors


def prepare_execution_turns(
    *, all_cases: list[dict[str, Any]], selected_cases: list[dict[str, Any]]
) -> list[TurnSpec]:
    case_order_by_id: dict[str, int] = {}
    case_location_by_id: dict[str, str] = {}
    errors: list[str] = []
    for case in all_cases:
        case_id = str(case.get("caseId", ""))
        location = f"{case['_dataset_path']}:{case['_line_number']}"
        if case_id in case_order_by_id:
            errors.append(
                f"duplicate caseId {case_id!r}: {case_location_by_id[case_id]} and {location}"
            )
            continue
        case_order_by_id[case_id] = int(case["_case_order"])
        case_location_by_id[case_id] = location
    turn_specs = normalize_execution_turns(selected_cases)
    for turn_spec in turn_specs:
        errors.extend(_validate_turn_spec(turn_spec, case_order_by_id=case_order_by_id))
    if errors:
        raise ValueError("Dataset preflight failed:\n- " + "\n- ".join(errors))
    return turn_specs


def _reply_matches_regex(pattern: str, text: str) -> bool:
    return re.search(pattern, text, REPLY_REGEX_FLAGS) is not None


def evaluate_expectations(
    *,
    expected: dict[str, Any],
    tool_calls: list[str],
    host_reply: str,
    timed_out: bool,
    return_code: int,
) -> list[str]:
    findings: list[str] = []
    allow_timeout = bool(expected.get("allowTimeout", False))
    if timed_out and not allow_timeout:
        findings.append("turn timed out")
    if return_code not in (0, 124):
        findings.append(f"hermes returned non-zero exit code {return_code}")

    prefix = [str(item) for item in expected.get("toolSequencePrefix", [])]
    if prefix and tool_calls[: len(prefix)] != prefix:
        findings.append(
            "tool sequence prefix mismatch: "
            f"expected {prefix}, got {tool_calls[: len(prefix)]}"
        )

    allowed_prefixes = [
        [str(tool_name) for tool_name in prefix_items]
        for prefix_items in expected.get("allowedToolSequencePrefixes", [])
        if isinstance(prefix_items, list)
    ]
    if allowed_prefixes and not any(
        tool_calls[: len(prefix_items)] == prefix_items for prefix_items in allowed_prefixes
    ):
        findings.append(
            "tool sequence did not match any allowed prefix: "
            f"allowed={allowed_prefixes}, got={tool_calls}"
        )

    allowed_sequences = [
        [str(tool_name) for tool_name in tool_sequence]
        for tool_sequence in expected.get("allowedToolSequences", [])
        if isinstance(tool_sequence, list)
    ]
    if allowed_sequences and tool_calls not in allowed_sequences:
        findings.append(
            "tool sequence did not match any allowed exact sequence: "
            f"allowed={allowed_sequences}, got={tool_calls}"
        )

    required_tools = [str(item) for item in expected.get("requiredTools", [])]
    for tool_name in required_tools:
        if tool_name not in tool_calls:
            findings.append(f"missing required tool {tool_name}")

    forbidden_tools = [str(item) for item in expected.get("forbiddenTools", [])]
    for tool_name in forbidden_tools:
        if tool_name in tool_calls:
            findings.append(f"forbidden tool called: {tool_name}")

    max_tool_occurrences = expected.get("maxToolOccurrences", {})
    if isinstance(max_tool_occurrences, dict):
        for tool_name, max_count in max_tool_occurrences.items():
            if not isinstance(max_count, int):
                continue
            actual_count = sum(1 for call in tool_calls if call == str(tool_name))
            if actual_count > max_count:
                findings.append(
                    f"tool called too often: {tool_name} {actual_count} > {max_count}"
                )

    for snippet in [str(item) for item in expected.get("requiredReplySubstrings", [])]:
        if snippet not in host_reply:
            findings.append(f"reply missing substring: {snippet}")

    for pattern in [str(item) for item in expected.get("requiredReplyRegexes", [])]:
        if not _reply_matches_regex(pattern, host_reply):
            findings.append(f"reply missing regex match: {pattern}")

    for snippet in [str(item) for item in expected.get("forbiddenReplySubstrings", [])]:
        if snippet in host_reply:
            findings.append(f"reply contains forbidden substring: {snippet}")

    for pattern in [str(item) for item in expected.get("forbiddenReplyRegexes", [])]:
        if _reply_matches_regex(pattern, host_reply):
            findings.append(f"reply matched forbidden regex: {pattern}")

    if bool(expected.get("noInternalLeak")) and _looks_like_internal_leak(host_reply):
        findings.append("visible host reply leaked internals")

    max_questions = expected.get("maxQuestions")
    if isinstance(max_questions, int) and _question_count(host_reply) > max_questions:
        findings.append(
            f"reply asked too many questions: {_question_count(host_reply)} > {max_questions}"
        )

    max_sentences = expected.get("maxSentences")
    if isinstance(max_sentences, int) and _sentence_count(host_reply) > max_sentences:
        findings.append(
            f"reply exceeded max sentences: {_sentence_count(host_reply)} > {max_sentences}"
        )

    max_chars = expected.get("maxReplyChars")
    if isinstance(max_chars, int) and len(host_reply) > max_chars:
        findings.append(f"reply exceeded max chars: {len(host_reply)} > {max_chars}")

    return findings


def run_turn(
    *,
    hermes_bin: str,
    toolset: str,
    max_turns: int,
    timeout_seconds: int,
    user_turn: str,
    resume_session_id: str | None,
) -> tuple[str | None, list[str], str, str, int, bool]:
    cmd = [
        hermes_bin,
        "chat",
        "-v",
        "-Q",
        "-t",
        toolset,
        "--max-turns",
        str(max_turns),
    ]
    if resume_session_id:
        cmd.extend(["--resume", resume_session_id])
    cmd.extend(["-q", user_turn])
    timed_out = False
    try:
        result = subprocess.run(
            cmd,
            cwd=REPO_ROOT,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            timeout=timeout_seconds,
        )
        return_code = result.returncode
        raw_output = sanitize_output(result.stdout or "")
    except subprocess.TimeoutExpired as exc:
        timed_out = True
        return_code = 124
        raw_output = sanitize_output(exc.stdout or "")
    session_id, host_reply = _extract_host_reply(raw_output)
    tool_calls = TOOL_CALL_RE.findall(raw_output)
    return session_id, tool_calls, host_reply, raw_output, return_code, timed_out


def resolve_resume_session_id(
    turn_spec: TurnSpec,
    *,
    sessions_by_label: dict[str, str],
    session_ids_by_case_id: dict[str, str],
) -> tuple[str | None, str | None]:
    if turn_spec.resume_from_case_id is not None:
        session_id = session_ids_by_case_id.get(turn_spec.resume_from_case_id)
        if session_id is None:
            return (
                None,
                "resume dependency unavailable: "
                f"case {turn_spec.resume_from_case_id} produced no session id in this run",
            )
        return session_id, None
    if turn_spec.session_label is None:
        return None, None
    return sessions_by_label.get(turn_spec.session_label), None


def short(text: str, limit: int = 220) -> str:
    collapsed = " ".join(text.split())
    if len(collapsed) <= limit:
        return collapsed
    return collapsed[: limit - 1] + "..."


def build_story_rollups(turn_results: list[TurnResult]) -> list[dict[str, Any]]:
    rollups_by_story_id: dict[str, dict[str, Any]] = {}
    story_order: list[str] = []
    for turn_result in turn_results:
        if turn_result.story_id is None:
            continue
        if turn_result.story_id not in rollups_by_story_id:
            story_order.append(turn_result.story_id)
            rollups_by_story_id[turn_result.story_id] = {
                "storyId": turn_result.story_id,
                "storyTitle": turn_result.story_title,
                "turnCount": 0,
                "passedTurnCount": 0,
                "failedTurnCount": 0,
                "caseIds": [],
            }
        rollup = rollups_by_story_id[turn_result.story_id]
        rollup["turnCount"] += 1
        if turn_result.passed:
            rollup["passedTurnCount"] += 1
        else:
            rollup["failedTurnCount"] += 1
        rollup["caseIds"].append(turn_result.case_id)
    story_rollups: list[dict[str, Any]] = []
    for story_id in story_order:
        rollup = dict(rollups_by_story_id[story_id])
        rollup["passed"] = rollup["failedTurnCount"] == 0
        story_rollups.append(rollup)
    return story_rollups


def _story_context_parts(
    *, story_id: str | None, turn_index: int | None
) -> list[str]:
    parts: list[str] = []
    if story_id is not None:
        parts.append(f"story={story_id}")
    if turn_index is not None:
        parts.append(f"turn={turn_index}")
    return parts


def render_markdown(summary: dict[str, Any]) -> str:
    lines = [
        "# Hermes Real Host Harness Report",
        "",
        f"- Run id: `{summary['runId']}`",
        f"- Cases: `{summary['caseCount']}`",
        f"- Turns: `{summary['turnCount']}`",
        f"- Passed: `{summary['passedTurnCount']}`",
        f"- Failed: `{summary['failedTurnCount']}`",
        "",
    ]
    story_summaries = summary.get("storySummaries", [])
    if story_summaries:
        lines.extend(["## Story Rollup", ""])
        for story in story_summaries:
            status = "PASS" if story["passed"] else "FAIL"
            title = story["storyTitle"] or story["storyId"]
            lines.extend(
                [
                    f"- `{story['storyId']}` [{status}] turns={story['turnCount']} "
                    f"passed={story['passedTurnCount']} failed={story['failedTurnCount']} "
                    f"title={title}",
                ]
            )
        lines.append("")
    for result in summary["results"]:
        status = "PASS" if result["passed"] else "FAIL"
        result_header = result["caseId"]
        if result["turnId"] is not None:
            result_header = f"{result_header} / {result['turnId']}"
        lines.extend([f"## {result_header} [{status}]", ""])
        if result["storyId"] is not None:
            lines.append(f"- Story: `{result['storyId']}`")
        if result["turnIndex"] is not None:
            lines.append(f"- Story turn: `{result['turnIndex']}`")
        lines.extend(
            [
                f"- Title: {result['title']}",
                f"- Session label: `{result['sessionLabel'] or 'none'}`",
                f"- Session id: `{result['sessionId'] or 'none'}`",
                f"- Executed: `{'yes' if result['executed'] else 'no'}`",
                f"- Tool calls: `{', '.join(result['toolCalls']) or '(none)'}`",
                f"- User turn: `{result['userTurn']}`",
                f"- Host reply: `{short(result['hostReply'], 320)}`",
            ]
        )
        findings = result.get("findings", [])
        if findings:
            lines.append("- Findings:")
            for finding in findings:
                lines.append(f"  - {finding}")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def main() -> int:
    args = parse_args()
    dataset_paths = args.dataset or [DEFAULT_DATASET]
    cases = load_cases(dataset_paths)
    selected_cases = filter_cases(
        cases,
        case_ids=set(args.case or []),
        split_filter=set(args.split or []),
        include_tags=set(args.include_tag or []),
        exclude_tags=set(args.exclude_tag or []),
    )
    if not selected_cases:
        print("No matching real-host harness cases.", file=sys.stderr)
        return 1
    try:
        turn_specs = prepare_execution_turns(all_cases=cases, selected_cases=selected_cases)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    if args.dry_run:
        for turn_spec in turn_specs:
            story_parts = _story_context_parts(
                story_id=turn_spec.story_id,
                turn_index=turn_spec.turn_index,
            )
            story_prefix = f"{' '.join(story_parts)} " if story_parts else ""
            split_value = next(
                (
                    case.get("split")
                    for case in selected_cases
                    if case["caseId"] == turn_spec.case_id
                ),
                None,
            )
            print(
                f"{story_prefix}{turn_spec.display_id()} split={split_value} "
                f"title={turn_spec.title}"
            )
        return 0

    run_id = f"hermes_real_host_{uuid.uuid4().hex[:10]}"
    sessions_by_label: dict[str, str] = {}
    session_ids_by_case_id: dict[str, str] = {}
    turn_results: list[TurnResult] = []
    trace_records: list[dict[str, Any]] = []

    for turn_spec in turn_specs:
        resume_session_id, dependency_finding = resolve_resume_session_id(
            turn_spec,
            sessions_by_label=sessions_by_label,
            session_ids_by_case_id=session_ids_by_case_id,
        )
        if dependency_finding is not None:
            turn_result = TurnResult(
                case_id=turn_spec.case_id,
                turn_id=turn_spec.turn_id,
                title=turn_spec.title,
                session_label=turn_spec.session_label,
                session_id=None,
                story_id=turn_spec.story_id,
                story_title=turn_spec.story_title,
                turn_index=turn_spec.turn_index,
                user_turn=turn_spec.user_turn,
                tool_calls=[],
                host_reply="",
                findings=[dependency_finding],
                passed=False,
                timed_out=False,
                return_code=0,
                raw_output="",
                executed=False,
            )
        else:
            session_id, tool_calls, host_reply, raw_output, return_code, timed_out = run_turn(
                hermes_bin=args.hermes_bin,
                toolset=args.toolset,
                max_turns=turn_spec.max_turns or args.max_turns,
                timeout_seconds=args.timeout_seconds,
                user_turn=turn_spec.user_turn,
                resume_session_id=resume_session_id,
            )
            if turn_spec.session_label is not None and session_id is not None:
                sessions_by_label[turn_spec.session_label] = session_id
            if session_id is not None:
                session_ids_by_case_id[turn_spec.case_id] = session_id
            findings = evaluate_expectations(
                expected=turn_spec.expected,
                tool_calls=tool_calls,
                host_reply=host_reply,
                timed_out=timed_out,
                return_code=return_code,
            )
            turn_result = TurnResult(
                case_id=turn_spec.case_id,
                turn_id=turn_spec.turn_id,
                title=turn_spec.title,
                session_label=turn_spec.session_label,
                session_id=session_id,
                story_id=turn_spec.story_id,
                story_title=turn_spec.story_title,
                turn_index=turn_spec.turn_index,
                user_turn=turn_spec.user_turn,
                tool_calls=tool_calls,
                host_reply=host_reply,
                findings=findings,
                passed=not findings,
                timed_out=timed_out,
                return_code=return_code,
                raw_output=raw_output,
                executed=True,
            )

        turn_results.append(turn_result)
        trace_records.append(
            {
                "caseId": turn_result.case_id,
                "turnId": turn_result.turn_id,
                "sessionLabel": turn_result.session_label,
                "sessionId": turn_result.session_id,
                "storyId": turn_result.story_id,
                "turnIndex": turn_result.turn_index,
                "toolCalls": turn_result.tool_calls,
                "passed": turn_result.passed,
                "executed": turn_result.executed,
                "rawOutput": turn_result.raw_output,
            }
        )
        status = "PASS" if turn_result.passed else "FAIL"
        story_parts = _story_context_parts(
            story_id=turn_result.story_id,
            turn_index=turn_result.turn_index,
        )
        story_prefix = f"{' '.join(story_parts)} " if story_parts else ""
        print(
            f"[{status}] {story_prefix}{turn_result.display_id()} "
            f"tools={','.join(turn_result.tool_calls) or '(none)'} "
            f"reply={short(turn_result.host_reply)}"
        )
        for finding in turn_result.findings:
            print(f"  - {finding}")

    story_rollups = build_story_rollups(turn_results)
    summary = {
        "runId": run_id,
        "datasetPaths": [str(path) for path in dataset_paths],
        "caseCount": len(selected_cases),
        "turnCount": len(turn_results),
        "passedTurnCount": sum(1 for item in turn_results if item.passed),
        "failedTurnCount": sum(1 for item in turn_results if not item.passed),
        "storyCount": len(story_rollups),
        "passedStoryCount": sum(1 for item in story_rollups if item["passed"]),
        "failedStoryCount": sum(1 for item in story_rollups if not item["passed"]),
        "storySummaries": story_rollups,
        "results": [item.to_summary_dict() for item in turn_results],
    }

    print(
        "Summary: "
        f"cases={summary['caseCount']} turns={summary['turnCount']} "
        f"passed={summary['passedTurnCount']} failed={summary['failedTurnCount']}"
    )
    for story_rollup in story_rollups:
        status = "PASS" if story_rollup["passed"] else "FAIL"
        title = story_rollup["storyTitle"] or story_rollup["storyId"]
        print(
            f"[STORY {status}] {story_rollup['storyId']} "
            f"turns={story_rollup['turnCount']} "
            f"passed={story_rollup['passedTurnCount']} "
            f"failed={story_rollup['failedTurnCount']} "
            f"title={title}"
        )

    if args.report_json is not None:
        args.report_json.parent.mkdir(parents=True, exist_ok=True)
        args.report_json.write_text(
            json.dumps(summary, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
    if args.report_md is not None:
        args.report_md.parent.mkdir(parents=True, exist_ok=True)
        args.report_md.write_text(render_markdown(summary), encoding="utf-8")
    if args.trace_jsonl is not None:
        args.trace_jsonl.parent.mkdir(parents=True, exist_ok=True)
        args.trace_jsonl.write_text(
            "".join(json.dumps(item, ensure_ascii=False) + "\n" for item in trace_records),
            encoding="utf-8",
        )

    return 1 if args.strict and summary["failedTurnCount"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
