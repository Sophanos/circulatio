from __future__ import annotations

from typing import Protocol

from ..domain.context import ContextSnapshot
from ..domain.integration import IntegrationRecord
from ..domain.interpretations import InterpretationRunRecord
from ..domain.materials import MaterialRecord, MaterialRevision
from ..domain.patterns import PatternHistoryEntry, PatternRecord
from ..domain.practices import PracticeSessionRecord
from ..domain.reviews import WeeklyReviewRecord
from ..domain.symbols import SymbolHistoryEntry, SymbolRecord
from ..domain.types import EvidenceItem, Id
from ..domain.typology import TypologyLensRecord


class HermesCirculatioPersistencePort(Protocol):
    """Write-only mirror interface for Hermes-facing persistence adapters.

    This port is intentionally narrower than ``CirculatioRepository``. Phase 1 integrations
    may mirror Circulatio writes into Hermes profile storage for debugging or export, but the
    authoritative read/write repository contract remains ``CirculatioRepository``.
    """

    async def upsert_material(self, record: MaterialRecord) -> MaterialRecord: ...

    async def append_material_revision(self, revision: MaterialRevision) -> MaterialRevision: ...

    async def upsert_context_snapshot(self, snapshot: ContextSnapshot) -> ContextSnapshot: ...

    async def upsert_interpretation_run(
        self, run: InterpretationRunRecord
    ) -> InterpretationRunRecord: ...

    async def upsert_symbol(self, record: SymbolRecord) -> SymbolRecord: ...

    async def append_symbol_history(self, entry: SymbolHistoryEntry) -> SymbolHistoryEntry: ...

    async def upsert_pattern(self, record: PatternRecord) -> PatternRecord: ...

    async def append_pattern_history(self, entry: PatternHistoryEntry) -> PatternHistoryEntry: ...

    async def upsert_typology_lens(self, record: TypologyLensRecord) -> TypologyLensRecord: ...

    async def upsert_practice_session(
        self, record: PracticeSessionRecord
    ) -> PracticeSessionRecord: ...

    async def upsert_weekly_review(self, record: WeeklyReviewRecord) -> WeeklyReviewRecord: ...

    async def append_integration_record(self, record: IntegrationRecord) -> IntegrationRecord: ...

    async def store_evidence_items(
        self, user_id: Id, items: list[EvidenceItem]
    ) -> list[EvidenceItem]: ...
