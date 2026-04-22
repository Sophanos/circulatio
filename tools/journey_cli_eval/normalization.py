from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass, field

from circulatio_hermes_plugin import schemas as plugin_schemas

from .output_schema import CANONICAL_MOVE_KINDS, CANONICAL_SURFACES

_FENCED_JSON_RE = re.compile(r"```(?:json)?\s*(\{.*?\})\s*```", re.DOTALL)
_ESCALATION_PHRASES = {
    "projection_language": (
        "what alex represents",
        "you are projecting",
        "this person symbolizes",
        "they symbolize",
    ),
    "archetypal_patterning": (
        "archetype",
        "shadow",
        " self ",
        " anima ",
        " animus ",
    ),
    "diagnostic_claim": (
        "this is trauma",
        "you have",
        "this proves",
        "this means you are",
    ),
    "new_practice_before_recording_response": (
        "here is another practice",
        "try this practice instead",
    ),
}
_WRITE_KIND_BY_TOOL = {
    "circulatio_store_dream": "material",
    "circulatio_store_event": "material",
    "circulatio_store_reflection": "material",
    "circulatio_store_symbolic_note": "material",
    "circulatio_store_body_state": "body_state",
    "circulatio_create_journey": "journey",
    "circulatio_update_journey": "journey",
    "circulatio_set_journey_status": "journey",
    "circulatio_record_relational_scene": "relational_scene",
    "circulatio_generate_practice_recommendation": "practice_session",
    "circulatio_respond_practice_recommendation": "practice_response",
    "circulatio_record_interpretation_feedback": "feedback",
    "circulatio_record_practice_feedback": "feedback",
    "circulatio_threshold_review": "review",
    "circulatio_living_myth_review": "review",
    "circulatio_approve_proposals": "proposal",
    "circulatio_reject_proposals": "proposal",
}
_READ_ONLY_TOOLS = {
    "circulatio_alive_today",
    "circulatio_journey_page",
    "circulatio_discovery",
    "circulatio_list_materials",
    "circulatio_get_material",
    "circulatio_list_journeys",
    "circulatio_get_journey",
    "circulatio_query_graph",
    "circulatio_memory_kernel",
    "circulatio_dashboard_summary",
}
_SURFACE_ALIASES = {
    "alive today": "alive_today",
    "alive_today": "alive_today",
    "journey page": "journey_page",
    "journey_page": "journey_page",
    "practice follow-up": "practice_followup",
    "practice follow up": "practice_followup",
    "practice_followup": "practice_followup",
    "method_state_response": "method_state_response",
    "method state response": "method_state_response",
    "analysis packet": "analysis_packet",
    "analysis_packet": "analysis_packet",
    "threshold review": "threshold_review",
    "threshold_review": "threshold_review",
    "living myth review": "living_myth_review",
    "living_myth_review": "living_myth_review",
    "weekly review": "weekly_review",
    "weekly_review": "weekly_review",
    "discovery": "discovery",
    "none": "none",
}


def _normalize_identifier(value: object) -> str:
    text = str(value or "").strip().lower()
    text = re.sub(r"[^a-z0-9]+", "_", text)
    return text.strip("_")


def _canonical_tool_names() -> dict[str, str]:
    aliases: dict[str, str] = {}
    for schema in plugin_schemas.TOOL_SCHEMAS:
        canonical = str(schema.get("name") or "")
        stripped = canonical.removeprefix("circulatio_")
        tokens = [token for token in stripped.split("_") if token]
        forms = {
            canonical,
            stripped,
            stripped.replace("_", "."),
            stripped.replace("_", "-"),
            f"circulatio.{stripped}",
            f"circulatio.{stripped.replace('_', '.')}",
        }
        if tokens:
            forms.add("_".join(tokens[1:] + tokens[:1]))
            forms.add(".".join(tokens))
            forms.add("-".join(tokens))
        for form in forms:
            aliases[_normalize_identifier(form)] = canonical
    return aliases


_TOOL_ALIASES = _canonical_tool_names()


