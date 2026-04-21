from __future__ import annotations

from ..adapters.context_adapter import BuildContextInput, ContextAdapter
from ..application.circulatio_service import CirculatioService
from ..core.circulatio_core import CirculatioCore
from ..domain.types import (
    CirculationSummaryInput,
    MaterialInterpretationInput,
    RecordIntegrationInput,
)


class HermesCirculationFacade:
    def __init__(
        self,
        context_adapter: ContextAdapter,
        core: CirculatioCore,
        service: CirculatioService | None = None,
    ) -> None:
        self._context_adapter = context_adapter
        self._core = core
        self._service = service

    async def interpret_from_hermes_command(self, input_data: BuildContextInput):
        if self._service is not None:
            workflow = await self._service.create_and_interpret_material(
                {
                    "userId": input_data["userId"],
                    "materialType": input_data["materialType"],
                    "text": input_data["materialText"],
                    "materialDate": input_data.get("materialDate"),
                    "sessionContext": input_data.get("sessionContext"),
                    "userAssociations": input_data.get("userAssociations"),
                    "explicitQuestion": input_data.get("explicitQuestion"),
                    "culturalOrigins": input_data.get("culturalOrigins"),
                    "safetyContext": input_data.get("safetyContext"),
                    "options": input_data.get("options"),
                    "lifeOsWindow": input_data.get("lifeOsWindow"),
                }
            )
            return workflow["interpretation"]
        material_input: MaterialInterpretationInput = (
            await self._context_adapter.build_material_input(input_data)
        )
        return await self._core.interpret_material(material_input)

    async def weekly_review(self, input_data: CirculationSummaryInput):
        if self._service is not None:
            review = await self._service.generate_weekly_review(
                user_id=input_data["userId"],
                window_start=input_data["windowStart"],
                window_end=input_data["windowEnd"],
            )
            return review["result"]
        return await self._core.generate_circulation_summary(input_data)

    async def record_user_feedback(self, input_data: RecordIntegrationInput):
        return await self._core.record_integration(input_data)
