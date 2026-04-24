from __future__ import annotations

import asyncio
import json
import logging
from collections.abc import Awaitable, Callable
from copy import deepcopy
from pathlib import Path
from typing import TypeVar

from ..domain.adaptation import UserAdaptationProfileRecord, UserAdaptationProfileUpdate
from ..domain.amplifications import (
    AmplificationPromptRecord,
    AmplificationPromptStatus,
    AmplificationPromptUpdate,
    PersonalAmplificationRecord,
    PersonalAmplificationUpdate,
)
from ..domain.clarifications import (
    ClarificationAnswerRecord,
    ClarificationAnswerUpdate,
    ClarificationPromptRecord,
    ClarificationPromptStatus,
    ClarificationPromptUpdate,
)
from ..domain.conscious_attitude import (
    ConsciousAttitudeSnapshotFilters,
    ConsciousAttitudeSnapshotRecord,
    ConsciousAttitudeSnapshotUpdate,
)
from ..domain.context import ContextSnapshot
from ..domain.culture import (
    CollectiveAmplificationRecord,
    CollectiveAmplificationUpdate,
    CulturalFrameRecord,
    CulturalFrameUpdate,
)
from ..domain.dream_series import (
    DreamSeriesMembershipRecord,
    DreamSeriesMembershipUpdate,
    DreamSeriesRecord,
    DreamSeriesUpdate,
)
from ..domain.errors import (
    PersistenceError,
    ProfileStorageConflictError,
    ProfileStorageCorruptionError,
)
from ..domain.feedback import InteractionFeedbackRecord
from ..domain.goals import GoalRecord, GoalTensionRecord, GoalTensionUpdate, GoalUpdate
from ..domain.graph import (
    DeleteGraphEntityRequest,
    GraphQuery,
    GraphQueryResult,
    ReviseGraphEntityRequest,
    SuppressHypothesisRequest,
    SymbolicMemorySnapshot,
)
from ..domain.individuation import (
    IndividuationRecord,
    IndividuationRecordStatus,
    IndividuationRecordType,
    IndividuationRecordUpdate,
)
from ..domain.integration import IntegrationRecord
from ..domain.interpretations import (
    InterpretationRunRecord,
    InterpretationRunUpdate,
    ProposalDecisionRecord,
)
from ..domain.journeys import JourneyRecord, JourneyUpdate
from ..domain.living_myth import (
    AnalysisPacketRecord,
    LivingMythRecord,
    LivingMythRecordStatus,
    LivingMythRecordType,
    LivingMythRecordUpdate,
    LivingMythReviewRecord,
    LivingMythReviewUpdate,
)
from ..domain.materials import MaterialListFilters, MaterialRecord, MaterialRevision, MaterialUpdate
from ..domain.memory import MemoryKernelSnapshot, MemoryRetrievalQuery
from ..domain.method_state import MethodStateCaptureRunRecord, MethodStateCaptureRunUpdate
from ..domain.patterns import PatternHistoryEntry, PatternRecord, PatternType, PatternUpdate
from ..domain.practices import PracticeSessionRecord, PracticeSessionStatus, PracticeSessionUpdate
from ..domain.presentation import RitualCompletionEvent
from ..domain.proactive import (
    ProactiveBriefRecord,
    ProactiveBriefStatus,
    ProactiveBriefType,
    ProactiveBriefUpdate,
)
from ..domain.readiness import ConsentPreferenceRecord, ConsentPreferenceUpdate
from ..domain.records import DeletionMode
from ..domain.reviews import DashboardSummary, WeeklyReviewRecord
from ..domain.soma import BodyStateRecord, BodyStateUpdate
from ..domain.symbols import SymbolHistoryEntry, SymbolRecord, SymbolUpdate
from ..domain.types import (
    AnalysisPacketInput,
    CirculationSummaryInput,
    EvidenceItem,
    HermesMemoryContext,
    Id,
    LifeContextSnapshot,
    LivingMythReviewInput,
    MemoryWritePlan,
    MethodContextSnapshot,
    RecordIntegrationInput,
    RecordIntegrationResult,
    SuppressedHypothesisSummary,
    ThreadDigest,
    ThresholdReviewInput,
)
from ..domain.typology import TypologyLensRecord, TypologyLensUpdate
from ..hermes.profile_paths import get_circulatio_db_path
from .circulatio_repository import CirculatioRepository
from .in_memory_bucket import UserCirculatioBucket
from .in_memory_circulatio_repository import InMemoryCirculatioRepository
from .sqlite_utils import (
    create_sqlite_connection,
    sqlite_transaction,
    table_exists,
    table_has_column,
)

T = TypeVar("T")

LOGGER = logging.getLogger(__name__)

_SCHEMA_VERSION = 1
_WRITE_CONFLICT_RETRIES = 3


