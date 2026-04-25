from __future__ import annotations

import json
from collections.abc import Iterable, Sequence
from pathlib import Path

from tools.self_evolution.dataset_builder import load_jsonl_cases

SCHEMA_PATH = (
    Path(__file__).resolve().parents[2]
    / "tests"
    / "evals"
    / "journey_cli"
    / "schema"
    / "journey_case.schema.json"
)

_TOP_LEVEL_FIELDS = {
    "schemaVersion",
    "caseId",
    "title",
    "journeyFamily",
    "caseKind",
    "assertionKinds",
    "split",
    "severity",
    "gateType",
    "tags",
    "testLayers",
    "historySeed",
    "turns",
    "backendAssertions",
    "methodEvalFeedback",
    "notes",
    "targetKinds",
    "_dataset",
    "_datasetPath",
}
_FAMILIES = {
    "EmbodiedRecurrence",
    "SymbolBodyPressure",
    "ThoughtLoopTypology",
    "RelationalSceneRecurrence",
    "PracticeReentry",
    "CrossFamilyUmbrella",
}
_CASE_KINDS = {
    "single_turn_route",
    "multi_turn_story",
    "read_mostly_surface",
    "anchored_followup",
    "feedback_route",
    "practice_adaptation",
    "consent_boundary",
    "host_smoke_reference",
}
_ASSERTION_KINDS = {
    "route",
    "no_host_interpretation",
    "write_budget",
    "read_mostly",
    "consent_gate",
    "grounding_gate",
    "capture_target",
    "surface_shape",
    "reply_style",
    "backend_invariant",
    "bridge_invariant",
}
_TURN_KINDS = {
    "ambient_intake",
    "explicit_interpretation_request",
    "explicit_surface_request",
    "anchored_method_state_response",
    "explicit_feedback",
    "practice_response",
    "return_after_absence",
    "artifact_completion",
    "scheduled_cron",
}
_TEST_LAYERS = {
    "cli_comparison",
    "backend",
    "hermes_bridge",
    "method_eval",
    "real_host_smoke",
}
_MATCH_KEYS = {"equals", "contains", "prefix", "oneOf", "notContains"}
_TURN_EXPECTED_FIELDS = {
    "toolSequence",
    "selectedSurface",
    "selectedMoveKind",
    "depthLevel",
    "captureTargets",
    "allowedWrites",
    "forbiddenTools",
    "forbiddenEscalations",
    "shouldAskClarification",
    "shouldPerformHostInterpretation",
    "replyStyle",
}
_BACKEND_ASSERTION_FIELDS = {
    "readMostly",
    "maxNewInterpretationRuns",
    "maxNewWeeklyReviews",
    "maxNewPracticeSessions",
}
_METHOD_FEEDBACK_FIELDS = {"targetKinds", "suggestedDatasets"}
_REPLY_STYLE_FIELDS = {"maxSentences", "requiredSubstrings", "forbiddenSubstrings", "maxChars"}
_ALLOWED_WRITE_FIELDS = {"kind", "source", "tool", "requiresApproval", "autonomous"}


def load_journey_schema() -> dict[str, object]:
    return json.loads(SCHEMA_PATH.read_text())


def _line_numbers(path: Path) -> list[int]:
    numbers: list[int] = []
    for line_number, raw_line in enumerate(path.read_text().splitlines(), start=1):
        if raw_line.strip():
            numbers.append(line_number)
    return numbers


def _string_set(value: object) -> set[str]:
    if not isinstance(value, list):
        return set()
    return {str(item) for item in value}


def _raise(path: Path, line_number: int, field_path: str, message: str) -> None:
    raise ValueError(f"{path}:{line_number}:{field_path} {message}")


def _require_mapping(
    value: object, *, path: Path, line_number: int, field_path: str
) -> dict[str, object]:
    if not isinstance(value, dict):
        _raise(path, line_number, field_path, "must be an object.")
    return {str(key): item for key, item in value.items()}


def _validate_match_spec(
    value: object,
    *,
    path: Path,
    line_number: int,
    field_path: str,
) -> None:
    mapping = _require_mapping(value, path=path, line_number=line_number, field_path=field_path)
    if not mapping:
        _raise(path, line_number, field_path, "must not be empty.")
    unknown = set(mapping) - _MATCH_KEYS
    if unknown:
        _raise(
            path,
            line_number,
            field_path,
            f"contains unsupported matcher(s): {', '.join(sorted(unknown))}.",
        )


