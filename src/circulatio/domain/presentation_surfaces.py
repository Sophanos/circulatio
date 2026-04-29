from __future__ import annotations

from copy import deepcopy
from typing import cast

from .presentation import RequestedRitualSurfaces

_CANONICAL_SURFACES = {
    "text",
    "audio",
    "captions",
    "breath",
    "meditation",
    "image",
    "cinema",
    "music",
}
_SURFACE_ALIASES = {"video": "cinema", "photo": "image"}
_UNSUPPORTED_SURFACES: set[str] = set()

_BREATH_PATTERNS = {"steadying", "lengthened_exhale", "box_breath", "orienting"}
_MEDITATION_FIELD_TYPES = {
    "coherence_convergence",
    "attention_anchor",
    "threshold_stillness",
    "image_afterglow",
}
_MEDITATION_DENSITIES = {"none", "sparse", "phase_label"}
_IMAGE_STYLE_INTENTS = {"symbolic_non_literal", "abstract", "photographic", "user_provided"}
_MUSIC_STYLE_INTENTS = {
    "dream_integration",
    "body_settling",
    "threshold_crossing",
    "quiet_reflection",
    "mythic_motion",
}


def normalize_requested_ritual_surfaces(
    value: object | None,
) -> tuple[RequestedRitualSurfaces, list[str]]:
    """Normalize loose host/tool ritual surface input into object-shaped surfaces."""
    if value is None:
        return {}, []
    if not isinstance(value, dict):
        return {}, ["requested_surface_invalid_shape_omitted:requestedSurfaces"]

    normalized: dict[str, object] = {}
    warnings: list[str] = []
    for raw_surface, raw_config in value.items():
        surface = str(raw_surface).strip()
        if not surface:
            continue
        canonical = _SURFACE_ALIASES.get(surface, surface)
        if canonical != surface:
            warnings.append(f"requested_surface_alias_normalized:{surface}->{canonical}")
        if surface in _UNSUPPORTED_SURFACES or canonical not in _CANONICAL_SURFACES:
            warnings.append(f"requested_surface_unsupported_omitted:{surface}")
            continue
        if raw_config is None:
            continue
        surface_config = _normalize_surface_config(canonical, raw_config, warnings)
        if surface_config is not None:
            normalized[canonical] = surface_config

    return cast(RequestedRitualSurfaces, normalized), list(dict.fromkeys(warnings))


def _normalize_surface_config(
    surface: str,
    value: object,
    warnings: list[str],
) -> dict[str, object] | None:
    if isinstance(value, bool):
        warnings.append(f"requested_surface_boolean_normalized:{surface}")
        return {"enabled": value}
    if not isinstance(value, dict):
        warnings.append(f"requested_surface_invalid_shape_omitted:{surface}")
        return None

    config = deepcopy(value)
    result: dict[str, object] = {}
    enabled = config.get("enabled", True)
    if isinstance(enabled, bool):
        result["enabled"] = enabled
    elif isinstance(enabled, str) and enabled.strip().lower() in {"true", "false"}:
        result["enabled"] = enabled.strip().lower() == "true"
        warnings.append(f"requested_surface_invalid_enabled_defaulted:{surface}")
    else:
        result["enabled"] = False
        warnings.append(f"requested_surface_invalid_enabled_defaulted:{surface}")

    for key, raw in config.items():
        if key == "enabled":
            continue
        if surface == "breath" and key == "request":
            request = _normalize_breath_request(raw, warnings)
            if request is not None:
                result["request"] = request
        elif surface == "meditation" and key == "request":
            request = _normalize_meditation_request(raw, warnings)
            if request is not None:
                result["request"] = request
        elif surface == "image" and key == "styleIntent":
            if isinstance(raw, str) and raw in _IMAGE_STYLE_INTENTS:
                result[key] = raw
            else:
                warnings.append(f"requested_surface_invalid_request_field_omitted:{surface}.{key}")
        elif surface in {"image", "cinema", "music"} and key == "allowExternalGeneration":
            if isinstance(raw, bool):
                result[key] = raw
            else:
                warnings.append(f"requested_surface_invalid_request_field_omitted:{surface}.{key}")
        elif surface == "music" and key == "styleIntent":
            if isinstance(raw, str) and raw in _MUSIC_STYLE_INTENTS:
                result[key] = raw
            else:
                warnings.append(f"requested_surface_invalid_request_field_omitted:{surface}.{key}")
        elif surface == "music" and key == "musicDurationSeconds":
            duration = _coerce_int(raw)
            if duration is None:
                warnings.append(f"requested_surface_invalid_request_field_omitted:{surface}.{key}")
            else:
                result[key] = min(max(duration, 15), 285)
        elif surface == "cinema" and key == "maxDurationSeconds":
            duration = _coerce_int(raw)
            if duration is None:
                warnings.append(f"requested_surface_invalid_request_field_omitted:{surface}.{key}")
            else:
                result[key] = min(max(duration, 1), 30)
        elif surface == "audio" and key in {"voiceId", "tone", "pace"} and isinstance(raw, str):
            result[key] = raw
        elif surface == "audio" and key == "speed":
            speed = _coerce_float(raw)
            if speed is None:
                warnings.append(f"requested_surface_invalid_request_field_omitted:{surface}.{key}")
            else:
                result[key] = min(max(speed, 0.1), 3.0)
        elif surface == "captions" and key == "format" and isinstance(raw, str):
            result[key] = raw
        elif surface == "text":
            result[key] = deepcopy(raw)

    return result


