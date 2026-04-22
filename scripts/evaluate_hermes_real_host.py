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


@dataclass
class TurnResult:
    case_id: str
    turn_id: str
    title: str
    session_label: str | None
    session_id: str | None
    user_turn: str
    tool_calls: list[str]
    host_reply: str
    findings: list[str]
    passed: bool
    timed_out: bool
    return_code: int
    raw_output: str

    def to_summary_dict(self) -> dict[str, Any]:
        return {
            "caseId": self.case_id,
            "turnId": self.turn_id,
            "title": self.title,
            "sessionLabel": self.session_label,
            "sessionId": self.session_id,
            "userTurn": self.user_turn,
            "toolCalls": self.tool_calls,
            "hostReply": self.host_reply,
            "findings": self.findings,
            "passed": self.passed,
            "timedOut": self.timed_out,
            "returnCode": self.return_code,
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


def sanitize_output(text: str) -> str:
    text = ANSI_RE.sub("", text)
    text = text.replace("\r", "\n").replace("\x00", "")
    text = text.replace("\u001b[2004h", "").replace("\u001b[2004l", "")
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def load_cases(dataset_paths: list[Path]) -> list[dict[str, Any]]:
    cases: list[dict[str, Any]] = []
    for dataset_path in dataset_paths:
        raw = dataset_path.read_text(encoding="utf-8")
        for line_number, line in enumerate(raw.splitlines(), start=1):
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue
            payload = json.loads(stripped)
            payload["_dataset_path"] = str(dataset_path)
            payload["_line_number"] = line_number
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
    required_tools = [str(item) for item in expected.get("requiredTools", [])]
    for tool_name in required_tools:
        if tool_name not in tool_calls:
            findings.append(f"missing required tool {tool_name}")
    forbidden_tools = [str(item) for item in expected.get("forbiddenTools", [])]
    for tool_name in forbidden_tools:
        if tool_name in tool_calls:
            findings.append(f"forbidden tool called: {tool_name}")
    for snippet in [str(item) for item in expected.get("requiredReplySubstrings", [])]:
        if snippet not in host_reply:
            findings.append(f"reply missing substring: {snippet}")
    for snippet in [str(item) for item in expected.get("forbiddenReplySubstrings", [])]:
        if snippet in host_reply:
            findings.append(f"reply contains forbidden substring: {snippet}")
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


def short(text: str, limit: int = 220) -> str:
    collapsed = " ".join(text.split())
    if len(collapsed) <= limit:
        return collapsed
    return collapsed[: limit - 1] + "..."


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
    for result in summary["results"]:
        status = "PASS" if result["passed"] else "FAIL"
        lines.extend(
            [
                f"## {result['caseId']} / {result['turnId']} [{status}]",
                "",
                f"- Title: {result['title']}",
                f"- Session label: `{result['sessionLabel'] or 'none'}`",
                f"- Session id: `{result['sessionId'] or 'none'}`",
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
    if args.dry_run:
        for case in selected_cases:
            print(
                f"{case['caseId']} split={case.get('split')} "
                f"turns={len(case.get('turns', []))} title={case.get('title')}"
            )
        return 0

    run_id = f"hermes_real_host_{uuid.uuid4().hex[:10]}"
    sessions_by_label: dict[str, str] = {}
    turn_results: list[TurnResult] = []
    trace_records: list[dict[str, Any]] = []

    for case in selected_cases:
        title = str(case.get("title", case.get("caseId", "untitled")))
        for turn in case.get("turns", []):
            session_label = turn.get("sessionLabel")
            resume_session_id = (
                sessions_by_label.get(str(session_label)) if session_label is not None else None
            )
            session_id, tool_calls, host_reply, raw_output, return_code, timed_out = run_turn(
                hermes_bin=args.hermes_bin,
                toolset=args.toolset,
                max_turns=int(turn.get("maxTurns", args.max_turns)),
                timeout_seconds=args.timeout_seconds,
                user_turn=str(turn["userTurn"]),
                resume_session_id=resume_session_id,
            )
            if session_label is not None and session_id is not None:
                sessions_by_label[str(session_label)] = session_id
            expected = dict(turn.get("expected", {}))
            findings = evaluate_expectations(
                expected=expected,
                tool_calls=tool_calls,
                host_reply=host_reply,
                timed_out=timed_out,
                return_code=return_code,
            )
            turn_result = TurnResult(
                case_id=str(case["caseId"]),
                turn_id=str(turn["turnId"]),
                title=title,
                session_label=str(session_label) if session_label is not None else None,
                session_id=session_id,
                user_turn=str(turn["userTurn"]),
                tool_calls=tool_calls,
                host_reply=host_reply,
                findings=findings,
                passed=not findings,
                timed_out=timed_out,
                return_code=return_code,
                raw_output=raw_output,
            )
            turn_results.append(turn_result)
            trace_records.append(
                {
                    "caseId": turn_result.case_id,
                    "turnId": turn_result.turn_id,
                    "sessionLabel": turn_result.session_label,
                    "sessionId": turn_result.session_id,
                    "toolCalls": turn_result.tool_calls,
                    "passed": turn_result.passed,
                    "rawOutput": turn_result.raw_output,
                }
            )
            status = "PASS" if turn_result.passed else "FAIL"
            print(
                f"[{status}] {turn_result.case_id}/{turn_result.turn_id} "
                f"tools={','.join(turn_result.tool_calls) or '(none)'} "
                f"reply={short(turn_result.host_reply)}"
            )
            for finding in findings:
                print(f"  - {finding}")

    summary = {
        "runId": run_id,
        "datasetPaths": [str(path) for path in dataset_paths],
        "caseCount": len(selected_cases),
        "turnCount": len(turn_results),
        "passedTurnCount": sum(1 for item in turn_results if item.passed),
        "failedTurnCount": sum(1 for item in turn_results if not item.passed),
        "results": [item.to_summary_dict() for item in turn_results],
    }

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