def _validate_reply_style(
    value: object,
    *,
    path: Path,
    line_number: int,
    field_path: str,
) -> None:
    mapping = _require_mapping(value, path=path, line_number=line_number, field_path=field_path)
    unknown = set(mapping) - _REPLY_STYLE_FIELDS
    if unknown:
        _raise(
            path,
            line_number,
            field_path,
            f"contains unsupported key(s): {', '.join(sorted(unknown))}.",
        )


def _validate_allowed_writes(
    value: object,
    *,
    path: Path,
    line_number: int,
    field_path: str,
) -> None:
    if not isinstance(value, list):
        _raise(path, line_number, field_path, "must be an array.")
    for index, item in enumerate(value):
        entry = _require_mapping(
            item,
            path=path,
            line_number=line_number,
            field_path=f"{field_path}[{index}]",
        )
        unknown = set(entry) - _ALLOWED_WRITE_FIELDS
        if unknown:
            _raise(
                path,
                line_number,
                f"{field_path}[{index}]",
                f"contains unsupported key(s): {', '.join(sorted(unknown))}.",
            )
        if "kind" not in entry:
            _raise(path, line_number, f"{field_path}[{index}].kind", "is required.")


def _validate_turn_expected(
    value: object,
    *,
    path: Path,
    line_number: int,
    field_path: str,
) -> None:
    mapping = _require_mapping(value, path=path, line_number=line_number, field_path=field_path)
    unknown = set(mapping) - _TURN_EXPECTED_FIELDS
    if unknown:
        _raise(
            path,
            line_number,
            field_path,
            f"contains unsupported key(s): {', '.join(sorted(unknown))}.",
        )
    for key in (
        "toolSequence",
        "selectedSurface",
        "selectedMoveKind",
        "depthLevel",
        "captureTargets",
    ):
        if key in mapping:
            _validate_match_spec(
                mapping[key],
                path=path,
                line_number=line_number,
                field_path=f"{field_path}.{key}",
            )
    if "allowedWrites" in mapping:
        _validate_allowed_writes(
            mapping["allowedWrites"],
            path=path,
            line_number=line_number,
            field_path=f"{field_path}.allowedWrites",
        )
    if "replyStyle" in mapping:
        _validate_reply_style(
            mapping["replyStyle"],
            path=path,
            line_number=line_number,
            field_path=f"{field_path}.replyStyle",
        )


def _validate_turn(
    value: object,
    *,
    path: Path,
    line_number: int,
    field_path: str,
) -> None:
    mapping = _require_mapping(value, path=path, line_number=line_number, field_path=field_path)
    required = {"turnId", "turnKind", "userTurn", "expected"}
    missing = sorted(required - set(mapping))
    if missing:
        _raise(path, line_number, field_path, f"is missing required key(s): {', '.join(missing)}.")
    unknown = set(mapping) - {"turnId", "turnKind", "userTurn", "expected", "notes"}
    if unknown:
        _raise(
            path,
            line_number,
            field_path,
            f"contains unsupported key(s): {', '.join(sorted(unknown))}.",
        )
    if str(mapping["turnKind"]) not in _TURN_KINDS:
        _raise(
            path,
            line_number,
            f"{field_path}.turnKind",
            f"has unsupported value '{mapping['turnKind']}'.",
        )
    _validate_turn_expected(
        mapping["expected"],
        path=path,
        line_number=line_number,
        field_path=f"{field_path}.expected",
    )


def _validate_backend_assertions(
    value: object,
    *,
    path: Path,
    line_number: int,
    field_path: str,
) -> None:
    mapping = _require_mapping(value, path=path, line_number=line_number, field_path=field_path)
    unknown = set(mapping) - _BACKEND_ASSERTION_FIELDS
    if unknown:
        _raise(
            path,
            line_number,
            field_path,
            f"contains unsupported key(s): {', '.join(sorted(unknown))}.",
        )


def _validate_method_feedback(
    value: object,
    *,
    path: Path,
    line_number: int,
    field_path: str,
) -> None:
    mapping = _require_mapping(value, path=path, line_number=line_number, field_path=field_path)
    unknown = set(mapping) - _METHOD_FEEDBACK_FIELDS
    if unknown:
        _raise(
            path,
            line_number,
            field_path,
            f"contains unsupported key(s): {', '.join(sorted(unknown))}.",
        )


