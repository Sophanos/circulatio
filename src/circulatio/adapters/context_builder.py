from __future__ import annotations

from typing import Protocol

from ..domain.normalization import compact_life_context_snapshot
from ..domain.types import Id, LifeContextSnapshot
from ..repositories.circulatio_repository import CirculatioRepository


class LifeContextBuilder(Protocol):
    async def build_life_context_snapshot(
        self,
        *,
        user_id: Id,
        window_start: str,
        window_end: str,
        material_id: Id | None = None,
    ) -> LifeContextSnapshot | None: ...


class CirculatioLifeContextBuilder:
    def __init__(
        self,
        repository: CirculatioRepository,
        *,
        default_window_days: int = 7,
    ) -> None:
        self._repository = repository
        self.default_window_days = default_window_days

    async def build_life_context_snapshot(
        self,
        *,
        user_id: Id,
        window_start: str,
        window_end: str,
        material_id: Id | None = None,
    ) -> LifeContextSnapshot | None:
        snapshot = await self._repository.build_life_context_snapshot_from_records(
            user_id,
            window_start=window_start,
            window_end=window_end,
            exclude_material_id=material_id,
        )
        if snapshot is None:
            return None
        compacted = compact_life_context_snapshot(snapshot)
        if compacted is None:
            return None
        compacted["source"] = "circulatio-backend"
        return compacted