class HermesProfileCirculatioRepository(CirculatioRepository):
    """Durable Circulatio repository stored in a profile-scoped SQLite DB.

    The repository persists a user bucket JSON blob per user. This keeps the
    existing service and in-memory helper logic intact while making the runtime
    durable across Hermes restarts.
    """

    def __init__(self, db_path: str | Path | None = None) -> None:
        self._db_path = Path(db_path) if db_path is not None else get_circulatio_db_path()
        self._connection = create_sqlite_connection(self._db_path)
        self._delegate = InMemoryCirculatioRepository()
        self._io_lock = asyncio.Lock()
        self._bucket_revisions: dict[Id, int] = {}
        self._corrupt_user_ids: dict[Id, str] = {}
        self._initialize_schema()
        self._load_all_buckets()

    @property
    def db_path(self) -> Path:
        return self._db_path

    def close(self) -> None:
        connection = getattr(self, "_connection", None)
        if connection is None:
            return
        try:
            connection.close()
        finally:
            self._connection = None

    def storage_health(self) -> dict[str, object]:
        return {
            "dbPath": str(self._db_path),
            "schemaVersion": self._schema_version(),
            "corruptUserIds": dict(self._corrupt_user_ids),
            "loadedUserCount": len(self._delegate._users),
        }

    async def create_material(self, record: MaterialRecord) -> MaterialRecord:
        return await self._write(record["userId"], lambda: self._delegate.create_material(record))

    async def get_material(
        self, user_id: Id, material_id: Id, *, include_deleted: bool = False
    ) -> MaterialRecord:
        return await self._read(
            lambda: self._delegate.get_material(
                user_id, material_id, include_deleted=include_deleted
            )
        )

    async def list_materials(
        self, user_id: Id, filters: MaterialListFilters | None = None
    ) -> list[MaterialRecord]:
        return await self._read(lambda: self._delegate.list_materials(user_id, filters))

    async def update_material(
        self, user_id: Id, material_id: Id, updates: MaterialUpdate
    ) -> MaterialRecord:
        return await self._write(
            user_id, lambda: self._delegate.update_material(user_id, material_id, updates)
        )

    async def create_material_revision(self, revision: MaterialRevision) -> MaterialRevision:
        return await self._write(
            revision["userId"], lambda: self._delegate.create_material_revision(revision)
        )

    async def list_material_revisions(self, user_id: Id, material_id: Id) -> list[MaterialRevision]:
        return await self._read(
            lambda: self._delegate.list_material_revisions(user_id, material_id)
        )

    async def delete_material(
        self, user_id: Id, material_id: Id, *, mode: DeletionMode, reason: str | None = None
    ) -> None:
        await self._write(
            user_id,
            lambda: self._delegate.delete_material(user_id, material_id, mode=mode, reason=reason),
        )

    async def create_context_snapshot(self, snapshot: ContextSnapshot) -> ContextSnapshot:
        return await self._write(
            snapshot["userId"], lambda: self._delegate.create_context_snapshot(snapshot)
        )

    async def get_context_snapshot(
        self, user_id: Id, snapshot_id: Id, *, include_deleted: bool = False
    ) -> ContextSnapshot:
        return await self._read(
            lambda: self._delegate.get_context_snapshot(
                user_id, snapshot_id, include_deleted=include_deleted
            )
        )

    async def list_context_snapshots(
        self,
        user_id: Id,
        *,
        material_id: Id | None = None,
        window_start: str | None = None,
        window_end: str | None = None,
    ) -> list[ContextSnapshot]:
        return await self._read(
            lambda: self._delegate.list_context_snapshots(
                user_id,
                material_id=material_id,
                window_start=window_start,
                window_end=window_end,
            )
        )

    async def delete_context_snapshot(
        self, user_id: Id, snapshot_id: Id, *, mode: DeletionMode
    ) -> None:
        await self._write(
            user_id, lambda: self._delegate.delete_context_snapshot(user_id, snapshot_id, mode=mode)
        )

    async def store_interpretation_run(
        self, run: InterpretationRunRecord
    ) -> InterpretationRunRecord:
        return await self._write(
            run["userId"], lambda: self._delegate.store_interpretation_run(run)
        )

    async def get_interpretation_run(self, user_id: Id, run_id: Id) -> InterpretationRunRecord:
        return await self._read(lambda: self._delegate.get_interpretation_run(user_id, run_id))

    async def list_interpretation_runs(
        self, user_id: Id, *, material_id: Id | None = None, limit: int = 20
    ) -> list[InterpretationRunRecord]:
        return await self._read(
            lambda: self._delegate.list_interpretation_runs(
                user_id, material_id=material_id, limit=limit
            )
        )

    async def update_interpretation_run(
        self, user_id: Id, run_id: Id, updates: InterpretationRunUpdate
    ) -> InterpretationRunRecord:
        return await self._write(
            user_id, lambda: self._delegate.update_interpretation_run(user_id, run_id, updates)
        )

    async def create_clarification_prompt(
        self, record: ClarificationPromptRecord
    ) -> ClarificationPromptRecord:
        return await self._write(
            record["userId"], lambda: self._delegate.create_clarification_prompt(record)
        )

    async def get_clarification_prompt(
        self, user_id: Id, prompt_id: Id, *, include_deleted: bool = False
    ) -> ClarificationPromptRecord:
        return await self._read(
            lambda: self._delegate.get_clarification_prompt(
                user_id,
                prompt_id,
                include_deleted=include_deleted,
            )
        )

    async def update_clarification_prompt(
        self, user_id: Id, prompt_id: Id, updates: ClarificationPromptUpdate
    ) -> ClarificationPromptRecord:
        return await self._write(
            user_id,
            lambda: self._delegate.update_clarification_prompt(user_id, prompt_id, updates),
        )

    async def list_clarification_prompts(
        self,
        user_id: Id,
        *,
        status: ClarificationPromptStatus | None = None,
        material_id: Id | None = None,
        run_id: Id | None = None,
        limit: int = 50,
    ) -> list[ClarificationPromptRecord]:
        return await self._read(
            lambda: self._delegate.list_clarification_prompts(
                user_id,
                status=status,
                material_id=material_id,
                run_id=run_id,
                limit=limit,
            )
        )

    async def create_clarification_answer(
        self, record: ClarificationAnswerRecord
    ) -> ClarificationAnswerRecord:
        return await self._write(
            record["userId"], lambda: self._delegate.create_clarification_answer(record)
        )

    async def get_clarification_answer(
        self, user_id: Id, answer_id: Id, *, include_deleted: bool = False
    ) -> ClarificationAnswerRecord:
        return await self._read(
            lambda: self._delegate.get_clarification_answer(
                user_id,
                answer_id,
                include_deleted=include_deleted,
            )
        )

    async def update_clarification_answer(
        self, user_id: Id, answer_id: Id, updates: ClarificationAnswerUpdate
    ) -> ClarificationAnswerRecord:
        return await self._write(
            user_id,
            lambda: self._delegate.update_clarification_answer(user_id, answer_id, updates),
        )

    async def list_clarification_answers(
        self,
        user_id: Id,
        *,
        prompt_id: Id | None = None,
        run_id: Id | None = None,
        limit: int = 50,
    ) -> list[ClarificationAnswerRecord]:
        return await self._read(
            lambda: self._delegate.list_clarification_answers(
                user_id,
                prompt_id=prompt_id,
                run_id=run_id,
                limit=limit,
            )
        )

    async def create_method_state_capture_run(
        self, record: MethodStateCaptureRunRecord
    ) -> MethodStateCaptureRunRecord:
        return await self._write(
            record["userId"], lambda: self._delegate.create_method_state_capture_run(record)
        )

    async def get_method_state_capture_run(
        self, user_id: Id, capture_run_id: Id, *, include_deleted: bool = False
    ) -> MethodStateCaptureRunRecord:
        return await self._read(
            lambda: self._delegate.get_method_state_capture_run(
                user_id,
                capture_run_id,
                include_deleted=include_deleted,
            )
        )

    async def get_method_state_capture_run_by_idempotency_key(
        self, user_id: Id, idempotency_key: str
    ) -> MethodStateCaptureRunRecord | None:
        return await self._read(
            lambda: self._delegate.get_method_state_capture_run_by_idempotency_key(
                user_id,
                idempotency_key,
            )
        )

    async def update_method_state_capture_run(
        self, user_id: Id, capture_run_id: Id, updates: MethodStateCaptureRunUpdate
    ) -> MethodStateCaptureRunRecord:
        return await self._write(
            user_id,
            lambda: self._delegate.update_method_state_capture_run(
                user_id, capture_run_id, updates
            ),
        )

    async def list_method_state_capture_runs(
        self, user_id: Id, *, limit: int = 50
    ) -> list[MethodStateCaptureRunRecord]:
        return await self._read(
            lambda: self._delegate.list_method_state_capture_runs(user_id, limit=limit)
        )

    async def store_evidence_items(
        self, user_id: Id, items: list[EvidenceItem]
    ) -> list[EvidenceItem]:
        return await self._write(
            user_id, lambda: self._delegate.store_evidence_items(user_id, items)
        )

    async def get_evidence_item(self, user_id: Id, evidence_id: Id) -> EvidenceItem:
        return await self._read(lambda: self._delegate.get_evidence_item(user_id, evidence_id))

    async def list_evidence_for_run(self, user_id: Id, run_id: Id) -> list[EvidenceItem]:
        return await self._read(lambda: self._delegate.list_evidence_for_run(user_id, run_id))

    async def create_symbol(self, record: SymbolRecord) -> SymbolRecord:
        return await self._write(record["userId"], lambda: self._delegate.create_symbol(record))

    async def get_symbol(
        self, user_id: Id, symbol_id: Id, *, include_deleted: bool = False
    ) -> SymbolRecord:
        return await self._read(
            lambda: self._delegate.get_symbol(user_id, symbol_id, include_deleted=include_deleted)
        )

    async def find_symbol_by_name(self, user_id: Id, canonical_name: str) -> SymbolRecord | None:
        return await self._read(lambda: self._delegate.find_symbol_by_name(user_id, canonical_name))

    async def list_symbols(
        self, user_id: Id, *, include_deleted: bool = False, limit: int = 50
    ) -> list[SymbolRecord]:
        return await self._read(
            lambda: self._delegate.list_symbols(
                user_id, include_deleted=include_deleted, limit=limit
            )
        )

    async def update_symbol(
        self, user_id: Id, symbol_id: Id, updates: SymbolUpdate
    ) -> SymbolRecord:
        return await self._write(
            user_id, lambda: self._delegate.update_symbol(user_id, symbol_id, updates)
        )

    async def append_symbol_history(self, entry: SymbolHistoryEntry) -> SymbolHistoryEntry:
        return await self._write(
            entry["userId"], lambda: self._delegate.append_symbol_history(entry)
        )

    async def list_symbol_history(
        self, user_id: Id, symbol_id: Id, *, limit: int = 50
    ) -> list[SymbolHistoryEntry]:
        return await self._read(
            lambda: self._delegate.list_symbol_history(user_id, symbol_id, limit=limit)
        )

    async def delete_symbol(
        self, user_id: Id, symbol_id: Id, *, mode: DeletionMode, reason: str | None = None
    ) -> None:
        await self._write(
            user_id,
            lambda: self._delegate.delete_symbol(user_id, symbol_id, mode=mode, reason=reason),
        )

    async def create_pattern(self, record: PatternRecord) -> PatternRecord:
        return await self._write(record["userId"], lambda: self._delegate.create_pattern(record))

    async def get_pattern(
        self, user_id: Id, pattern_id: Id, *, include_deleted: bool = False
    ) -> PatternRecord:
        return await self._read(
            lambda: self._delegate.get_pattern(user_id, pattern_id, include_deleted=include_deleted)
        )

    async def list_patterns(
        self,
        user_id: Id,
        *,
        pattern_type: PatternType | None = None,
        include_deleted: bool = False,
        limit: int = 50,
    ) -> list[PatternRecord]:
        return await self._read(
            lambda: self._delegate.list_patterns(
                user_id,
                pattern_type=pattern_type,
                include_deleted=include_deleted,
                limit=limit,
            )
        )

    async def update_pattern(
        self, user_id: Id, pattern_id: Id, updates: PatternUpdate
    ) -> PatternRecord:
        return await self._write(
            user_id, lambda: self._delegate.update_pattern(user_id, pattern_id, updates)
        )

    async def append_pattern_history(self, entry: PatternHistoryEntry) -> PatternHistoryEntry:
        return await self._write(
            entry["userId"], lambda: self._delegate.append_pattern_history(entry)
        )

    async def list_pattern_history(
        self, user_id: Id, pattern_id: Id, *, limit: int = 50
    ) -> list[PatternHistoryEntry]:
        return await self._read(
            lambda: self._delegate.list_pattern_history(user_id, pattern_id, limit=limit)
        )

    async def delete_pattern(
        self, user_id: Id, pattern_id: Id, *, mode: DeletionMode, reason: str | None = None
    ) -> None:
        await self._write(
            user_id,
            lambda: self._delegate.delete_pattern(user_id, pattern_id, mode=mode, reason=reason),
        )

    async def create_typology_lens(self, record: TypologyLensRecord) -> TypologyLensRecord:
        return await self._write(
            record["userId"], lambda: self._delegate.create_typology_lens(record)
        )

    async def get_typology_lens(
        self, user_id: Id, lens_id: Id, *, include_deleted: bool = False
    ) -> TypologyLensRecord:
        return await self._read(
            lambda: self._delegate.get_typology_lens(
                user_id, lens_id, include_deleted=include_deleted
            )
        )

    async def list_typology_lenses(
        self, user_id: Id, *, include_deleted: bool = False, limit: int = 20
    ) -> list[TypologyLensRecord]:
        return await self._read(
            lambda: self._delegate.list_typology_lenses(
                user_id, include_deleted=include_deleted, limit=limit
            )
        )

    async def update_typology_lens(
        self, user_id: Id, lens_id: Id, updates: TypologyLensUpdate
    ) -> TypologyLensRecord:
        return await self._write(
            user_id, lambda: self._delegate.update_typology_lens(user_id, lens_id, updates)
        )

    async def delete_typology_lens(
        self, user_id: Id, lens_id: Id, *, mode: DeletionMode, reason: str | None = None
    ) -> None:
        await self._write(
            user_id,
            lambda: self._delegate.delete_typology_lens(user_id, lens_id, mode=mode, reason=reason),
        )

    async def create_practice_session(self, record: PracticeSessionRecord) -> PracticeSessionRecord:
        return await self._write(
            record["userId"], lambda: self._delegate.create_practice_session(record)
        )

    async def get_practice_session(
        self, user_id: Id, practice_session_id: Id, *, include_deleted: bool = False
    ) -> PracticeSessionRecord:
        return await self._read(
            lambda: self._delegate.get_practice_session(
                user_id, practice_session_id, include_deleted=include_deleted
            )
        )

    async def list_practice_sessions(
        self,
        user_id: Id,
        *,
        material_id: Id | None = None,
        run_id: Id | None = None,
        statuses: list[PracticeSessionStatus] | None = None,
        since: str | None = None,
        include_deleted: bool = False,
        limit: int = 50,
    ) -> list[PracticeSessionRecord]:
        return await self._read(
            lambda: self._delegate.list_practice_sessions(
                user_id,
                material_id=material_id,
                run_id=run_id,
                statuses=statuses,
                since=since,
                include_deleted=include_deleted,
                limit=limit,
            )
        )

    async def update_practice_session(
        self, user_id: Id, practice_session_id: Id, updates: PracticeSessionUpdate
    ) -> PracticeSessionRecord:
        return await self._write(
            user_id,
            lambda: self._delegate.update_practice_session(user_id, practice_session_id, updates),
        )

    async def delete_practice_session(
        self, user_id: Id, practice_session_id: Id, *, mode: DeletionMode
    ) -> None:
        await self._write(
            user_id,
            lambda: self._delegate.delete_practice_session(user_id, practice_session_id, mode=mode),
        )

    async def create_weekly_review(self, record: WeeklyReviewRecord) -> WeeklyReviewRecord:
        return await self._write(
            record["userId"], lambda: self._delegate.create_weekly_review(record)
        )

    async def get_weekly_review(
        self, user_id: Id, review_id: Id, *, include_deleted: bool = False
    ) -> WeeklyReviewRecord:
        return await self._read(
            lambda: self._delegate.get_weekly_review(
                user_id, review_id, include_deleted=include_deleted
            )
        )

    async def list_weekly_reviews(
        self, user_id: Id, *, limit: int = 20
    ) -> list[WeeklyReviewRecord]:
        return await self._read(lambda: self._delegate.list_weekly_reviews(user_id, limit=limit))

    async def delete_weekly_review(self, user_id: Id, review_id: Id, *, mode: DeletionMode) -> None:
        await self._write(
            user_id, lambda: self._delegate.delete_weekly_review(user_id, review_id, mode=mode)
        )

    async def create_individuation_record(self, record: IndividuationRecord) -> IndividuationRecord:
        return await self._write(
            record["userId"], lambda: self._delegate.create_individuation_record(record)
        )

    async def update_individuation_record(
        self, user_id: Id, record_id: Id, updates: IndividuationRecordUpdate
    ) -> IndividuationRecord:
        return await self._write(
            user_id, lambda: self._delegate.update_individuation_record(user_id, record_id, updates)
        )

    async def get_individuation_record(
        self, user_id: Id, record_id: Id, *, include_deleted: bool = False
    ) -> IndividuationRecord:
        return await self._read(
            lambda: self._delegate.get_individuation_record(
                user_id, record_id, include_deleted=include_deleted
            )
        )

    async def list_individuation_records(
        self,
        user_id: Id,
        *,
        record_types: list[IndividuationRecordType] | None = None,
        statuses: list[IndividuationRecordStatus] | None = None,
        window_start: str | None = None,
        window_end: str | None = None,
        limit: int = 50,
    ) -> list[IndividuationRecord]:
        return await self._read(
            lambda: self._delegate.list_individuation_records(
                user_id,
                record_types=record_types,
                statuses=statuses,
                window_start=window_start,
                window_end=window_end,
                limit=limit,
            )
        )

    async def create_living_myth_record(self, record: LivingMythRecord) -> LivingMythRecord:
        return await self._write(
            record["userId"], lambda: self._delegate.create_living_myth_record(record)
        )

    async def update_living_myth_record(
        self, user_id: Id, record_id: Id, updates: LivingMythRecordUpdate
    ) -> LivingMythRecord:
        return await self._write(
            user_id, lambda: self._delegate.update_living_myth_record(user_id, record_id, updates)
        )

    async def get_living_myth_record(
        self, user_id: Id, record_id: Id, *, include_deleted: bool = False
    ) -> LivingMythRecord:
        return await self._read(
            lambda: self._delegate.get_living_myth_record(
                user_id, record_id, include_deleted=include_deleted
            )
        )

    async def list_living_myth_records(
        self,
        user_id: Id,
        *,
        record_types: list[LivingMythRecordType] | None = None,
        statuses: list[LivingMythRecordStatus] | None = None,
        window_start: str | None = None,
        window_end: str | None = None,
        limit: int = 50,
    ) -> list[LivingMythRecord]:
        return await self._read(
            lambda: self._delegate.list_living_myth_records(
                user_id,
                record_types=record_types,
                statuses=statuses,
                window_start=window_start,
                window_end=window_end,
                limit=limit,
            )
        )

    async def create_living_myth_review(
        self, record: LivingMythReviewRecord
    ) -> LivingMythReviewRecord:
        return await self._write(
            record["userId"], lambda: self._delegate.create_living_myth_review(record)
        )

    async def update_living_myth_review(
        self, user_id: Id, review_id: Id, updates: LivingMythReviewUpdate
    ) -> LivingMythReviewRecord:
        return await self._write(
            user_id, lambda: self._delegate.update_living_myth_review(user_id, review_id, updates)
        )

    async def get_living_myth_review(
        self, user_id: Id, review_id: Id, *, include_deleted: bool = False
    ) -> LivingMythReviewRecord:
        return await self._read(
            lambda: self._delegate.get_living_myth_review(
                user_id, review_id, include_deleted=include_deleted
            )
        )

    async def list_living_myth_reviews(
        self,
        user_id: Id,
        *,
        review_type: str | None = None,
        limit: int = 20,
    ) -> list[LivingMythReviewRecord]:
        return await self._read(
            lambda: self._delegate.list_living_myth_reviews(
                user_id, review_type=review_type, limit=limit
            )
        )

    async def create_analysis_packet(self, record: AnalysisPacketRecord) -> AnalysisPacketRecord:
        return await self._write(
            record["userId"], lambda: self._delegate.create_analysis_packet(record)
        )

    async def get_analysis_packet(
        self, user_id: Id, packet_id: Id, *, include_deleted: bool = False
    ) -> AnalysisPacketRecord:
        return await self._read(
            lambda: self._delegate.get_analysis_packet(
                user_id, packet_id, include_deleted=include_deleted
            )
        )

    async def list_analysis_packets(
        self, user_id: Id, *, limit: int = 20
    ) -> list[AnalysisPacketRecord]:
        return await self._read(lambda: self._delegate.list_analysis_packets(user_id, limit=limit))

    async def create_integration_record(self, record: IntegrationRecord) -> IntegrationRecord:
        return await self._write(
            record["userId"], lambda: self._delegate.create_integration_record(record)
        )

    async def get_integration_record(self, user_id: Id, integration_id: Id) -> IntegrationRecord:
        return await self._read(
            lambda: self._delegate.get_integration_record(user_id, integration_id)
        )

    async def list_integration_records(
        self,
        user_id: Id,
        *,
        run_id: Id | None = None,
        material_id: Id | None = None,
        limit: int = 50,
    ) -> list[IntegrationRecord]:
        return await self._read(
            lambda: self._delegate.list_integration_records(
                user_id,
                run_id=run_id,
                material_id=material_id,
                limit=limit,
            )
        )

    async def update_proposal_decisions(
        self, user_id: Id, run_id: Id, decisions: list[ProposalDecisionRecord]
    ) -> InterpretationRunRecord:
        return await self._write(
            user_id, lambda: self._delegate.update_proposal_decisions(user_id, run_id, decisions)
        )

    async def create_conscious_attitude_snapshot(
        self, record: ConsciousAttitudeSnapshotRecord
    ) -> ConsciousAttitudeSnapshotRecord:
        return await self._write(
            record["userId"], lambda: self._delegate.create_conscious_attitude_snapshot(record)
        )

    async def get_conscious_attitude_snapshot(
        self, user_id: Id, snapshot_id: Id, *, include_deleted: bool = False
    ) -> ConsciousAttitudeSnapshotRecord:
        return await self._read(
            lambda: self._delegate.get_conscious_attitude_snapshot(
                user_id, snapshot_id, include_deleted=include_deleted
            )
        )

    async def list_conscious_attitude_snapshots(
        self,
        user_id: Id,
        *,
        filters: ConsciousAttitudeSnapshotFilters | None = None,
    ) -> list[ConsciousAttitudeSnapshotRecord]:
        return await self._read(
            lambda: self._delegate.list_conscious_attitude_snapshots(user_id, filters=filters)
        )

    async def update_conscious_attitude_snapshot(
        self, user_id: Id, snapshot_id: Id, updates: ConsciousAttitudeSnapshotUpdate
    ) -> ConsciousAttitudeSnapshotRecord:
        return await self._write(
            user_id,
            lambda: self._delegate.update_conscious_attitude_snapshot(
                user_id, snapshot_id, updates
            ),
        )

    async def delete_conscious_attitude_snapshot(
        self, user_id: Id, snapshot_id: Id, *, mode: DeletionMode, reason: str | None = None
    ) -> None:
        await self._write(
            user_id,
            lambda: self._delegate.delete_conscious_attitude_snapshot(
                user_id, snapshot_id, mode=mode, reason=reason
            ),
        )

    async def create_amplification_prompt(
        self, record: AmplificationPromptRecord
    ) -> AmplificationPromptRecord:
        return await self._write(
            record["userId"], lambda: self._delegate.create_amplification_prompt(record)
        )

    async def get_amplification_prompt(
        self, user_id: Id, prompt_id: Id, *, include_deleted: bool = False
    ) -> AmplificationPromptRecord:
        return await self._read(
            lambda: self._delegate.get_amplification_prompt(
                user_id, prompt_id, include_deleted=include_deleted
            )
        )

    async def list_amplification_prompts(
        self,
        user_id: Id,
        *,
        material_id: Id | None = None,
        run_id: Id | None = None,
        symbol_id: Id | None = None,
        statuses: list[AmplificationPromptStatus] | None = None,
        limit: int = 50,
    ) -> list[AmplificationPromptRecord]:
        return await self._read(
            lambda: self._delegate.list_amplification_prompts(
                user_id,
                material_id=material_id,
                run_id=run_id,
                symbol_id=symbol_id,
                statuses=statuses,
                limit=limit,
            )
        )

    async def update_amplification_prompt(
        self, user_id: Id, prompt_id: Id, updates: AmplificationPromptUpdate
    ) -> AmplificationPromptRecord:
        return await self._write(
            user_id, lambda: self._delegate.update_amplification_prompt(user_id, prompt_id, updates)
        )

    async def create_personal_amplification(
        self, record: PersonalAmplificationRecord
    ) -> PersonalAmplificationRecord:
        return await self._write(
            record["userId"], lambda: self._delegate.create_personal_amplification(record)
        )

    async def get_personal_amplification(
        self, user_id: Id, amplification_id: Id, *, include_deleted: bool = False
    ) -> PersonalAmplificationRecord:
        return await self._read(
            lambda: self._delegate.get_personal_amplification(
                user_id, amplification_id, include_deleted=include_deleted
            )
        )

    async def list_personal_amplifications(
        self,
        user_id: Id,
        *,
        material_id: Id | None = None,
        run_id: Id | None = None,
        symbol_id: Id | None = None,
        limit: int = 50,
    ) -> list[PersonalAmplificationRecord]:
        return await self._read(
            lambda: self._delegate.list_personal_amplifications(
                user_id,
                material_id=material_id,
                run_id=run_id,
                symbol_id=symbol_id,
                limit=limit,
            )
        )

    async def update_personal_amplification(
        self, user_id: Id, amplification_id: Id, updates: PersonalAmplificationUpdate
    ) -> PersonalAmplificationRecord:
        return await self._write(
            user_id,
            lambda: self._delegate.update_personal_amplification(
                user_id, amplification_id, updates
            ),
        )

    async def delete_personal_amplification(
        self, user_id: Id, amplification_id: Id, *, mode: DeletionMode, reason: str | None = None
    ) -> None:
        await self._write(
            user_id,
            lambda: self._delegate.delete_personal_amplification(
                user_id, amplification_id, mode=mode, reason=reason
            ),
        )

    async def create_body_state(self, record: BodyStateRecord) -> BodyStateRecord:
        return await self._write(record["userId"], lambda: self._delegate.create_body_state(record))

    async def get_body_state(
        self, user_id: Id, body_state_id: Id, *, include_deleted: bool = False
    ) -> BodyStateRecord:
        return await self._read(
            lambda: self._delegate.get_body_state(
                user_id, body_state_id, include_deleted=include_deleted
            )
        )

    async def list_body_states(
        self,
        user_id: Id,
        *,
        material_id: Id | None = None,
        run_id: Id | None = None,
        limit: int = 50,
    ) -> list[BodyStateRecord]:
        return await self._read(
            lambda: self._delegate.list_body_states(
                user_id, material_id=material_id, run_id=run_id, limit=limit
            )
        )

    async def update_body_state(
        self, user_id: Id, body_state_id: Id, updates: BodyStateUpdate
    ) -> BodyStateRecord:
        return await self._write(
            user_id, lambda: self._delegate.update_body_state(user_id, body_state_id, updates)
        )

    async def delete_body_state(
        self, user_id: Id, body_state_id: Id, *, mode: DeletionMode, reason: str | None = None
    ) -> None:
        await self._write(
            user_id,
            lambda: self._delegate.delete_body_state(
                user_id, body_state_id, mode=mode, reason=reason
            ),
        )

    async def create_goal(self, record: GoalRecord) -> GoalRecord:
        return await self._write(record["userId"], lambda: self._delegate.create_goal(record))

    async def get_goal(
        self, user_id: Id, goal_id: Id, *, include_deleted: bool = False
    ) -> GoalRecord:
        return await self._read(
            lambda: self._delegate.get_goal(user_id, goal_id, include_deleted=include_deleted)
        )

    async def list_goals(
        self, user_id: Id, *, include_deleted: bool = False, limit: int = 50
    ) -> list[GoalRecord]:
        return await self._read(
            lambda: self._delegate.list_goals(user_id, include_deleted=include_deleted, limit=limit)
        )

    async def update_goal(self, user_id: Id, goal_id: Id, updates: GoalUpdate) -> GoalRecord:
        return await self._write(
            user_id, lambda: self._delegate.update_goal(user_id, goal_id, updates)
        )

    async def delete_goal(
        self, user_id: Id, goal_id: Id, *, mode: DeletionMode, reason: str | None = None
    ) -> None:
        await self._write(
            user_id, lambda: self._delegate.delete_goal(user_id, goal_id, mode=mode, reason=reason)
        )

    async def create_goal_tension(self, record: GoalTensionRecord) -> GoalTensionRecord:
        return await self._write(
            record["userId"], lambda: self._delegate.create_goal_tension(record)
        )

    async def get_goal_tension(
        self, user_id: Id, tension_id: Id, *, include_deleted: bool = False
    ) -> GoalTensionRecord:
        return await self._read(
            lambda: self._delegate.get_goal_tension(
                user_id, tension_id, include_deleted=include_deleted
            )
        )

    async def list_goal_tensions(
        self, user_id: Id, *, include_deleted: bool = False, limit: int = 50
    ) -> list[GoalTensionRecord]:
        return await self._read(
            lambda: self._delegate.list_goal_tensions(
                user_id, include_deleted=include_deleted, limit=limit
            )
        )

    async def update_goal_tension(
        self, user_id: Id, tension_id: Id, updates: GoalTensionUpdate
    ) -> GoalTensionRecord:
        return await self._write(
            user_id, lambda: self._delegate.update_goal_tension(user_id, tension_id, updates)
        )

    async def delete_goal_tension(
        self, user_id: Id, tension_id: Id, *, mode: DeletionMode, reason: str | None = None
    ) -> None:
        await self._write(
            user_id,
            lambda: self._delegate.delete_goal_tension(
                user_id, tension_id, mode=mode, reason=reason
            ),
        )

    async def create_dream_series(self, record: DreamSeriesRecord) -> DreamSeriesRecord:
        return await self._write(
            record["userId"], lambda: self._delegate.create_dream_series(record)
        )

    async def get_dream_series(
        self, user_id: Id, series_id: Id, *, include_deleted: bool = False
    ) -> DreamSeriesRecord:
        return await self._read(
            lambda: self._delegate.get_dream_series(
                user_id, series_id, include_deleted=include_deleted
            )
        )

    async def list_dream_series(
        self, user_id: Id, *, include_deleted: bool = False, limit: int = 50
    ) -> list[DreamSeriesRecord]:
        return await self._read(
            lambda: self._delegate.list_dream_series(
                user_id, include_deleted=include_deleted, limit=limit
            )
        )

    async def update_dream_series(
        self, user_id: Id, series_id: Id, updates: DreamSeriesUpdate
    ) -> DreamSeriesRecord:
        return await self._write(
            user_id, lambda: self._delegate.update_dream_series(user_id, series_id, updates)
        )

    async def delete_dream_series(
        self, user_id: Id, series_id: Id, *, mode: DeletionMode, reason: str | None = None
    ) -> None:
        await self._write(
            user_id,
            lambda: self._delegate.delete_dream_series(
                user_id, series_id, mode=mode, reason=reason
            ),
        )

    async def create_dream_series_membership(
        self, record: DreamSeriesMembershipRecord
    ) -> DreamSeriesMembershipRecord:
        return await self._write(
            record["userId"], lambda: self._delegate.create_dream_series_membership(record)
        )

    async def list_dream_series_memberships(
        self,
        user_id: Id,
        *,
        series_id: Id | None = None,
        material_id: Id | None = None,
        include_deleted: bool = False,
        limit: int = 50,
    ) -> list[DreamSeriesMembershipRecord]:
        return await self._read(
            lambda: self._delegate.list_dream_series_memberships(
                user_id,
                series_id=series_id,
                material_id=material_id,
                include_deleted=include_deleted,
                limit=limit,
            )
        )

    async def update_dream_series_membership(
        self, user_id: Id, membership_id: Id, updates: DreamSeriesMembershipUpdate
    ) -> DreamSeriesMembershipRecord:
        return await self._write(
            user_id,
            lambda: self._delegate.update_dream_series_membership(user_id, membership_id, updates),
        )

    async def create_cultural_frame(self, record: CulturalFrameRecord) -> CulturalFrameRecord:
        return await self._write(
            record["userId"], lambda: self._delegate.create_cultural_frame(record)
        )

    async def get_cultural_frame(
        self, user_id: Id, cultural_frame_id: Id, *, include_deleted: bool = False
    ) -> CulturalFrameRecord:
        return await self._read(
            lambda: self._delegate.get_cultural_frame(
                user_id, cultural_frame_id, include_deleted=include_deleted
            )
        )

    async def list_cultural_frames(
        self, user_id: Id, *, include_deleted: bool = False, limit: int = 50
    ) -> list[CulturalFrameRecord]:
        return await self._read(
            lambda: self._delegate.list_cultural_frames(
                user_id, include_deleted=include_deleted, limit=limit
            )
        )

    async def update_cultural_frame(
        self, user_id: Id, cultural_frame_id: Id, updates: CulturalFrameUpdate
    ) -> CulturalFrameRecord:
        return await self._write(
            user_id,
            lambda: self._delegate.update_cultural_frame(user_id, cultural_frame_id, updates),
        )

    async def create_collective_amplification(
        self, record: CollectiveAmplificationRecord
    ) -> CollectiveAmplificationRecord:
        return await self._write(
            record["userId"], lambda: self._delegate.create_collective_amplification(record)
        )

    async def list_collective_amplifications(
        self,
        user_id: Id,
        *,
        material_id: Id | None = None,
        run_id: Id | None = None,
        symbol_id: Id | None = None,
        limit: int = 50,
    ) -> list[CollectiveAmplificationRecord]:
        return await self._read(
            lambda: self._delegate.list_collective_amplifications(
                user_id,
                material_id=material_id,
                run_id=run_id,
                symbol_id=symbol_id,
                limit=limit,
            )
        )

    async def update_collective_amplification(
        self, user_id: Id, amplification_id: Id, updates: CollectiveAmplificationUpdate
    ) -> CollectiveAmplificationRecord:
        return await self._write(
            user_id,
            lambda: self._delegate.update_collective_amplification(
                user_id, amplification_id, updates
            ),
        )

    async def create_consent_preference(
        self, record: ConsentPreferenceRecord
    ) -> ConsentPreferenceRecord:
        return await self._write(
            record["userId"], lambda: self._delegate.create_consent_preference(record)
        )

    async def list_consent_preferences(
        self, user_id: Id, *, limit: int = 50
    ) -> list[ConsentPreferenceRecord]:
        return await self._read(
            lambda: self._delegate.list_consent_preferences(user_id, limit=limit)
        )

    async def update_consent_preference(
        self, user_id: Id, preference_id: Id, updates: ConsentPreferenceUpdate
    ) -> ConsentPreferenceRecord:
        return await self._write(
            user_id,
            lambda: self._delegate.update_consent_preference(user_id, preference_id, updates),
        )

    async def upsert_adaptation_profile(
        self, user_id: Id, record: UserAdaptationProfileRecord
    ) -> UserAdaptationProfileRecord:
        return await self._write(
            user_id, lambda: self._delegate.upsert_adaptation_profile(user_id, record)
        )

    async def get_adaptation_profile(self, user_id: Id) -> UserAdaptationProfileRecord | None:
        return await self._read(lambda: self._delegate.get_adaptation_profile(user_id))

    async def update_adaptation_profile(
        self, user_id: Id, profile_id: Id, updates: UserAdaptationProfileUpdate
    ) -> UserAdaptationProfileRecord:
        return await self._write(
            user_id,
            lambda: self._delegate.update_adaptation_profile(user_id, profile_id, updates),
        )

    async def create_interaction_feedback(
        self, record: InteractionFeedbackRecord
    ) -> InteractionFeedbackRecord:
        return await self._write(
            record["userId"], lambda: self._delegate.create_interaction_feedback(record)
        )

    async def list_interaction_feedback(
        self,
        user_id: Id,
        *,
        domain: str | None = None,
        target_id: Id | None = None,
        limit: int = 50,
    ) -> list[InteractionFeedbackRecord]:
        return await self._read(
            lambda: self._delegate.list_interaction_feedback(
                user_id,
                domain=domain,
                target_id=target_id,
                limit=limit,
            )
        )

    async def create_journey(self, record: JourneyRecord) -> JourneyRecord:
        return await self._write(record["userId"], lambda: self._delegate.create_journey(record))

    async def list_journeys(
        self, user_id: Id, *, include_deleted: bool = False, limit: int = 50
    ) -> list[JourneyRecord]:
        return await self._read(
            lambda: self._delegate.list_journeys(
                user_id, include_deleted=include_deleted, limit=limit
            )
        )

    async def get_journey(
        self, user_id: Id, journey_id: Id, *, include_deleted: bool = False
    ) -> JourneyRecord:
        return await self._read(
            lambda: self._delegate.get_journey(user_id, journey_id, include_deleted=include_deleted)
        )

    async def update_journey(
        self, user_id: Id, journey_id: Id, updates: JourneyUpdate
    ) -> JourneyRecord:
        return await self._write(
            user_id, lambda: self._delegate.update_journey(user_id, journey_id, updates)
        )

    async def create_proactive_brief(self, record: ProactiveBriefRecord) -> ProactiveBriefRecord:
        return await self._write(
            record["userId"], lambda: self._delegate.create_proactive_brief(record)
        )

    async def get_proactive_brief(
        self, user_id: Id, brief_id: Id, *, include_deleted: bool = False
    ) -> ProactiveBriefRecord:
        return await self._read(
            lambda: self._delegate.get_proactive_brief(
                user_id, brief_id, include_deleted=include_deleted
            )
        )

    async def list_proactive_briefs(
        self,
        user_id: Id,
        *,
        statuses: list[ProactiveBriefStatus] | None = None,
        brief_type: ProactiveBriefType | None = None,
        since: str | None = None,
        include_deleted: bool = False,
        limit: int = 50,
    ) -> list[ProactiveBriefRecord]:
        return await self._read(
            lambda: self._delegate.list_proactive_briefs(
                user_id,
                statuses=statuses,
                brief_type=brief_type,
                since=since,
                include_deleted=include_deleted,
                limit=limit,
            )
        )

    async def update_proactive_brief(
        self, user_id: Id, brief_id: Id, updates: ProactiveBriefUpdate
    ) -> ProactiveBriefRecord:
        return await self._write(
            user_id, lambda: self._delegate.update_proactive_brief(user_id, brief_id, updates)
        )

    async def create_ritual_completion_event(
        self, record: RitualCompletionEvent
    ) -> RitualCompletionEvent:
        return await self._write(
            record["userId"], lambda: self._delegate.create_ritual_completion_event(record)
        )

    async def get_ritual_completion_event_by_idempotency_key(
        self, user_id: Id, idempotency_key: str
    ) -> RitualCompletionEvent | None:
        return await self._read(
            lambda: self._delegate.get_ritual_completion_event_by_idempotency_key(
                user_id,
                idempotency_key,
            )
        )

    async def build_hermes_memory_context_from_records(
        self, user_id: Id, *, max_items: int | None = None
    ) -> HermesMemoryContext:
        return await self._read(
            lambda: self._delegate.build_hermes_memory_context_from_records(
                user_id, max_items=max_items
            )
        )

    async def build_memory_kernel_snapshot(
        self,
        user_id: Id,
        *,
        query: MemoryRetrievalQuery | None = None,
    ) -> MemoryKernelSnapshot:
        return await self._read(
            lambda: self._delegate.build_memory_kernel_snapshot(user_id, query=query)
        )

    async def query_graph(
        self,
        user_id: Id,
        *,
        query: GraphQuery | None = None,
    ) -> GraphQueryResult:
        return await self._read(lambda: self._delegate.query_graph(user_id, query=query))

    async def build_life_context_snapshot_from_records(
        self,
        user_id: Id,
        *,
        window_start: str,
        window_end: str,
        exclude_material_id: Id | None = None,
    ) -> LifeContextSnapshot | None:
        return await self._read(
            lambda: self._delegate.build_life_context_snapshot_from_records(
                user_id,
                window_start=window_start,
                window_end=window_end,
                exclude_material_id=exclude_material_id,
            )
        )

    async def build_method_context_snapshot_from_records(
        self,
        user_id: Id,
        *,
        window_start: str,
        window_end: str,
        material_id: Id | None = None,
    ) -> MethodContextSnapshot | None:
        return await self._read(
            lambda: self._delegate.build_method_context_snapshot_from_records(
                user_id,
                window_start=window_start,
                window_end=window_end,
                material_id=material_id,
            )
        )

    async def build_circulation_summary_input(
        self,
        user_id: Id,
        *,
        window_start: str,
        window_end: str,
    ) -> CirculationSummaryInput:
        return await self._read(
            lambda: self._delegate.build_circulation_summary_input(
                user_id,
                window_start=window_start,
                window_end=window_end,
            )
        )

    async def build_thread_digests_from_records(
        self,
        user_id: Id,
        *,
        window_start: str,
        window_end: str,
        material_id: Id | None = None,
    ) -> list[ThreadDigest]:
        return await self._read(
            lambda: self._delegate.build_thread_digests_from_records(
                user_id,
                window_start=window_start,
                window_end=window_end,
                material_id=material_id,
            )
        )

    async def build_threshold_review_input(
        self,
        user_id: Id,
        *,
        window_start: str,
        window_end: str,
        threshold_process_id: Id | None = None,
        explicit_question: str | None = None,
    ) -> ThresholdReviewInput:
        return await self._read(
            lambda: self._delegate.build_threshold_review_input(
                user_id,
                window_start=window_start,
                window_end=window_end,
                threshold_process_id=threshold_process_id,
                explicit_question=explicit_question,
            )
        )

    async def build_living_myth_review_input(
        self,
        user_id: Id,
        *,
        window_start: str,
        window_end: str,
        explicit_question: str | None = None,
    ) -> LivingMythReviewInput:
        return await self._read(
            lambda: self._delegate.build_living_myth_review_input(
                user_id,
                window_start=window_start,
                window_end=window_end,
                explicit_question=explicit_question,
            )
        )

    async def build_analysis_packet_input(
        self,
        user_id: Id,
        *,
        window_start: str,
        window_end: str,
        packet_focus: str | None = None,
        explicit_question: str | None = None,
    ) -> AnalysisPacketInput:
        return await self._read(
            lambda: self._delegate.build_analysis_packet_input(
                user_id,
                window_start=window_start,
                window_end=window_end,
                packet_focus=packet_focus,
                explicit_question=explicit_question,
            )
        )

    async def get_dashboard_summary(self, user_id: Id) -> DashboardSummary:
        return await self._read(lambda: self._delegate.get_dashboard_summary(user_id))

    async def get_hermes_memory_context(
        self, user_id: Id, *, max_items: int | None = None
    ) -> HermesMemoryContext:
        return await self._read(
            lambda: self._delegate.get_hermes_memory_context(user_id, max_items=max_items)
        )

    async def get_symbolic_memory_snapshot(
        self, user_id: Id, *, max_items: int | None = None
    ) -> SymbolicMemorySnapshot:
        return await self._read(
            lambda: self._delegate.get_symbolic_memory_snapshot(user_id, max_items=max_items)
        )

    async def apply_approved_proposals(
        self, *, user_id: Id, memory_write_plan: MemoryWritePlan, approved_proposal_ids: list[Id]
    ) -> dict[str, list[Id]]:
        return await self._write(
            user_id,
            lambda: self._delegate.apply_approved_proposals(
                user_id=user_id,
                memory_write_plan=memory_write_plan,
                approved_proposal_ids=approved_proposal_ids,
            ),
        )

    async def record_integration(
        self, input_data: RecordIntegrationInput
    ) -> RecordIntegrationResult:
        return await self._write(
            input_data["userId"], lambda: self._delegate.record_integration(input_data)
        )

    async def suppress_hypothesis(
        self, request: SuppressHypothesisRequest
    ) -> SuppressedHypothesisSummary:
        return await self._write(
            str(request["userId"]), lambda: self._delegate.suppress_hypothesis(request)
        )

    async def revise_entity(self, request: ReviseGraphEntityRequest) -> None:
        await self._write(str(request["userId"]), lambda: self._delegate.revise_entity(request))

    async def delete_entity(self, request: DeleteGraphEntityRequest) -> None:
        await self._write(str(request["userId"]), lambda: self._delegate.delete_entity(request))

    async def _read(self, call: Callable[[], Awaitable[T]]) -> T:
        async with self._io_lock:
            inferred_user_id = _infer_user_id(call)
            if inferred_user_id is not None:
                self._ensure_user_storage_available(inferred_user_id)
            return await call()

    async def _write(self, user_id: Id, call: Callable[[], Awaitable[T]]) -> T:
        async with self._io_lock:
            last_conflict: ProfileStorageConflictError | None = None
            for attempt in range(_WRITE_CONFLICT_RETRIES + 1):
                self._ensure_user_storage_available(user_id)
                had_bucket = user_id in self._delegate._users
                previous_bucket = deepcopy(self._delegate._users[user_id]) if had_bucket else None
                previous_revision = self._bucket_revisions.get(user_id, 0)
                try:
                    result = await call()
                    bucket = self._delegate._bucket(user_id)
                    payload_json = _serialize_bucket(bucket)
                    self._persist_serialized_user(
                        user_id,
                        payload_json=payload_json,
                        expected_revision=previous_revision,
                        insert_new=not had_bucket,
                    )
                    return result
                except ProfileStorageConflictError as exc:
                    last_conflict = exc
                    self._restore_user_snapshot(
                        user_id,
                        bucket=previous_bucket,
                        revision=previous_revision,
                        had_bucket=had_bucket,
                    )
                    self._reload_user_from_storage(user_id)
                    if attempt >= _WRITE_CONFLICT_RETRIES:
                        LOGGER.warning(
                            "Circulatio profile write conflict exhausted retries for user_id=%s",
                            user_id,
                        )
                        raise
                    LOGGER.info(
                        "Circulatio profile write conflict; retrying user_id=%s attempt=%s",
                        user_id,
                        attempt + 1,
                    )
                    await asyncio.sleep(0.025 * (2**attempt))
                except Exception:
                    self._restore_user_snapshot(
                        user_id,
                        bucket=previous_bucket,
                        revision=previous_revision,
                        had_bucket=had_bucket,
                    )
                    raise
            if last_conflict is not None:
                raise last_conflict
            raise PersistenceError("Circulatio storage write failed without a recorded cause.")

    def _initialize_schema(self) -> None:
        with sqlite_transaction(
            self._connection,
            db_path=self._db_path,
            action="initialize Circulatio storage",
            immediate=True,
        ):
            self._connection.execute(
                """
                CREATE TABLE IF NOT EXISTS circulatio_schema_version (
                    version INTEGER NOT NULL
                )
                """
            )
            self._connection.execute(
                """
                CREATE TABLE IF NOT EXISTS circulatio_user_buckets (
                    user_id TEXT PRIMARY KEY,
                    payload_json TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )
            if not table_has_column(self._connection, "circulatio_user_buckets", "revision"):
                self._connection.execute(
                    "ALTER TABLE circulatio_user_buckets "
                    "ADD COLUMN revision INTEGER NOT NULL DEFAULT 0"
                )
            row = self._connection.execute(
                "SELECT version FROM circulatio_schema_version ORDER BY rowid DESC LIMIT 1"
            ).fetchone()
            if row is None:
                self._connection.execute(
                    "INSERT INTO circulatio_schema_version(version) VALUES (?)",
                    (_SCHEMA_VERSION,),
                )
                return
            version = int(row["version"])
            if version > _SCHEMA_VERSION:
                raise PersistenceError(
                    "Circulatio storage schema version "
                    f"{version} is newer than supported version "
                    f"{_SCHEMA_VERSION}."
                )
            if version < _SCHEMA_VERSION:
                self._connection.execute(
                    "UPDATE circulatio_schema_version SET version = ?",
                    (_SCHEMA_VERSION,),
                )

    def _schema_version(self) -> int:
        if not table_exists(self._connection, "circulatio_schema_version"):
            return 0
        row = self._connection.execute(
            "SELECT version FROM circulatio_schema_version ORDER BY rowid DESC LIMIT 1"
        ).fetchone()
        if row is None:
            return 0
        return int(row["version"])

    def _load_all_buckets(self) -> None:
        rows = self._connection.execute(
            "SELECT user_id, payload_json, revision FROM circulatio_user_buckets"
        ).fetchall()
        for row in rows:
            user_id = str(row["user_id"])
            try:
                payload = json.loads(str(row["payload_json"]))
                if not isinstance(payload, dict):
                    raise ValueError("Stored payload is not a JSON object.")
                self._delegate._users[user_id] = _bucket_from_payload(payload)
                self._bucket_revisions[user_id] = int(row["revision"] or 0)
                self._corrupt_user_ids.pop(user_id, None)
            except (json.JSONDecodeError, TypeError, ValueError) as exc:
                self._delegate._users.pop(user_id, None)
                self._bucket_revisions.pop(user_id, None)
                self._corrupt_user_ids[user_id] = str(exc)

    def _ensure_user_storage_available(self, user_id: Id) -> None:
        if user_id in self._corrupt_user_ids:
            raise ProfileStorageCorruptionError(
                "Circulatio storage for user "
                f"{user_id} is corrupt and must be repaired before it can be used."
            )

    def _persist_serialized_user(
        self,
        user_id: Id,
        *,
        payload_json: str,
        expected_revision: int,
        insert_new: bool,
    ) -> None:
        next_revision = 1 if insert_new else expected_revision + 1
        try:
            with sqlite_transaction(
                self._connection,
                db_path=self._db_path,
                action=f"persist Circulatio bucket for {user_id}",
                immediate=True,
            ):
                if insert_new:
                    cursor = self._connection.execute(
                        """
                        INSERT INTO circulatio_user_buckets(
                            user_id,
                            payload_json,
                            revision,
                            updated_at
                        )
                        VALUES (?, ?, ?, datetime('now'))
                        ON CONFLICT(user_id) DO NOTHING
                        """,
                        (user_id, payload_json, next_revision),
                    )
                else:
                    cursor = self._connection.execute(
                        """
                        UPDATE circulatio_user_buckets
                        SET payload_json = ?, revision = ?, updated_at = datetime('now')
                        WHERE user_id = ? AND revision = ?
                        """,
                        (payload_json, next_revision, user_id, expected_revision),
                    )
                if cursor.rowcount == 0:
                    raise ProfileStorageConflictError(
                        "Circulatio storage for user "
                        f"{user_id} changed concurrently. Retry the request."
                    )
        except ProfileStorageConflictError:
            raise
        except PersistenceError:
            raise
        self._bucket_revisions[user_id] = next_revision

    def _reload_user_from_storage(self, user_id: Id) -> None:
        row = self._connection.execute(
            "SELECT payload_json, revision FROM circulatio_user_buckets WHERE user_id = ?",
            (user_id,),
        ).fetchone()
        if row is None:
            self._delegate._users.pop(user_id, None)
            self._bucket_revisions.pop(user_id, None)
            self._corrupt_user_ids.pop(user_id, None)
            return
        try:
            payload = json.loads(str(row["payload_json"]))
            if not isinstance(payload, dict):
                raise ValueError("Stored payload is not a JSON object.")
            self._delegate._users[user_id] = _bucket_from_payload(payload)
            self._bucket_revisions[user_id] = int(row["revision"] or 0)
            self._corrupt_user_ids.pop(user_id, None)
        except (json.JSONDecodeError, TypeError, ValueError) as exc:
            self._delegate._users.pop(user_id, None)
            self._bucket_revisions.pop(user_id, None)
            self._corrupt_user_ids[user_id] = str(exc)
            raise ProfileStorageCorruptionError(
                f"Circulatio storage for user {user_id} is corrupt and could not be reloaded."
            ) from exc

    def _restore_user_snapshot(
        self,
        user_id: Id,
        *,
        bucket: UserCirculatioBucket | None,
        revision: int,
        had_bucket: bool,
    ) -> None:
        if had_bucket and bucket is not None:
            self._delegate._users[user_id] = bucket
            self._bucket_revisions[user_id] = revision
            return
        self._delegate._users.pop(user_id, None)
        self._bucket_revisions.pop(user_id, None)


def _serialize_bucket(bucket: UserCirculatioBucket) -> str:
    try:
        return json.dumps(
            _bucket_to_payload(bucket), sort_keys=True, separators=(",", ":"), default=str
        )
    except (TypeError, ValueError) as exc:
        raise PersistenceError(
            "Circulatio could not serialize profile storage for persistence."
        ) from exc


def _bucket_to_payload(bucket: UserCirculatioBucket) -> dict[str, object]:
    return {
        "materials": deepcopy(bucket.materials),
        "material_revisions": deepcopy(bucket.material_revisions),
        "material_summaries": deepcopy(bucket.material_summaries),
        "context_snapshots": deepcopy(bucket.context_snapshots),
        "interpretation_runs": deepcopy(bucket.interpretation_runs),
        "clarification_prompts": deepcopy(bucket.clarification_prompts),
        "clarification_answers": deepcopy(bucket.clarification_answers),
        "method_state_capture_runs": deepcopy(bucket.method_state_capture_runs),
        "evidence": deepcopy(bucket.evidence),
        "symbols": deepcopy(bucket.symbols),
        "symbol_name_index": deepcopy(bucket.symbol_name_index),
        "symbol_history": deepcopy(bucket.symbol_history),
        "patterns": deepcopy(bucket.patterns),
        "pattern_history": deepcopy(bucket.pattern_history),
        "typology_lenses": deepcopy(bucket.typology_lenses),
        "practice_sessions": deepcopy(bucket.practice_sessions),
        "integrations": deepcopy(bucket.integrations),
        "weekly_reviews": deepcopy(bucket.weekly_reviews),
        "individuation_records": deepcopy(bucket.individuation_records),
        "living_myth_records": deepcopy(bucket.living_myth_records),
        "living_myth_reviews": deepcopy(bucket.living_myth_reviews),
        "analysis_packets": deepcopy(bucket.analysis_packets),
        "conscious_attitudes": deepcopy(bucket.conscious_attitudes),
        "amplification_prompts": deepcopy(bucket.amplification_prompts),
        "personal_amplifications": deepcopy(bucket.personal_amplifications),
        "body_states": deepcopy(bucket.body_states),
        "goals": deepcopy(bucket.goals),
        "goal_tensions": deepcopy(bucket.goal_tensions),
        "dream_series": deepcopy(bucket.dream_series),
        "dream_series_memberships": deepcopy(bucket.dream_series_memberships),
        "cultural_frames": deepcopy(bucket.cultural_frames),
        "collective_amplifications": deepcopy(bucket.collective_amplifications),
        "consent_preferences": deepcopy(bucket.consent_preferences),
        "adaptation_profiles": deepcopy(bucket.adaptation_profiles),
        "journeys": deepcopy(bucket.journeys),
        "proactive_briefs": deepcopy(bucket.proactive_briefs),
        "ritual_completion_events": deepcopy(bucket.ritual_completion_events),
        "feedback": deepcopy(bucket.feedback),
        "interaction_feedback": deepcopy(bucket.interaction_feedback),
        "cultural_origins": deepcopy(bucket.cultural_origins),
        "suppressed": deepcopy(bucket.suppressed),
        "applied_proposal_ids": sorted(bucket.applied_proposal_ids),
    }


def _bucket_from_payload(payload: dict[str, object]) -> UserCirculatioBucket:
    return UserCirculatioBucket(
        materials=deepcopy(payload.get("materials", {})),
        material_revisions=deepcopy(payload.get("material_revisions", {})),
        material_summaries=deepcopy(payload.get("material_summaries", {})),
        context_snapshots=deepcopy(payload.get("context_snapshots", {})),
        interpretation_runs=deepcopy(payload.get("interpretation_runs", {})),
        clarification_prompts=deepcopy(payload.get("clarification_prompts", {})),
        clarification_answers=deepcopy(payload.get("clarification_answers", {})),
        method_state_capture_runs=deepcopy(payload.get("method_state_capture_runs", {})),
        evidence=deepcopy(payload.get("evidence", {})),
        symbols=deepcopy(payload.get("symbols", {})),
        symbol_name_index=deepcopy(payload.get("symbol_name_index", {})),
        symbol_history=deepcopy(payload.get("symbol_history", {})),
        patterns=deepcopy(payload.get("patterns", {})),
        pattern_history=deepcopy(payload.get("pattern_history", {})),
        typology_lenses=deepcopy(payload.get("typology_lenses", {})),
        practice_sessions=deepcopy(payload.get("practice_sessions", {})),
        integrations=deepcopy(payload.get("integrations", {})),
        weekly_reviews=deepcopy(payload.get("weekly_reviews", {})),
        individuation_records=deepcopy(payload.get("individuation_records", {})),
        living_myth_records=deepcopy(payload.get("living_myth_records", {})),
        living_myth_reviews=deepcopy(payload.get("living_myth_reviews", {})),
        analysis_packets=deepcopy(payload.get("analysis_packets", {})),
        conscious_attitudes=deepcopy(payload.get("conscious_attitudes", {})),
        amplification_prompts=deepcopy(payload.get("amplification_prompts", {})),
        personal_amplifications=deepcopy(payload.get("personal_amplifications", {})),
        body_states=deepcopy(payload.get("body_states", {})),
        goals=deepcopy(payload.get("goals", {})),
        goal_tensions=deepcopy(payload.get("goal_tensions", {})),
        dream_series=deepcopy(payload.get("dream_series", {})),
        dream_series_memberships=deepcopy(payload.get("dream_series_memberships", {})),
        cultural_frames=deepcopy(payload.get("cultural_frames", {})),
        collective_amplifications=deepcopy(payload.get("collective_amplifications", {})),
        consent_preferences=deepcopy(payload.get("consent_preferences", {})),
        adaptation_profiles=deepcopy(payload.get("adaptation_profiles", {})),
        journeys=deepcopy(payload.get("journeys", {})),
        proactive_briefs=deepcopy(payload.get("proactive_briefs", {})),
        ritual_completion_events=deepcopy(payload.get("ritual_completion_events", {})),
        feedback=deepcopy(payload.get("feedback", [])),
        interaction_feedback=deepcopy(payload.get("interaction_feedback", [])),
        cultural_origins=deepcopy(payload.get("cultural_origins", [])),
        suppressed=deepcopy(payload.get("suppressed", {})),
        applied_proposal_ids=set(payload.get("applied_proposal_ids", [])),
    )


def _infer_user_id(call: Callable[[], Awaitable[object]]) -> Id | None:
    closure = getattr(call, "__closure__", None)
    freevars = getattr(call, "__code__", None)
    if closure is None or freevars is None:
        return None
    for name, cell in zip(freevars.co_freevars, closure, strict=False):
        if name == "user_id":
            value = cell.cell_contents
            return str(value)
    return None
