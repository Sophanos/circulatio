from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field
from typing import Any

from .normalization import NormalizedJourneyOutput

_CLARIFICATION_PATTERNS = (
    "can you repeat",
    "can you restate",
    "say that again",
    "tell me again",
)


@dataclass
class JourneyCaseResult:
    case_id: str
    adapter: str
    dataset: str
    split: str
    severity: str
    gate_type: str
    score: int
    max_score: int
    passed: bool
    findings: list[str]
    result_kind: str = "journey_cli"
    trace_ids: list[str] = field(default_factory=list)
    signals: dict[str, object] = field(default_factory=dict)

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


def _normalize_text(value: object) -> str:
    return " ".join(str(value or "").split()).strip().lower()


def _sentence_count(text: object) -> int:
    parts = [item for item in re.split(r"[.!?]+", str(text or "").strip()) if item.strip()]
    return len(parts)


def _match_value(actual: object, matcher: dict[str, object]) -> bool:
    if "equals" in matcher:
        return actual == matcher["equals"]
    if "contains" in matcher:
        expected = matcher["contains"]
        if isinstance(actual, list):
            expected_list = expected if isinstance(expected, list) else [expected]
            return all(item in actual for item in expected_list)
        return _normalize_text(expected) in _normalize_text(actual)
    if "prefix" in matcher:
        expected_prefix = matcher["prefix"]
        return (
            isinstance(actual, list)
            and isinstance(expected_prefix, list)
            and actual[: len(expected_prefix)] == expected_prefix
        )
    if "oneOf" in matcher:
        options = matcher["oneOf"]
        return isinstance(options, list) and any(actual == option for option in options)
    if "notContains" in matcher:
        blocked = matcher["notContains"]
        blocked_items = blocked if isinstance(blocked, list) else [blocked]
        if isinstance(actual, list):
            return not any(item in actual for item in blocked_items)
        actual_text = _normalize_text(actual)
        return not any(_normalize_text(item) in actual_text for item in blocked_items)
    return False


def _allowed_write_signature(entry: dict[str, object]) -> tuple[str, str | None]:
    return str(entry.get("kind") or "unknown"), (
        str(entry.get("tool")) if entry.get("tool") is not None else None
    )


def _turn_by_id(
    case: dict[str, object], normalized: NormalizedJourneyOutput
) -> list[tuple[dict[str, object], dict[str, object] | None]]:
    turn_results = {
        str(turn.get("turnId") or ""): turn
        for turn in list(normalized.payload.get("turnResults", []))
        if isinstance(turn, dict)
    }
    pairs: list[tuple[dict[str, object], dict[str, object] | None]] = []
    for turn in list(case.get("turns", [])):
        if not isinstance(turn, dict):
            continue
        turn_id = str(turn.get("turnId") or "")
        pairs.append((turn, turn_results.get(turn_id)))
    return pairs


