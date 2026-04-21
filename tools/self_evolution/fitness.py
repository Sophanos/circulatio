from __future__ import annotations

import json
from collections.abc import Callable, Mapping
from dataclasses import asdict, dataclass, field


@dataclass
class CaseResult:
    case_id: str
    dataset: str
    split: str
    severity: str
    gate_type: str
    score: int
    max_score: int
    passed: bool
    findings: list[str] = field(default_factory=list)
    result_kind: str = "deterministic"
    candidate_id: str | None = None
    trace_ids: list[str] = field(default_factory=list)
    signals: dict[str, object] = field(default_factory=dict)

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


def _normalize_text(value: object) -> str:
    return " ".join(str(value).split()).lower()


def _contains(haystack: object, needle: object) -> bool:
    return _normalize_text(needle) in _normalize_text(haystack)


def _payload_path(payload: object, dotted_path: str) -> object:
    current: object = payload
    for segment in dotted_path.split("."):
        if not isinstance(current, dict) or segment not in current:
            return None
        current = current[segment]
    return current


def _object_mapping(value: object) -> dict[str, object]:
    if not isinstance(value, Mapping):
        return {}
    return {str(key): item for key, item in value.items()}


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


def _listify(value: object) -> list[object]:
    if isinstance(value, list):
        return list(value)
    return []


def _case_meta(case: dict[str, object]) -> dict[str, str]:
    return {
        "case_id": str(case.get("caseId") or ""),
        "dataset": str(case.get("_dataset") or ""),
        "split": str(case.get("split") or "dev"),
        "severity": str(case.get("severity") or "blocking"),
        "gate_type": str(case.get("gateType") or "deterministic"),
    }


def _collection_length(value: object) -> int | None:
    if isinstance(value, (str, list, tuple, dict, set)):
        return len(value)
    return None


def _matches_path_expectation(actual: object, expectation: object) -> tuple[bool, str | None]:
    if isinstance(expectation, Mapping):
        expectation_map = _object_mapping(expectation)
        if expectation_map.get("present") is True and actual is None:
            return False, "expected value to be present"
        if expectation_map.get("nonEmpty") is True:
            if actual in (None, "", [], {}, ()):  # pragma: no branch - explicit shapes only
                return False, "expected value to be non-empty"
        if "equals" in expectation_map and actual != expectation_map["equals"]:
            return False, f"expected {expectation_map['equals']!r}"
        if "oneOf" in expectation_map:
            allowed = _listify(expectation_map.get("oneOf"))
            if actual not in allowed:
                return False, f"expected one of {allowed!r}"
        if "contains" in expectation_map and not _contains(actual, expectation_map["contains"]):
            return False, f"expected text containing {expectation_map['contains']!r}"
        if "notContains" in expectation_map and _contains(actual, expectation_map["notContains"]):
            return False, f"expected text without {expectation_map['notContains']!r}"
        if "minLength" in expectation_map:
            actual_length = _collection_length(actual)
            min_length = int(expectation_map["minLength"])
            if actual_length is None or actual_length < min_length:
                return False, f"expected length >= {min_length}"
        if "maxLength" in expectation_map:
            actual_length = _collection_length(actual)
            max_length = int(expectation_map["maxLength"])
            if actual_length is None or actual_length > max_length:
                return False, f"expected length <= {max_length}"
        return True, None
    if actual != expectation:
        return False, f"expected {expectation!r}"
    return True, None


def _evaluate_path_expectations(
    *,
    check: Callable[[bool, str], None],
    payload: object,
    expectations: Mapping[str, object],
    label: str,
) -> None:
    for dotted_path, expected_value in expectations.items():
        actual = _payload_path(payload, dotted_path)
        passed, detail = _matches_path_expectation(actual, expected_value)
        message = (
            f"{label} path {dotted_path} "
            f"{detail or 'did not match expectation'}; found {actual!r}."
        )
        check(passed, message)