def canonicalize_tool_name(value: object) -> tuple[str | None, str | None]:
    text = str(value or "").strip()
    if not text:
        return None, None
    canonical = _TOOL_ALIASES.get(_normalize_identifier(text))
    if canonical is not None:
        return canonical, None
    return text, f"Unrecognized tool alias '{text}'."


def _normalize_surface(value: object) -> tuple[str | None, str | None]:
    text = " ".join(str(value or "").strip().lower().replace("_", " ").split())
    if not text:
        return None, None
    surface = _SURFACE_ALIASES.get(text)
    if surface is not None:
        return surface, None
    candidate = text.replace(" ", "_")
    if candidate in CANONICAL_SURFACES:
        return candidate, None
    return candidate, f"Unknown surface '{value}'."


def _normalize_move_kind(value: object) -> tuple[str | None, str | None]:
    text = _normalize_identifier(value)
    if not text:
        return None, None
    if text in CANONICAL_MOVE_KINDS:
        return text, None
    return text, f"Unknown move kind '{value}'."


def _normalize_bool(value: object) -> tuple[bool | None, str | None]:
    if isinstance(value, bool):
        return value, None
    if value is None:
        return None, None
    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered in {"true", "false"}:
            return lowered == "true", f"Normalized string boolean '{value}'."
    return None, f"Could not normalize boolean value '{value}'."


def _coerce_string_list(value: object) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item) for item in value if str(item).strip()]
    text = str(value).strip()
    return [text] if text else []


def detect_forbidden_escalations(text: object, forbidden: list[str]) -> list[str]:
    haystack = f" {str(text or '').strip().lower()} "
    present: list[str] = []
    for name in forbidden:
        phrases = _ESCALATION_PHRASES.get(name, ())
        if any(phrase in haystack for phrase in phrases):
            present.append(name)
    return present


def _extract_balanced_object(text: str) -> str | None:
    start = text.find("{")
    if start < 0:
        return None
    depth = 0
    in_string = False
    escaped = False
    for index in range(start, len(text)):
        char = text[index]
        if in_string:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                in_string = False
            continue
        if char == '"':
            in_string = True
        elif char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return text[start : index + 1]
    return None


def _parse_json_object(text: str) -> dict[str, object] | None:
    stripped = text.strip()
    if not stripped:
        return None
    try:
        payload = json.loads(stripped)
    except json.JSONDecodeError:
        return None
    if isinstance(payload, dict):
        return {str(key): value for key, value in payload.items()}
    return None


def _extract_payload_from_value(value: object) -> dict[str, object] | None:
    if isinstance(value, dict):
        payload = {str(key): nested for key, nested in value.items()}
        if "turnResults" in payload or "caseId" in payload:
            return payload
        for nested in payload.values():
            candidate = _extract_payload_from_value(nested)
            if candidate is not None:
                return candidate
        return None
    if isinstance(value, list):
        for item in value:
            candidate = _extract_payload_from_value(item)
            if candidate is not None:
                return candidate
        return None
    if isinstance(value, str):
        candidate = _parse_json_object(value)
        if candidate is not None:
            extracted = _extract_payload_from_value(candidate)
            if extracted is not None:
                return extracted
        balanced = _extract_balanced_object(value)
        if balanced is not None:
            candidate = _parse_json_object(balanced)
            if candidate is not None:
                extracted = _extract_payload_from_value(candidate)
                if extracted is not None:
                    return extracted
    return None


def _parse_json_lines(text: str) -> dict[str, object] | None:
    parsed: list[dict[str, object]] = []
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        payload = _parse_json_object(line)
        if payload is not None:
            parsed.append(payload)
    for payload in reversed(parsed):
        candidate = _extract_payload_from_value(payload)
        if candidate is not None:
            return candidate
    return None


