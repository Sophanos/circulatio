from __future__ import annotations

from typing import Any, cast

from .types import (
    HermesMemoryContext,
    InterpretationOptions,
    LifeContextSnapshot,
    MaterialInterpretationInput,
    MaterialType,
    SessionContext,
)

_VALID_MATERIAL_TYPES: set[MaterialType] = {
    "dream",
    "reflection",
    "charged_event",
    "symbolic_motif",
    "practice_outcome",
}


def normalize_hermes_memory_context(
    context: dict[str, Any] | HermesMemoryContext | None,
) -> HermesMemoryContext:
    raw = context or {}
    return {
        "recurringSymbols": list(raw.get("recurringSymbols", [])),
        "activeComplexCandidates": list(raw.get("activeComplexCandidates", [])),
        "recentMaterialSummaries": list(raw.get("recentMaterialSummaries", [])),
        "recentInterpretationFeedback": list(raw.get("recentInterpretationFeedback", [])),
        "practiceOutcomes": list(raw.get("practiceOutcomes", [])),
        "culturalOriginPreferences": list(raw.get("culturalOriginPreferences", [])),
        "suppressedHypotheses": list(raw.get("suppressedHypotheses", [])),
        "typologyLensSummaries": list(raw.get("typologyLensSummaries", [])),
        "recentTypologySignals": list(raw.get("recentTypologySignals", [])),
    }


def normalize_session_context(context: dict[str, Any] | SessionContext | None) -> SessionContext:
    raw = context or {}
    return {
        "contextNotes": list(raw.get("contextNotes", [])),
        "recentEventNotes": list(raw.get("recentEventNotes", [])),
        "currentStateNotes": list(raw.get("currentStateNotes", [])),
        "source": "current-conversation",
    }


def normalize_options(
    options: dict[str, Any] | InterpretationOptions | None,
) -> InterpretationOptions:
    raw = dict(options or {})
    normalized: InterpretationOptions = {
        "maxHistoricalItems": int(raw.get("maxHistoricalItems", 12)),
        "maxHypotheses": int(raw.get("maxHypotheses", 2)),
        "allowCulturalAmplification": bool(raw.get("allowCulturalAmplification", False)),
        "allowLifeContextLinks": bool(raw.get("allowLifeContextLinks", True)),
        "proposeRawMaterialStorage": bool(raw.get("proposeRawMaterialStorage", False)),
        "enableTypology": bool(raw.get("enableTypology", False)),
        "maxTypologyHypotheses": int(raw.get("maxTypologyHypotheses", 1)),
    }
    for key in ("maxHistoricalItems", "maxHypotheses", "maxTypologyHypotheses"):
        if normalized[key] < 0:  # type: ignore[index]
            raise ValueError(f"{key} cannot be negative")
    return normalized


def compact_life_context_snapshot(
    snapshot: dict[str, Any] | LifeContextSnapshot | None,
) -> LifeContextSnapshot | None:
    if snapshot is None:
        return None
    compact: LifeContextSnapshot = {
        "windowStart": snapshot["windowStart"],
        "windowEnd": snapshot["windowEnd"],
        "source": snapshot["source"],
    }
    if snapshot.get("lifeEventRefs"):
        compact["lifeEventRefs"] = list(snapshot["lifeEventRefs"][:5])
    for key in (
        "moodSummary",
        "energySummary",
        "focusSummary",
        "mentalStateSummary",
        "habitSummary",
    ):
        if snapshot.get(key):
            compact[key] = cast(str, snapshot[key])
    if snapshot.get("notableChanges"):
        compact["notableChanges"] = list(snapshot["notableChanges"][:5])
    return compact


def validate_material_input(input_data: MaterialInterpretationInput) -> None:
    if not input_data.get("userId"):
        raise ValueError("userId is required")
    if input_data.get("materialType") not in _VALID_MATERIAL_TYPES:
        raise ValueError("materialType is invalid")
    if not input_data.get("materialText") or not input_data["materialText"].strip():
        raise ValueError("materialText must be non-blank")