def evaluate_prompt_case(case: dict[str, object], messages: list[dict[str, str]]) -> CaseResult:
    findings: list[str] = []
    score = 0
    max_score = 0

    def check(condition: bool, message: str) -> None:
        nonlocal score, max_score
        max_score += 1
        if condition:
            score += 1
        else:
            findings.append(message)

    system_text = messages[0]["content"]
    user_text = messages[1]["content"]
    payload = json.loads(user_text)
    instructions = payload.get("instructions") if isinstance(payload, dict) else None
    meta = _case_meta(case)

    for key in _string_list(case.get("requiredInstructionKeys")):
        key_text = str(key)
        check(
            isinstance(instructions, dict) and bool(str(instructions.get(key_text) or "").strip()),
            f"Missing non-empty instructions.{key_text}.",
        )

    for key, values in _string_mapping_of_lists(case.get("requiredInstructionSubstrings")).items():
        instruction_text = ""
        if isinstance(instructions, dict):
            instruction_text = str(instructions.get(str(key)) or "")
        for value in values:
            phrase = str(value)
            check(
                _contains(instruction_text, phrase),
                f"instructions.{key} is missing required text: {phrase}",
            )

    for phrase in _string_list(case.get("requiredSystemSubstrings")):
        required = str(phrase)
        check(
            _contains(system_text, required),
            f"System prompt is missing required text: {required}",
        )

    for phrase in _string_list(case.get("requiredUserSubstrings")):
        required = str(phrase)
        check(
            _contains(user_text, required),
            f"User payload is missing required text: {required}",
        )

    combined = f"{system_text}\n{user_text}"
    for phrase in _string_list(case.get("forbiddenSubstrings")):
        forbidden = str(phrase)
        check(
            not _contains(combined, forbidden),
            f"Prompt includes forbidden text: {forbidden}",
        )

    _evaluate_path_expectations(
        check=check,
        payload=payload,
        expectations=_object_mapping(case.get("expectedPayloadPaths")),
        label="Payload",
    )
    _evaluate_path_expectations(
        check=check,
        payload=payload,
        expectations=_object_mapping(case.get("expectedJsonPaths")),
        label="JSON",
    )

    return CaseResult(
        case_id=meta["case_id"],
        dataset=meta["dataset"],
        split=meta["split"],
        severity=meta["severity"],
        gate_type=meta["gate_type"],
        score=score,
        max_score=max_score,
        passed=score == max_score,
        findings=findings,
    )


def evaluate_skill_case(case: dict[str, object], skill_text: str) -> CaseResult:
    findings: list[str] = []
    score = 0
    max_score = 0
    meta = _case_meta(case)

    def check(condition: bool, message: str) -> None:
        nonlocal score, max_score
        max_score += 1
        if condition:
            score += 1
        else:
            findings.append(message)

    for phrase in _string_list(case.get("requiredSubstrings")):
        required = str(phrase)
        check(
            _contains(skill_text, required),
            f"Skill text is missing required text: {required}",
        )

    for phrase in _string_list(case.get("forbiddenSubstrings")):
        forbidden = str(phrase)
        check(
            not _contains(skill_text, forbidden),
            f"Skill text includes forbidden text: {forbidden}",
        )

    max_bytes = case.get("maxBytes")
    if isinstance(max_bytes, int):
        check(
            len(skill_text.encode("utf-8")) <= max_bytes,
            f"Skill text exceeds maxBytes={max_bytes}.",
        )

    return CaseResult(
        case_id=meta["case_id"],
        dataset=meta["dataset"],
        split=meta["split"],
        severity=meta["severity"],
        gate_type=meta["gate_type"],
        score=score,
        max_score=max_score,
        passed=score == max_score,
        findings=findings,
    )


