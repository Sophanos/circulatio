from __future__ import annotations

from typing import Protocol

from ..domain.types import Id, MethodContextSnapshot
from ..repositories.circulatio_repository import CirculatioRepository


class MethodContextBuilder(Protocol):
    async def build_method_context_snapshot(
        self,
        *,
        user_id: Id,
        window_start: str,
        window_end: str,
        material_id: Id | None = None,
    ) -> MethodContextSnapshot | None: ...


class CirculatioMethodContextBuilder:
    def __init__(self, repository: CirculatioRepository) -> None:
        self._repository = repository

    async def build_method_context_snapshot(
        self,
        *,
        user_id: Id,
        window_start: str,
        window_end: str,
        material_id: Id | None = None,
    ) -> MethodContextSnapshot | None:
        return await self._repository.build_method_context_snapshot_from_records(
            user_id,
            window_start=window_start,
            window_end=window_end,
            material_id=material_id,
        )
