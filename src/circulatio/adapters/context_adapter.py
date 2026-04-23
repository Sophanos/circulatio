from __future__ import annotations

import logging
from copy import deepcopy
from datetime import UTC, datetime, timedelta
from typing import TypedDict

from ..domain.normalization import (
    compact_life_context_snapshot,
    normalize_hermes_memory_context,
    normalize_options,
    normalize_session_context,
)
from ..domain.timestamps import format_iso_datetime, parse_iso_datetime
from ..domain.types import (
    CulturalOriginSummary,
    InterpretationOptions,
    LifeContextSnapshot,
    MaterialInterpretationInput,
    MaterialType,
    MethodContextSnapshot,
    PracticeRecommendationInput,
    PracticeTriggerSummary,
    SafetyContext,
    SessionContext,
    UserAssociationInput,
)
from ..repositories.graph_memory_repository import GraphMemoryRepository
from .context_builder import LifeContextBuilder
from .life_os_adapter import LifeOsReferenceAdapter
from .method_context_builder import MethodContextBuilder

LOGGER = logging.getLogger(__name__)


class LifeOsWindow(TypedDict):
    start: str
    end: str


class BuildContextInput(TypedDict, total=False):
    userId: str
    materialId: str
    materialType: MaterialType
    materialText: str
    materialDate: str
    sessionContext: SessionContext
    wakingTone: str
    userAssociations: list[UserAssociationInput]
    explicitQuestion: str
    culturalOrigins: list[CulturalOriginSummary]
    safetyContext: SafetyContext
    options: InterpretationOptions
    lifeContextSnapshot: LifeContextSnapshot
    lifeOsWindow: LifeOsWindow
    methodContextSnapshot: MethodContextSnapshot


class BuildPracticeContextInput(TypedDict, total=False):
    userId: str
    windowStart: str
    windowEnd: str
    trigger: PracticeTriggerSummary
    sessionContext: SessionContext
    explicitQuestion: str
    safetyContext: SafetyContext
    options: InterpretationOptions