def _extract_payload(raw_text: str) -> tuple[dict[str, object] | None, str]:
    direct = _parse_json_object(raw_text)
    if direct is not None:
        candidate = _extract_payload_from_value(direct)
        if candidate is not None:
            return candidate, "parsed"
    json_lines = _parse_json_lines(raw_text)
    if json_lines is not None:
        return json_lines, "parsed"
    fenced = _FENCED_JSON_RE.search(raw_text)
    if fenced:
        fenced_payload = _parse_json_object(fenced.group(1))
        if fenced_payload is not None:
            candidate = _extract_payload_from_value(fenced_payload)
            if candidate is not None:
                return candidate, "parsed"
    balanced = _extract_balanced_object(raw_text)
    if balanced is not None:
        balanced_payload = _parse_json_object(balanced)
        if balanced_payload is not None:
            candidate = _extract_payload_from_value(balanced_payload)
            if candidate is not None:
                return candidate, "parsed"
    return None, "failed"


def _normalize_write_actions(
    raw_value: object,
    *,
    selected_tools: list[str],
) -> tuple[list[dict[str, object]], list[str]]:
    warnings: list[str] = []
    actions: list[dict[str, object]] = []
    if isinstance(raw_value, list):
        for index, item in enumerate(raw_value):
            if not isinstance(item, dict):
                warnings.append(f"writeActions[{index}] was not an object.")
                continue
            canonical_tool, warning = canonicalize_tool_name(item.get("tool"))
            if warning:
                warnings.append(warning)
            kind = _normalize_identifier(item.get("kind")) or "unknown"
            actions.append(
                {
                    "kind": kind,
                    "tool": canonical_tool,
                    "requiresApproval": item.get("requiresApproval"),
                    "autonomous": item.get("autonomous"),
                }
            )
    if actions:
        return actions, warnings
    inferred: list[dict[str, object]] = []
    for tool_name in selected_tools:
        kind = _WRITE_KIND_BY_TOOL.get(tool_name)
        if kind is None or tool_name in _READ_ONLY_TOOLS:
            continue
        inferred.append(
            {
                "kind": kind,
                "tool": tool_name,
                "requiresApproval": None,
                "autonomous": None,
            }
        )
    return inferred, warnings


def _normalize_turn(
    turn: dict[str, object],
    *,
    default_turn_id: str,
    forbidden_escalations: list[str],
) -> tuple[dict[str, object], list[str]]:
    warnings: list[str] = []
    raw_tools = turn.get("selectedToolSequence")
    if raw_tools is None and "selectedTool" in turn:
        raw_tools = [turn.get("selectedTool")]
    selected_tools: list[str] = []
    for item in _coerce_string_list(raw_tools):
        canonical, warning = canonicalize_tool_name(item)
        if warning:
            warnings.append(warning)
        if canonical:
            selected_tools.append(canonical)
    selected_surface, warning = _normalize_surface(turn.get("selectedSurface"))
    if warning:
        warnings.append(warning)
    selected_move_kind, warning = _normalize_move_kind(turn.get("selectedMoveKind"))
    if warning:
        warnings.append(warning)
    asked_clarification, warning = _normalize_bool(turn.get("askedClarification"))
    if warning:
        warnings.append(warning)
    performed_host_interpretation, warning = _normalize_bool(
        turn.get("performedHostInterpretation")
    )
    if warning:
        warnings.append(warning)
    write_actions, write_warnings = _normalize_write_actions(
        turn.get("writeActions"),
        selected_tools=selected_tools,
    )
    warnings.extend(write_warnings)
    read_actions = []
    for item in _coerce_string_list(turn.get("readActions")):
        canonical, warning = canonicalize_tool_name(item)
        if warning:
            warnings.append(warning)
        if canonical:
            read_actions.append(canonical)
    if not read_actions:
        read_actions = [tool for tool in selected_tools if tool in _READ_ONLY_TOOLS]
    capture_targets = [
        _normalize_identifier(item) for item in _coerce_string_list(turn.get("captureTargets"))
    ]
    host_reply = str(turn.get("hostReply") or "")
    rationale = str(turn.get("rationale") or "")
    forbidden_present = detect_forbidden_escalations(host_reply, forbidden_escalations)
    normalized = {
        "turnId": str(turn.get("turnId") or default_turn_id),
        "selectedToolSequence": selected_tools,
        "toolArgsSummary": turn.get("toolArgsSummary")
        if isinstance(turn.get("toolArgsSummary"), dict)
        else {},
        "selectedSurface": selected_surface,
        "selectedMoveKind": selected_move_kind,
        "depthLevel": _normalize_identifier(turn.get("depthLevel")) or None,
        "captureTargets": capture_targets,
        "readActions": read_actions,
        "writeActions": write_actions,
        "askedClarification": asked_clarification,
        "performedHostInterpretation": performed_host_interpretation,
        "forbiddenEscalationsPresent": forbidden_present,
        "hostReply": host_reply,
        "confidence": turn.get("confidence"),
        "rationale": rationale,
    }
    return normalized, warnings