def _normalize_breath_request(value: object, warnings: list[str]) -> dict[str, object] | None:
    if not isinstance(value, dict):
        warnings.append("requested_surface_invalid_request_omitted:breath.request")
        return None
    result: dict[str, object] = {}
    pattern = value.get("pattern")
    if pattern is not None:
        if isinstance(pattern, str) and pattern in _BREATH_PATTERNS:
            result["pattern"] = pattern
        else:
            warnings.append("requested_surface_invalid_request_field_omitted:breath.request.pattern")
    technique_name = value.get("techniqueName")
    if isinstance(technique_name, str) and technique_name.strip():
        result["techniqueName"] = technique_name.strip()
    for field in ("cycles", "maxDurationSeconds"):
        if field not in value:
            continue
        integer = _coerce_int(value[field])
        if integer is None:
            warnings.append(f"requested_surface_invalid_request_field_omitted:breath.request.{field}")
        else:
            result[field] = integer
    return result


def _normalize_meditation_request(value: object, warnings: list[str]) -> dict[str, object] | None:
    if not isinstance(value, dict):
        warnings.append("requested_surface_invalid_request_omitted:meditation.request")
        return None
    result: dict[str, object] = {}
    field_type = value.get("fieldType")
    if field_type is not None:
        if isinstance(field_type, str) and field_type in _MEDITATION_FIELD_TYPES:
            result["fieldType"] = field_type
        else:
            warnings.append("requested_surface_invalid_request_field_omitted:meditation.request.fieldType")
    density = value.get("instructionDensity")
    if density is not None:
        if isinstance(density, str) and density in _MEDITATION_DENSITIES:
            result["instructionDensity"] = density
        else:
            warnings.append(
                "requested_surface_invalid_request_field_omitted:meditation.request.instructionDensity"
            )
    if "durationMs" in value:
        duration = _coerce_int(value["durationMs"])
        if duration is None:
            warnings.append("requested_surface_invalid_request_field_omitted:meditation.request.durationMs")
        else:
            result["durationMs"] = duration
    return result


def _coerce_int(value: object) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        stripped = value.strip()
        if stripped.isdecimal() or (stripped.startswith("-") and stripped[1:].isdecimal()):
            return int(stripped)
    return None


def _coerce_float(value: object) -> float | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int | float):
        return float(value)
    if isinstance(value, str):
        stripped = value.strip()
        try:
            return float(stripped)
        except ValueError:
            return None
    return None