def evaluate_tool_description_case(
    case: dict[str, object],
    tool_schemas: list[dict[str, object]],
) -> CaseResult:
    findings: list[str] = []
    score = 0
    max_score = 0
    meta = _case_meta(case)

    def check(condition: bool, message: str) -> None:
        nonlocal score, max_score
        max_score += 1
        if condition:
            score += 1
        else:
            findings.append(message)

    tool_name = str(case.get("toolName") or "")
    by_name = {str(schema.get("name") or ""): schema for schema in tool_schemas}
    schema = by_name.get(tool_name)
    description = str(schema.get("description") or "") if isinstance(schema, dict) else ""
    check(schema is not None, f"Tool schema '{tool_name}' was not found.")
    if schema is not None:
        for phrase in _string_list(case.get("requiredSubstrings")):
            required = str(phrase)
            check(
                _contains(description, required),
                f"Description for {tool_name} is missing required text: {required}",
            )
        for phrase in _string_list(case.get("forbiddenSubstrings")):
            forbidden = str(phrase)
            check(
                not _contains(description, forbidden),
                f"Description for {tool_name} includes forbidden text: {forbidden}",
            )
        max_description_chars = case.get("maxDescriptionChars")
        if isinstance(max_description_chars, int):
            check(
                len(description) <= max_description_chars,
                f"Description for {tool_name} exceeds {max_description_chars} characters.",
            )

    return CaseResult(
        case_id=meta["case_id"],
        dataset=meta["dataset"],
        split=meta["split"],
        severity=meta["severity"],
        gate_type=meta["gate_type"],
        score=score,
        max_score=max_score,
        passed=score == max_score,
        findings=findings,
    )


def evaluate_execution_output_case(
    case: dict[str, object],
    payload: dict[str, object],
    *,
    candidate_id: str | None = None,
    trace_id: str | None = None,
    text: str | None = None,
    result_kind: str = "execution",
    signals: dict[str, object] | None = None,
) -> CaseResult:
    findings: list[str] = []
    score = 0
    max_score = 0
    meta = _case_meta(case)
    serialized = text or json.dumps(payload, sort_keys=True, default=str)

    def check(condition: bool, message: str) -> None:
        nonlocal score, max_score
        max_score += 1
        if condition:
            score += 1
        else:
            findings.append(message)

    for phrase in _string_list(case.get("requiredSubstrings")):
        required = str(phrase)
        check(
            _contains(serialized, required),
            f"Execution output is missing required text: {required}",
        )
    for phrase in _string_list(case.get("forbiddenSubstrings")):
        forbidden = str(phrase)
        check(
            not _contains(serialized, forbidden),
            f"Execution output includes forbidden text: {forbidden}",
        )
    _evaluate_path_expectations(
        check=check,
        payload=payload,
        expectations=_object_mapping(case.get("expectedJsonPaths")),
        label="Output",
    )
    return CaseResult(
        case_id=meta["case_id"],
        dataset=meta["dataset"],
        split=meta["split"],
        severity=meta["severity"],
        gate_type=meta["gate_type"],
        score=score,
        max_score=max_score,
        passed=score == max_score,
        findings=findings,
        result_kind=result_kind,
        candidate_id=candidate_id,
        trace_ids=[trace_id] if trace_id else [],
        signals=signals or {},
    )


def build_advisory_case_result(
    case: dict[str, object],
    *,
    score: int,
    max_score: int,
    findings: list[str],
    candidate_id: str | None = None,
    trace_id: str | None = None,
    signals: dict[str, object] | None = None,
) -> CaseResult:
    meta = _case_meta(case)
    return CaseResult(
        case_id=meta["case_id"],
        dataset=meta["dataset"],
        split=meta["split"],
        severity=meta["severity"],
        gate_type=meta["gate_type"],
        score=score,
        max_score=max_score,
        passed=not findings,
        findings=findings,
        result_kind="judge",
        candidate_id=candidate_id,
        trace_ids=[trace_id] if trace_id else [],
        signals=signals or {},
    )