@dataclass
class NormalizedJourneyOutput:
    case_id: str
    adapter: str
    parse_status: str
    payload: dict[str, object]
    warnings: list[str] = field(default_factory=list)
    raw_text: str = ""

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


def normalize_journey_output(
    raw_text: str,
    *,
    case: dict[str, object],
    adapter: str,
) -> NormalizedJourneyOutput:
    payload, parse_status = _extract_payload(raw_text)
    warnings: list[str] = []
    if payload is None:
        payload = {
            "caseId": str(case.get("caseId") or ""),
            "turnResults": [],
            "globalNotes": [],
            "parseStatus": parse_status,
        }
        return NormalizedJourneyOutput(
            case_id=str(case.get("caseId") or ""),
            adapter=adapter,
            parse_status=parse_status,
            payload=payload,
            warnings=warnings,
            raw_text=raw_text,
        )

    normalized_turns: list[dict[str, object]] = []
    raw_turns = payload.get("turnResults")
    if isinstance(raw_turns, list):
        for index, raw_turn in enumerate(raw_turns):
            if not isinstance(raw_turn, dict):
                warnings.append(f"turnResults[{index}] was not an object.")
                continue
            expected = (
                case.get("turns")[index]
                if isinstance(case.get("turns"), list) and index < len(case.get("turns", []))
                else {}
            )
            forbidden = []
            if isinstance(expected, dict):
                expected_mapping = expected.get("expected")
                if isinstance(expected_mapping, dict):
                    forbidden = [
                        str(item) for item in expected_mapping.get("forbiddenEscalations", [])
                    ]
            normalized_turn, turn_warnings = _normalize_turn(
                {str(key): value for key, value in raw_turn.items()},
                default_turn_id=str(raw_turn.get("turnId") or f"turn_{index + 1}"),
                forbidden_escalations=forbidden,
            )
            normalized_turns.append(normalized_turn)
            warnings.extend(turn_warnings)
    elif isinstance(case.get("turns"), list) and len(case["turns"]) == 1:
        first_turn = case["turns"][0]
        expected = first_turn.get("expected") if isinstance(first_turn, dict) else {}
        forbidden = []
        if isinstance(expected, dict):
            forbidden = [str(item) for item in expected.get("forbiddenEscalations", [])]
        normalized_turn, turn_warnings = _normalize_turn(
            payload,
            default_turn_id=str(first_turn.get("turnId") or "turn_1"),
            forbidden_escalations=forbidden,
        )
        normalized_turns.append(normalized_turn)
        warnings.extend(turn_warnings)
    normalized_payload = {
        "caseId": str(payload.get("caseId") or case.get("caseId") or ""),
        "turnResults": normalized_turns,
        "globalNotes": [str(item) for item in _coerce_string_list(payload.get("globalNotes"))],
        "parseStatus": parse_status,
        "normalizationWarnings": warnings,
    }
    return NormalizedJourneyOutput(
        case_id=str(case.get("caseId") or ""),
        adapter=adapter,
        parse_status=parse_status,
        payload=normalized_payload,
        warnings=warnings,
        raw_text=raw_text,
    )