class ContextAdapter:
    def __init__(
        self,
        repository: GraphMemoryRepository,
        life_os: LifeOsReferenceAdapter | None = None,
        life_context_builder: LifeContextBuilder | None = None,
        method_context_builder: MethodContextBuilder | None = None,
        default_life_context_window_days: int = 7,
    ) -> None:
        self._repository = repository
        self._life_os = life_os
        self._life_context_builder = life_context_builder
        self._method_context_builder = method_context_builder
        self._default_life_context_window_days = default_life_context_window_days

    async def build_material_input(
        self, input_data: BuildContextInput
    ) -> MaterialInterpretationInput:
        options = normalize_options(input_data.get("options"))
        hermes_memory_context = normalize_hermes_memory_context(
            await self._repository.get_hermes_memory_context(
                input_data["userId"],
                max_items=options.get("maxHistoricalItems", 12),
            )
        )

        window_start, window_end = self._resolve_window(input_data)
        life_context_snapshot = await self._resolve_life_context_snapshot(
            input_data=input_data,
            window_start=window_start,
            window_end=window_end,
        )
        method_context_snapshot = await self._resolve_method_context_snapshot(
            input_data=input_data,
            window_start=window_start,
            window_end=window_end,
        )

        result: MaterialInterpretationInput = {
            "userId": input_data["userId"],
            "materialType": input_data["materialType"],
            "materialText": input_data["materialText"],
            "hermesMemoryContext": hermes_memory_context,
            "sessionContext": normalize_session_context(input_data.get("sessionContext")),
            "options": options,
        }
        if input_data.get("materialId"):
            result["materialId"] = input_data["materialId"]
        for key in (
            "materialDate",
            "wakingTone",
            "userAssociations",
            "explicitQuestion",
            "culturalOrigins",
            "safetyContext",
        ):
            if key in input_data:
                result[key] = input_data[key]  # type: ignore[index]
        if life_context_snapshot is not None:
            result["lifeContextSnapshot"] = life_context_snapshot
        if method_context_snapshot is not None:
            result["methodContextSnapshot"] = method_context_snapshot
        return result

    async def build_practice_input(
        self, input_data: BuildPracticeContextInput
    ) -> PracticeRecommendationInput:
        options = normalize_options(input_data.get("options"))
        hermes_memory_context = normalize_hermes_memory_context(
            await self._repository.get_hermes_memory_context(
                input_data["userId"],
                max_items=options.get("maxHistoricalItems", 12),
            )
        )
        life_context_snapshot = await self._resolve_life_context_snapshot(
            input_data={
                "userId": input_data["userId"],
                "materialType": "reflection",
                "materialText": input_data.get("explicitQuestion") or "practice request",
                "materialDate": input_data["windowEnd"],
                "sessionContext": normalize_session_context(input_data.get("sessionContext")),
                "options": options,
            },
            window_start=input_data["windowStart"],
            window_end=input_data["windowEnd"],
        )
        method_context_snapshot = await self._resolve_method_context_snapshot(
            input_data={
                "userId": input_data["userId"],
                "materialType": "reflection",
                "materialText": input_data.get("explicitQuestion") or "practice request",
                "materialDate": input_data["windowEnd"],
                "sessionContext": normalize_session_context(input_data.get("sessionContext")),
                "options": options,
            },
            window_start=input_data["windowStart"],
            window_end=input_data["windowEnd"],
        )
        result: PracticeRecommendationInput = {
            "userId": input_data["userId"],
            "windowStart": input_data["windowStart"],
            "windowEnd": input_data["windowEnd"],
            "trigger": (
                deepcopy(input_data["trigger"])
                if isinstance(input_data["trigger"], dict)
                else {"triggerType": "manual"}
            ),
            "hermesMemoryContext": hermes_memory_context,
            "sessionContext": normalize_session_context(input_data.get("sessionContext")),
            "options": options,
        }
        if input_data.get("explicitQuestion"):
            result["explicitQuestion"] = input_data["explicitQuestion"]
        if input_data.get("safetyContext"):
            result["safetyContext"] = input_data["safetyContext"]
        if life_context_snapshot is not None:
            result["lifeContextSnapshot"] = life_context_snapshot
        if method_context_snapshot is not None:
            result["methodContextSnapshot"] = method_context_snapshot
        return result

    async def _resolve_life_context_snapshot(
        self,
        *,
        input_data: BuildContextInput,
        window_start: str,
        window_end: str,
    ) -> LifeContextSnapshot | None:
        if self._life_context_builder is not None:
            try:
                snapshot = await self._life_context_builder.build_life_context_snapshot(
                    user_id=input_data["userId"],
                    window_start=window_start,
                    window_end=window_end,
                    material_id=input_data.get("materialId"),
                )
            except Exception:
                LOGGER.warning(
                    (
                        "Circulatio native life context builder failed; "
                        "continuing with fallback precedence."
                    ),
                    exc_info=True,
                )
            else:
                if snapshot is not None:
                    return snapshot

        provided = input_data.get("lifeContextSnapshot")
        if provided is not None:
            try:
                compacted = compact_life_context_snapshot(provided)
            except Exception:
                LOGGER.warning(
                    "Provided life context snapshot could not be compacted; ignoring it.",
                    exc_info=True,
                )
            else:
                if compacted is not None:
                    return compacted

        if input_data.get("lifeOsWindow") and self._life_os is not None:
            try:
                raw_snapshot = await self._life_os.get_life_context_snapshot(
                    user_id=input_data["userId"],
                    window_start=input_data["lifeOsWindow"]["start"],
                    window_end=input_data["lifeOsWindow"]["end"],
                )
                return compact_life_context_snapshot(raw_snapshot)
            except Exception:
                LOGGER.warning(
                    "Hermes life-OS context lookup failed; continuing without life context.",
                    exc_info=True,
                )
        return None

    async def _resolve_method_context_snapshot(
        self,
        *,
        input_data: BuildContextInput,
        window_start: str,
        window_end: str,
    ) -> MethodContextSnapshot | None:
        provided = input_data.get("methodContextSnapshot")
        if provided is not None:
            return provided
        if self._method_context_builder is None:
            return None
        try:
            return await self._method_context_builder.build_method_context_snapshot(
                user_id=input_data["userId"],
                window_start=window_start,
                window_end=window_end,
                material_id=input_data.get("materialId"),
            )
        except Exception:
            LOGGER.warning(
                "Circulatio method context builder failed; continuing without method context.",
                exc_info=True,
            )
            return None

    def _resolve_window(self, input_data: BuildContextInput) -> tuple[str, str]:
        if input_data.get("lifeOsWindow"):
            return input_data["lifeOsWindow"]["start"], input_data["lifeOsWindow"]["end"]
        anchor = parse_iso_datetime(input_data.get("materialDate"), default=datetime.now(UTC))
        window_end = anchor
        window_start = anchor - timedelta(days=self._default_life_context_window_days)
        return format_iso_datetime(window_start), format_iso_datetime(window_end)
