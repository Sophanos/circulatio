from __future__ import annotations

from abc import ABC, abstractmethod

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


class GraphMemoryRepository(ABC):
    @abstractmethod
    async def get_hermes_memory_context(
        self, user_id: Id, *, max_items: int | None = None
    ) -> HermesMemoryContext:
        raise NotImplementedError

    @abstractmethod
    async def get_symbolic_memory_snapshot(
        self, user_id: Id, *, max_items: int | None = None
    ) -> SymbolicMemorySnapshot:
        raise NotImplementedError

    @abstractmethod
    async def apply_approved_proposals(
        self, *, user_id: Id, memory_write_plan: MemoryWritePlan, approved_proposal_ids: list[Id]
    ) -> dict[str, list[Id]]:
        raise NotImplementedError

    @abstractmethod
    async def record_integration(
        self, input_data: RecordIntegrationInput
    ) -> RecordIntegrationResult:
        raise NotImplementedError

    @abstractmethod
    async def suppress_hypothesis(
        self, request: SuppressHypothesisRequest
    ) -> SuppressedHypothesisSummary:
        raise NotImplementedError

    @abstractmethod
    async def revise_entity(self, request: ReviseGraphEntityRequest) -> None:
        raise NotImplementedError

    @abstractmethod
    async def delete_entity(self, request: DeleteGraphEntityRequest) -> None:
        raise NotImplementedError