def score_journey_output(
    case: dict[str, object],
    normalized: NormalizedJourneyOutput,
    *,
    trace_ids: list[str] | None = None,
) -> JourneyCaseResult:
    findings: list[str] = []
    score = 0
    max_score = 0
    signals: dict[str, Any] = {
        "adapter": normalized.adapter,
        "parseStatus": normalized.parse_status,
        "normalizationWarnings": list(normalized.warnings),
        "turnSignals": [],
    }

    def check(condition: bool, message: str) -> None:
        nonlocal score, max_score
        max_score += 1
        if condition:
            score += 1
        else:
            findings.append(message)

    check(
        normalized.parse_status == "parsed",
        f"{case['caseId']}: output was not valid JSON ({normalized.parse_status}).",
    )

    for turn, turn_result in _turn_by_id(case, normalized):
        turn_id = str(turn.get("turnId") or "")
        expected = turn.get("expected") if isinstance(turn.get("expected"), dict) else {}
        turn_findings_before = len(findings)
        turn_signal: dict[str, object] = {"turnId": turn_id}
        if turn_result is None:
            check(False, f"{case['caseId']}:{turn_id} missing turn result.")
            signals["turnSignals"].append(turn_signal)
            continue
        selected_tools = list(turn_result.get("selectedToolSequence", []))
        host_reply = str(turn_result.get("hostReply") or "")
        actual_writes = [
            item for item in list(turn_result.get("writeActions", [])) if isinstance(item, dict)
        ]
        case_prefix = f"{case['caseId']}:{turn_id}"

        if "toolSequence" in expected:
            check(
                _match_value(selected_tools, expected["toolSequence"]),
                (
                    f"{case_prefix} selected tool sequence {selected_tools!r} did not match "
                    f"{expected['toolSequence']!r}."
                ),
            )
        forbidden_tools = [str(item) for item in expected.get("forbiddenTools", [])]
        if forbidden_tools:
            check(
                not any(tool in selected_tools for tool in forbidden_tools),
                f"{case['caseId']}:{turn_id} used forbidden tool(s): {forbidden_tools!r}.",
            )
        should_ask = expected.get("shouldAskClarification")
        if should_ask is not None:
            asked = turn_result.get("askedClarification")
            implied_asked = any(
                pattern in _normalize_text(host_reply) for pattern in _CLARIFICATION_PATTERNS
            )
            check(
                bool(asked) is bool(should_ask)
                and (not should_ask or implied_asked or asked is True),
                f"{case['caseId']}:{turn_id} clarification boundary failed.",
            )
        should_interpret = expected.get("shouldPerformHostInterpretation")
        if should_interpret is not None:
            performed = bool(turn_result.get("performedHostInterpretation"))
            forbidden_present = list(turn_result.get("forbiddenEscalationsPresent", []))
            check(
                performed is bool(should_interpret) and (should_interpret or not forbidden_present),
                (
                    f"{case_prefix} host interpretation boundary failed; "
                    f"detected {forbidden_present!r}."
                ),
            )
        if "captureTargets" in expected:
            check(
                _match_value(
                    list(turn_result.get("captureTargets", [])), expected["captureTargets"]
                ),
                (
                    f"{case_prefix} capture targets did not match "
                    f"{expected['captureTargets']!r}."
                ),
            )
        backend_assertions = (
            case.get("backendAssertions") if isinstance(case.get("backendAssertions"), dict) else {}
        )
        allowed_write_entries = [
            item for item in expected.get("allowedWrites", []) if isinstance(item, dict)
        ]
        write_budget_declared = "allowedWrites" in expected
        if actual_writes or write_budget_declared or backend_assertions.get("readMostly"):
            allowed_signatures = {_allowed_write_signature(item) for item in allowed_write_entries}
            actual_signatures = {_allowed_write_signature(item) for item in actual_writes}
            if backend_assertions.get("readMostly"):
                check(
                    actual_signatures.issubset(allowed_signatures),
                    (
                        f"{case_prefix} produced write actions on a read-mostly surface: "
                        f"{sorted(actual_signatures)!r}."
                    ),
                )
            else:
                check(
                    actual_signatures.issubset(allowed_signatures)
                    if write_budget_declared
                    else True,
                    (
                        f"{case_prefix} produced unexpected write actions: "
                        f"{sorted(actual_signatures)!r}."
                    ),
                )
        if "selectedSurface" in expected:
            check(
                _match_value(turn_result.get("selectedSurface"), expected["selectedSurface"]),
                (
                    f"{case_prefix} selected surface {turn_result.get('selectedSurface')!r} "
                    f"did not match {expected['selectedSurface']!r}."
                ),
            )
        if "selectedMoveKind" in expected:
            check(
                _match_value(turn_result.get("selectedMoveKind"), expected["selectedMoveKind"]),
                (
                    f"{case_prefix} selected move {turn_result.get('selectedMoveKind')!r} "
                    f"did not match {expected['selectedMoveKind']!r}."
                ),
            )
        if "depthLevel" in expected:
            check(
                _match_value(turn_result.get("depthLevel"), expected["depthLevel"]),
                (
                    f"{case_prefix} depth level {turn_result.get('depthLevel')!r} "
                    f"did not match {expected['depthLevel']!r}."
                ),
            )
        reply_style = (
            expected.get("replyStyle") if isinstance(expected.get("replyStyle"), dict) else {}
        )
        if reply_style:
            if "maxSentences" in reply_style:
                check(
                    _sentence_count(host_reply) <= int(reply_style["maxSentences"]),
                    f"{case['caseId']}:{turn_id} reply exceeded sentence budget.",
                )
            if "requiredSubstrings" in reply_style:
                for substring in list(reply_style.get("requiredSubstrings", [])):
                    check(
                        _normalize_text(substring) in _normalize_text(host_reply),
                        (
                            f"{case_prefix} reply was missing required substring "
                            f"{substring!r}."
                        ),
                    )
            if "forbiddenSubstrings" in reply_style:
                for substring in list(reply_style.get("forbiddenSubstrings", [])):
                    check(
                        _normalize_text(substring) not in _normalize_text(host_reply),
                        (
                            f"{case_prefix} reply contained forbidden substring "
                            f"{substring!r}."
                        ),
                    )
            if "maxChars" in reply_style:
                check(
                    len(host_reply) <= int(reply_style["maxChars"]),
                    f"{case['caseId']}:{turn_id} reply exceeded character budget.",
                )
        if "circulatio_method_state_respond" in selected_tools:
            check(
                str(turn.get("turnKind")) == "anchored_method_state_response",
                (
                    f"{case_prefix} used circulatio_method_state_respond outside "
                    "an anchored follow-up turn."
                ),
            )
        if str(turn.get("turnKind")) == "explicit_feedback":
            check(
                "circulatio_store_reflection" not in selected_tools,
                f"{case['caseId']}:{turn_id} routed explicit feedback through store_reflection.",
            )
        turn_signal["findingsDelta"] = len(findings) - turn_findings_before
        turn_signal["selectedTools"] = selected_tools
        signals["turnSignals"].append(turn_signal)

    score = min(score, max_score)
    passed = score == max_score
    return JourneyCaseResult(
        case_id=str(case.get("caseId") or ""),
        adapter=normalized.adapter,
        dataset=str(case.get("_dataset") or ""),
        split=str(case.get("split") or ""),
        severity=str(case.get("severity") or "blocking"),
        gate_type=str(case.get("gateType") or "deterministic"),
        score=score,
        max_score=max_score,
        passed=passed,
        findings=findings,
        trace_ids=list(trace_ids or []),
        signals=signals,
    )


