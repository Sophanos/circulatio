from __future__ import annotations

from typing import Protocol

from ..domain.graph import (
    DeleteGraphEntityRequest,
    ReviseGraphEntityRequest,
    SuppressHypothesisRequest,
    SymbolicMemorySnapshot,
)
from ..domain.types import (
    HermesMemoryContext,
    Id,
    MemoryWritePlan,
    RecordIntegrationInput,
    RecordIntegrationResult,
    SuppressedHypothesisSummary,
)
from ..repositories.graph_memory_repository import GraphMemoryRepository


class HermesMemoryPort(Protocol):
    async def read_symbolic_context(
        self, user_id: Id, *, max_items: int | None = None
    ) -> HermesMemoryContext: ...

    async def write_approved_symbolic_proposals(
        self, *, user_id: Id, memory_write_plan: MemoryWritePlan, approved_proposal_ids: list[Id]
    ) -> dict[str, list[Id]]: ...

    async def write_integration_feedback(
        self, input_data: RecordIntegrationInput
    ) -> RecordIntegrationResult: ...

    async def suppress_symbolic_hypothesis(
        self, request: SuppressHypothesisRequest
    ) -> SuppressedHypothesisSummary: ...

    async def revise_symbolic_memory(self, request: ReviseGraphEntityRequest) -> None: ...

    async def delete_symbolic_memory(self, request: DeleteGraphEntityRequest) -> None: ...


class HermesMemoryBackedRepository(GraphMemoryRepository):
    """Legacy symbolic-memory adapter.

    Full Circulatio product persistence should be implemented against
    `HermesCirculatioPersistencePort` rather than extending this narrow facade.
    """

    def __init__(self, port: HermesMemoryPort) -> None:
        self._port = port

    async def get_hermes_memory_context(
        self, user_id: Id, *, max_items: int | None = None
    ) -> HermesMemoryContext:
        return await self._port.read_symbolic_context(user_id, max_items=max_items)

    async def get_symbolic_memory_snapshot(
        self, user_id: Id, *, max_items: int | None = None
    ) -> SymbolicMemorySnapshot:
        context = await self._port.read_symbolic_context(user_id, max_items=max_items)
        return {
            "personalSymbols": context["recurringSymbols"],
            "complexCandidates": context["activeComplexCandidates"],
            "materialSummaries": context["recentMaterialSummaries"],
            "evidence": [],
            "practiceOutcomes": context["practiceOutcomes"],
            "culturalOrigins": context["culturalOriginPreferences"],
            "typologyLenses": context["typologyLensSummaries"],
        }

    async def apply_approved_proposals(
        self, *, user_id: Id, memory_write_plan: MemoryWritePlan, approved_proposal_ids: list[Id]
    ) -> dict[str, list[Id]]:
        return await self._port.write_approved_symbolic_proposals(
            user_id=user_id,
            memory_write_plan=memory_write_plan,
            approved_proposal_ids=approved_proposal_ids,
        )

    async def record_integration(
        self, input_data: RecordIntegrationInput
    ) -> RecordIntegrationResult:
        return await self._port.write_integration_feedback(input_data)

    async def suppress_hypothesis(
        self, request: SuppressHypothesisRequest
    ) -> SuppressedHypothesisSummary:
        return await self._port.suppress_symbolic_hypothesis(request)

    async def revise_entity(self, request: ReviseGraphEntityRequest) -> None:
        await self._port.revise_symbolic_memory(request)

    async def delete_entity(self, request: DeleteGraphEntityRequest) -> None:
        await self._port.delete_symbolic_memory(request)