def _validate_case(case: dict[str, object], *, path: Path, line_number: int) -> dict[str, object]:
    unknown = set(case) - _TOP_LEVEL_FIELDS
    if unknown:
        _raise(
            path,
            line_number,
            "",
            f"contains unsupported top-level field(s): {', '.join(sorted(unknown))}.",
        )
    if int(case.get("schemaVersion") or 0) != 1:
        _raise(path, line_number, "schemaVersion", "must equal 1 for journey CLI cases.")
    if str(case.get("journeyFamily") or "") not in _FAMILIES:
        _raise(
            path,
            line_number,
            "journeyFamily",
            f"has unsupported value '{case.get('journeyFamily')}'.",
        )
    if str(case.get("caseKind") or "") not in _CASE_KINDS:
        _raise(path, line_number, "caseKind", f"has unsupported value '{case.get('caseKind')}'.")
    if not _string_set(case.get("testLayers")):
        _raise(path, line_number, "testLayers", "must contain at least one layer.")
    unsupported_layers = _string_set(case.get("testLayers")) - _TEST_LAYERS
    if unsupported_layers:
        _raise(
            path,
            line_number,
            "testLayers",
            f"contains unsupported value(s): {', '.join(sorted(unsupported_layers))}.",
        )
    unsupported_assertions = _string_set(case.get("assertionKinds")) - _ASSERTION_KINDS
    if unsupported_assertions:
        _raise(
            path,
            line_number,
            "assertionKinds",
            f"contains unsupported value(s): {', '.join(sorted(unsupported_assertions))}.",
        )
    turns = case.get("turns")
    if not isinstance(turns, list) or not turns:
        _raise(path, line_number, "turns", "must be a non-empty array.")
    seen_turn_ids: set[str] = set()
    for index, turn in enumerate(turns):
        _validate_turn(turn, path=path, line_number=line_number, field_path=f"turns[{index}]")
        turn_id = str(
            _require_mapping(
                turn, path=path, line_number=line_number, field_path=f"turns[{index}]"
            )["turnId"]
        )
        if turn_id in seen_turn_ids:
            _raise(
                path,
                line_number,
                f"turns[{index}].turnId",
                f"duplicates prior turn id '{turn_id}'.",
            )
        seen_turn_ids.add(turn_id)
    if "backendAssertions" in case:
        _validate_backend_assertions(
            case["backendAssertions"],
            path=path,
            line_number=line_number,
            field_path="backendAssertions",
        )
    if "methodEvalFeedback" in case:
        _validate_method_feedback(
            case["methodEvalFeedback"],
            path=path,
            line_number=line_number,
            field_path="methodEvalFeedback",
        )
    normalized = dict(case)
    normalized.setdefault("assertionKinds", [])
    normalized.setdefault("tags", [])
    normalized.setdefault("historySeed", {})
    normalized.setdefault("backendAssertions", {})
    return normalized


def load_journey_cases(
    paths: Sequence[Path],
    *,
    split_filter: Iterable[str] | None = None,
    case_ids: Iterable[str] | None = None,
    include_tags: Iterable[str] | None = None,
    exclude_tags: Iterable[str] | None = None,
) -> list[dict[str, object]]:
    allowed_case_ids = {str(item) for item in case_ids or () if str(item)}
    required_tags = {str(item) for item in include_tags or () if str(item)}
    blocked_tags = {str(item) for item in exclude_tags or () if str(item)}
    loaded: list[dict[str, object]] = []
    seen_case_ids: set[str] = set()
    for path in paths:
        cases = load_jsonl_cases(path)
        line_numbers = _line_numbers(path)
        if len(cases) != len(line_numbers):
            raise ValueError(f"{path} case count and line count diverged during load.")
        for case, line_number in zip(cases, line_numbers, strict=True):
            case_id = str(case.get("caseId") or "")
            if not case_id:
                _raise(path, line_number, "caseId", "is required.")
            if case_id in seen_case_ids:
                _raise(path, line_number, "caseId", f"duplicates prior case id '{case_id}'.")
            normalized = _validate_case(case, path=path, line_number=line_number)
            tags = _string_set(normalized.get("tags"))
            if allowed_case_ids and case_id not in allowed_case_ids:
                continue
            if required_tags and not required_tags.issubset(tags):
                continue
            if blocked_tags and blocked_tags.intersection(tags):
                continue
            seen_case_ids.add(case_id)
            loaded.append(normalized)
    return loaded