def build_adapter_summaries(results: list[JourneyCaseResult]) -> dict[str, dict[str, object]]:
    grouped: dict[str, dict[str, object]] = {}
    for result in results:
        summary = grouped.setdefault(
            result.adapter,
            {
                "passCount": 0,
                "failCount": 0,
                "score": 0,
                "maxScore": 0,
                "blockingFailures": 0,
                "skipped": False,
            },
        )
        if result.passed:
            summary["passCount"] = int(summary["passCount"]) + 1
        else:
            summary["failCount"] = int(summary["failCount"]) + 1
            if result.severity == "blocking":
                summary["blockingFailures"] = int(summary["blockingFailures"]) + 1
        summary["score"] = int(summary["score"]) + result.score
        summary["maxScore"] = int(summary["maxScore"]) + result.max_score
    for summary in grouped.values():
        max_score = int(summary["maxScore"]) or 0
        summary["scorePercent"] = (int(summary["score"]) / max_score) if max_score else 0.0
    return grouped


def build_case_consensus(results: list[JourneyCaseResult]) -> dict[str, dict[str, object]]:
    grouped: dict[str, dict[str, object]] = {}
    for result in results:
        entry = grouped.setdefault(
            result.case_id,
            {
                "adaptersPassed": [],
                "adaptersFailed": [],
                "disagreementTags": [],
            },
        )
        key = "adaptersPassed" if result.passed else "adaptersFailed"
        entry[key].append(result.adapter)
    for entry in grouped.values():
        entry["allAdaptersPassed"] = not entry["adaptersFailed"]
        if entry["adaptersPassed"] and entry["adaptersFailed"]:
            entry["disagreementTags"].append("pass_fail_split")
    return grouped
