from __future__ import annotations

import asyncio
from copy import deepcopy

from ..domain.adaptation import UserAdaptationProfileRecord, UserAdaptationProfileUpdate
from ..domain.amplifications import (
    AmplificationPromptRecord,
    AmplificationPromptStatus,
    AmplificationPromptUpdate,
    PersonalAmplificationRecord,
    PersonalAmplificationUpdate,
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
from ..domain.errors import ConflictError, EntityNotFoundError
from ..domain.goals import GoalRecord, GoalTensionRecord, GoalTensionUpdate, GoalUpdate
from ..domain.graph import (
    DeleteGraphEntityRequest,
    GraphQuery,
    GraphQueryResult,
    ReviseGraphEntityRequest,
    SuppressHypothesisRequest,
    SymbolicMemorySnapshot,
)
from ..domain.ids import create_id, now_iso
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
from ..domain.patterns import PatternHistoryEntry, PatternRecord, PatternType, PatternUpdate
from ..domain.practices import PracticeSessionRecord, PracticeSessionStatus, PracticeSessionUpdate
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
    ThresholdReviewInput,
)
from ..domain.typology import TypologyLensRecord, TypologyLensUpdate
from .circulatio_repository import CirculatioRepository
from .in_memory_bucket import UserCirculatioBucket
from .in_memory_projections import (
    build_analysis_packet_input_locked,
    build_circulation_summary_input_locked,
    build_dashboard_summary_locked,
    build_life_context_snapshot_locked,
    build_living_myth_review_input_locked,
    build_memory_context_locked,
    build_memory_kernel_snapshot_locked,
    build_method_context_snapshot_locked,
    build_symbolic_memory_snapshot_locked,
    build_threshold_review_input_locked,
    query_graph_locked,
)
from .in_memory_proposals import (
    append_pattern_history_locked,
    append_symbol_history_locked,
    apply_approved_proposals_locked,
    merge_decisions,
    proposal_action,
    proposal_entity_type,
)
from .in_memory_record_ops import (
    ensure_unique,
    get_visible,
    suppress_hypothesis_locked,
    tombstone_record,
)


class InMemoryCirculatioRepository(CirculatioRepository):
    def __init__(self) -> None:
        self._users: dict[Id, UserCirculatioBucket] = {}
        self._lock = asyncio.Lock()

    async def create_material(self, record: MaterialRecord) -> MaterialRecord:
        async with self._lock:
            bucket = self._bucket(record["userId"])
            ensure_unique(bucket.materials, record["id"], "material")
            bucket.materials[record["id"]] = deepcopy(record)
            return deepcopy(record)

    async def get_material(
        self, user_id: Id, material_id: Id, *, include_deleted: bool = False
    ) -> MaterialRecord:
        async with self._lock:
            return deepcopy(
                get_visible(
                    store=self._bucket(user_id).materials,
                    record_id=material_id,
                    include_deleted=include_deleted,
                    label="material",
                )
            )

    async def list_materials(
        self, user_id: Id, filters: MaterialListFilters | None = None
    ) -> list[MaterialRecord]:
        async with self._lock:
            bucket = self._bucket(user_id)
            criteria = filters or {}
            include_deleted = bool(criteria.get("includeDeleted", False))
            material_types = set(criteria.get("materialTypes", []))
            statuses = set(criteria.get("statuses", []))
            tags = set(criteria.get("tags", []))
            records = []
            for record in bucket.materials.values():
                if record.get("status") == "deleted" and not include_deleted:
                    continue
                if material_types and record["materialType"] not in material_types:
                    continue
                if statuses and record.get("status") not in statuses:
                    continue
                if tags and not tags.intersection(record.get("tags", [])):
                    continue
                records.append(deepcopy(record))
            records.sort(
                key=lambda item: (item.get("materialDate", ""), item.get("createdAt", "")),
                reverse=True,
            )
            limit = criteria.get("limit")
            if limit is not None:
                records = records[:limit]
            return records

    async def update_material(
        self, user_id: Id, material_id: Id, updates: MaterialUpdate
    ) -> MaterialRecord:
        async with self._lock:
            bucket = self._bucket(user_id)
            record = get_visible(
                store=bucket.materials,
                record_id=material_id,
                include_deleted=True,
                label="material",
            )
            record.update(deepcopy(updates))
            return deepcopy(record)

    async def create_material_revision(self, revision: MaterialRevision) -> MaterialRevision:
        async with self._lock:
            bucket = self._bucket(revision["userId"])
            get_visible(
                store=bucket.materials,
                record_id=revision["materialId"],
                include_deleted=True,
                label="material",
            )
            bucket.material_revisions.setdefault(revision["materialId"], []).append(
                deepcopy(revision)
            )
            return deepcopy(revision)

    async def list_material_revisions(self, user_id: Id, material_id: Id) -> list[MaterialRevision]:
        async with self._lock:
            bucket = self._bucket(user_id)
            get_visible(
                store=bucket.materials,
                record_id=material_id,
                include_deleted=True,
                label="material",
            )
            revisions = bucket.material_revisions.get(material_id, [])
            return [
                deepcopy(item)
                for item in sorted(revisions, key=lambda item: item["revisionNumber"], reverse=True)
            ]

    async def delete_material(
        self, user_id: Id, material_id: Id, *, mode: DeletionMode, reason: str | None = None
    ) -> None:
        del reason
        async with self._lock:
            bucket = self._bucket(user_id)
            record = get_visible(
                store=bucket.materials,
                record_id=material_id,
                include_deleted=True,
                label="material",
            )
            tombstone_record(record, mode=mode, erase_fields=("text", "summary"))
            summary = bucket.material_summaries.get(material_id)
            if summary and mode == "erase":
                summary["summary"] = ""
                summary["symbolNames"] = []
                summary["themeLabels"] = []

    async def create_context_snapshot(self, snapshot: ContextSnapshot) -> ContextSnapshot:
        async with self._lock:
            bucket = self._bucket(snapshot["userId"])
            ensure_unique(bucket.context_snapshots, snapshot["id"], "context snapshot")
            bucket.context_snapshots[snapshot["id"]] = deepcopy(snapshot)
            return deepcopy(snapshot)

    async def get_context_snapshot(
        self, user_id: Id, snapshot_id: Id, *, include_deleted: bool = False
    ) -> ContextSnapshot:
        async with self._lock:
            return deepcopy(
                get_visible(
                    store=self._bucket(user_id).context_snapshots,
                    record_id=snapshot_id,
                    include_deleted=include_deleted,
                    label="context snapshot",
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
        async with self._lock:
            bucket = self._bucket(user_id)
            items: list[ContextSnapshot] = []
            for snapshot in bucket.context_snapshots.values():
                if snapshot.get("status") == "deleted":
                    continue
                if material_id and material_id not in snapshot.get("relatedMaterialIds", []):
                    continue
                if (
                    window_start
                    and snapshot.get("windowEnd")
                    and snapshot["windowEnd"] < window_start
                ):
                    continue
                if (
                    window_end
                    and snapshot.get("windowStart")
                    and snapshot["windowStart"] > window_end
                ):
                    continue
                items.append(deepcopy(snapshot))
            items.sort(key=lambda item: item.get("createdAt", ""), reverse=True)
            return items

    async def delete_context_snapshot(
        self, user_id: Id, snapshot_id: Id, *, mode: DeletionMode
    ) -> None:
        async with self._lock:
            bucket = self._bucket(user_id)
            snapshot = get_visible(
                store=bucket.context_snapshots,
                record_id=snapshot_id,
                include_deleted=True,
                label="context snapshot",
            )
            tombstone_record(snapshot, mode=mode, erase_fields=("summary",))
            if mode == "erase":
                snapshot.pop("sessionContext", None)
                snapshot.pop("lifeContextSnapshot", None)

    async def store_interpretation_run(
        self, run: InterpretationRunRecord
    ) -> InterpretationRunRecord:
        async with self._lock:
            bucket = self._bucket(run["userId"])
            ensure_unique(bucket.interpretation_runs, run["id"], "interpretation run")
            bucket.interpretation_runs[run["id"]] = deepcopy(run)
            return deepcopy(run)

    async def get_interpretation_run(self, user_id: Id, run_id: Id) -> InterpretationRunRecord:
        async with self._lock:
            return deepcopy(
                get_visible(
                    store=self._bucket(user_id).interpretation_runs,
                    record_id=run_id,
                    include_deleted=True,
                    label="interpretation run",
                )
            )

    async def list_interpretation_runs(
        self, user_id: Id, *, material_id: Id | None = None, limit: int = 20
    ) -> list[InterpretationRunRecord]:
        async with self._lock:
            bucket = self._bucket(user_id)
            runs = [
                deepcopy(item)
                for item in bucket.interpretation_runs.values()
                if material_id is None or item["materialId"] == material_id
            ]
            runs.sort(key=lambda item: item.get("createdAt", ""), reverse=True)
            return runs[:limit]

    async def update_interpretation_run(
        self, user_id: Id, run_id: Id, updates: InterpretationRunUpdate
    ) -> InterpretationRunRecord:
        async with self._lock:
            bucket = self._bucket(user_id)
            record = get_visible(
                store=bucket.interpretation_runs,
                record_id=run_id,
                include_deleted=True,
                label="interpretation run",
            )
            record.update(deepcopy(updates))
            return deepcopy(record)

    async def store_evidence_items(
        self, user_id: Id, items: list[EvidenceItem]
    ) -> list[EvidenceItem]:
        async with self._lock:
            bucket = self._bucket(user_id)
            for item in items:
                bucket.evidence.setdefault(item["id"], deepcopy(item))
            return [deepcopy(item) for item in items]

    async def get_evidence_item(self, user_id: Id, evidence_id: Id) -> EvidenceItem:
        async with self._lock:
            bucket = self._bucket(user_id)
            if evidence_id not in bucket.evidence:
                raise EntityNotFoundError(f"Unknown evidence: {evidence_id}")
            return deepcopy(bucket.evidence[evidence_id])

    async def list_evidence_for_run(self, user_id: Id, run_id: Id) -> list[EvidenceItem]:
        async with self._lock:
            bucket = self._bucket(user_id)
            run = get_visible(
                store=bucket.interpretation_runs,
                record_id=run_id,
                include_deleted=True,
                label="interpretation run",
            )
            return [
                deepcopy(bucket.evidence[evidence_id])
                for evidence_id in run.get("evidenceIds", [])
                if evidence_id in bucket.evidence
            ]

    async def create_symbol(self, record: SymbolRecord) -> SymbolRecord:
        async with self._lock:
            bucket = self._bucket(record["userId"])
            ensure_unique(bucket.symbols, record["id"], "symbol")
            lowered = record["canonicalName"].lower()
            existing_id = bucket.symbol_name_index.get(lowered)
            if existing_id and existing_id != record["id"]:
                raise ConflictError(
                    f"Symbol already exists for canonical name: {record['canonicalName']}"
                )
            bucket.symbols[record["id"]] = deepcopy(record)
            bucket.symbol_name_index[lowered] = record["id"]
            return deepcopy(record)

    async def get_symbol(
        self, user_id: Id, symbol_id: Id, *, include_deleted: bool = False
    ) -> SymbolRecord:
        async with self._lock:
            return deepcopy(
                get_visible(
                    store=self._bucket(user_id).symbols,
                    record_id=symbol_id,
                    include_deleted=include_deleted,
                    label="symbol",
                )
            )

    async def find_symbol_by_name(self, user_id: Id, canonical_name: str) -> SymbolRecord | None:
        async with self._lock:
            bucket = self._bucket(user_id)
            symbol_id = bucket.symbol_name_index.get(canonical_name.lower())
            if not symbol_id:
                return None
            record = bucket.symbols[symbol_id]
            if record.get("status") == "deleted":
                return None
            return deepcopy(record)

    async def list_symbols(
        self, user_id: Id, *, include_deleted: bool = False, limit: int = 50
    ) -> list[SymbolRecord]:
        async with self._lock:
            bucket = self._bucket(user_id)
            items = [
                deepcopy(item)
                for item in bucket.symbols.values()
                if include_deleted or item.get("status") != "deleted"
            ]
            items.sort(
                key=lambda item: (
                    item.get("recurrenceCount", 0),
                    item.get("lastSeen", item.get("createdAt", "")),
                ),
                reverse=True,
            )
            return items[:limit]

    async def update_symbol(
        self, user_id: Id, symbol_id: Id, updates: SymbolUpdate
    ) -> SymbolRecord:
        async with self._lock:
            bucket = self._bucket(user_id)
            record = get_visible(
                store=bucket.symbols, record_id=symbol_id, include_deleted=True, label="symbol"
            )
            previous_name = record["canonicalName"].lower()
            record.update(deepcopy(updates))
            current_name = record["canonicalName"].lower()
            if current_name != previous_name:
                bucket.symbol_name_index.pop(previous_name, None)
                bucket.symbol_name_index[current_name] = symbol_id
            return deepcopy(record)

    async def append_symbol_history(self, entry: SymbolHistoryEntry) -> SymbolHistoryEntry:
        async with self._lock:
            bucket = self._bucket(entry["userId"])
            get_visible(
                store=bucket.symbols,
                record_id=entry["symbolId"],
                include_deleted=True,
                label="symbol",
            )
            append_symbol_history_locked(bucket, entry)
            return deepcopy(entry)

    async def list_symbol_history(
        self, user_id: Id, symbol_id: Id, *, limit: int = 50
    ) -> list[SymbolHistoryEntry]:
        async with self._lock:
            bucket = self._bucket(user_id)
            get_visible(
                store=bucket.symbols, record_id=symbol_id, include_deleted=True, label="symbol"
            )
            history = sorted(
                bucket.symbol_history.get(symbol_id, []),
                key=lambda item: item["createdAt"],
                reverse=True,
            )
            return [deepcopy(item) for item in history[:limit]]

    async def delete_symbol(
        self, user_id: Id, symbol_id: Id, *, mode: DeletionMode, reason: str | None = None
    ) -> None:
        del reason
        async with self._lock:
            bucket = self._bucket(user_id)
            record = get_visible(
                store=bucket.symbols, record_id=symbol_id, include_deleted=True, label="symbol"
            )
            tombstone_record(record, mode=mode, erase_fields=("canonicalName",))
            if mode == "erase":
                record["aliases"] = []
                record["linkedMaterialIds"] = []
                record["linkedLifeEventRefs"] = []
                record["personalAssociations"] = []
                record["valenceHistory"] = []
            bucket.symbol_name_index = {
                item["canonicalName"].lower(): item_id
                for item_id, item in bucket.symbols.items()
                if item.get("canonicalName") and item.get("status") != "deleted"
            }

    async def create_pattern(self, record: PatternRecord) -> PatternRecord:
        async with self._lock:
            bucket = self._bucket(record["userId"])
            ensure_unique(bucket.patterns, record["id"], "pattern")
            bucket.patterns[record["id"]] = deepcopy(record)
            return deepcopy(record)

    async def get_pattern(
        self, user_id: Id, pattern_id: Id, *, include_deleted: bool = False
    ) -> PatternRecord:
        async with self._lock:
            return deepcopy(
                get_visible(
                    store=self._bucket(user_id).patterns,
                    record_id=pattern_id,
                    include_deleted=include_deleted,
                    label="pattern",
                )
            )

    async def list_patterns(
        self,
        user_id: Id,
        *,
        pattern_type: PatternType | None = None,
        include_deleted: bool = False,
        limit: int = 50,
    ) -> list[PatternRecord]:
        async with self._lock:
            bucket = self._bucket(user_id)
            items = []
            for item in bucket.patterns.values():
                if not include_deleted and item.get("status") == "deleted":
                    continue
                if pattern_type and item["patternType"] != pattern_type:
                    continue
                items.append(deepcopy(item))
            items.sort(
                key=lambda item: item.get("updatedAt", item.get("createdAt", "")), reverse=True
            )
            return items[:limit]

    async def update_pattern(
        self, user_id: Id, pattern_id: Id, updates: PatternUpdate
    ) -> PatternRecord:
        async with self._lock:
            bucket = self._bucket(user_id)
            record = get_visible(
                store=bucket.patterns, record_id=pattern_id, include_deleted=True, label="pattern"
            )
            record.update(deepcopy(updates))
            return deepcopy(record)

    async def append_pattern_history(self, entry: PatternHistoryEntry) -> PatternHistoryEntry:
        async with self._lock:
            bucket = self._bucket(entry["userId"])
            get_visible(
                store=bucket.patterns,
                record_id=entry["patternId"],
                include_deleted=True,
                label="pattern",
            )
            append_pattern_history_locked(bucket, entry)
            return deepcopy(entry)

    async def list_pattern_history(
        self, user_id: Id, pattern_id: Id, *, limit: int = 50
    ) -> list[PatternHistoryEntry]:
        async with self._lock:
            bucket = self._bucket(user_id)
            get_visible(
                store=bucket.patterns, record_id=pattern_id, include_deleted=True, label="pattern"
            )
            history = sorted(
                bucket.pattern_history.get(pattern_id, []),
                key=lambda item: item["createdAt"],
                reverse=True,
            )
            return [deepcopy(item) for item in history[:limit]]

    async def delete_pattern(
        self, user_id: Id, pattern_id: Id, *, mode: DeletionMode, reason: str | None = None
    ) -> None:
        del reason
        async with self._lock:
            bucket = self._bucket(user_id)
            record = get_visible(
                store=bucket.patterns, record_id=pattern_id, include_deleted=True, label="pattern"
            )
            tombstone_record(record, mode=mode, erase_fields=("formulation",))
            if mode == "erase":
                record["linkedSymbols"] = []
                record["linkedSymbolIds"] = []
                record["linkedMaterialIds"] = []
                record["linkedLifeEventRefs"] = []
                record["evidenceIds"] = []
                record["counterevidenceIds"] = []

    async def create_typology_lens(self, record: TypologyLensRecord) -> TypologyLensRecord:
        async with self._lock:
            bucket = self._bucket(record["userId"])
            ensure_unique(bucket.typology_lenses, record["id"], "typology lens")
            bucket.typology_lenses[record["id"]] = deepcopy(record)
            return deepcopy(record)

    async def get_typology_lens(
        self, user_id: Id, lens_id: Id, *, include_deleted: bool = False
    ) -> TypologyLensRecord:
        async with self._lock:
            return deepcopy(
                get_visible(
                    store=self._bucket(user_id).typology_lenses,
                    record_id=lens_id,
                    include_deleted=include_deleted,
                    label="typology lens",
                )
            )

    async def list_typology_lenses(
        self, user_id: Id, *, include_deleted: bool = False, limit: int = 20
    ) -> list[TypologyLensRecord]:
        async with self._lock:
            bucket = self._bucket(user_id)
            items = [
                deepcopy(item)
                for item in bucket.typology_lenses.values()
                if include_deleted or item.get("status") != "deleted"
            ]
            items.sort(
                key=lambda item: item.get("updatedAt", item.get("createdAt", "")), reverse=True
            )
            return items[:limit]

    async def update_typology_lens(
        self, user_id: Id, lens_id: Id, updates: TypologyLensUpdate
    ) -> TypologyLensRecord:
        async with self._lock:
            bucket = self._bucket(user_id)
            record = get_visible(
                store=bucket.typology_lenses,
                record_id=lens_id,
                include_deleted=True,
                label="typology lens",
            )
            record.update(deepcopy(updates))
            return deepcopy(record)

    async def delete_typology_lens(
        self, user_id: Id, lens_id: Id, *, mode: DeletionMode, reason: str | None = None
    ) -> None:
        del reason
        async with self._lock:
            bucket = self._bucket(user_id)
            record = get_visible(
                store=bucket.typology_lenses,
                record_id=lens_id,
                include_deleted=True,
                label="typology lens",
            )
            tombstone_record(record, mode=mode, erase_fields=("claim", "userTestPrompt"))
            if mode == "erase":
                record["evidenceIds"] = []
                record["counterevidenceIds"] = []
                record["linkedMaterialIds"] = []

    async def create_practice_session(self, record: PracticeSessionRecord) -> PracticeSessionRecord:
        async with self._lock:
            bucket = self._bucket(record["userId"])
            ensure_unique(bucket.practice_sessions, record["id"], "practice session")
            bucket.practice_sessions[record["id"]] = deepcopy(record)
            return deepcopy(record)

    async def get_practice_session(
        self, user_id: Id, practice_session_id: Id, *, include_deleted: bool = False
    ) -> PracticeSessionRecord:
        async with self._lock:
            return deepcopy(
                get_visible(
                    store=self._bucket(user_id).practice_sessions,
                    record_id=practice_session_id,
                    include_deleted=include_deleted,
                    label="practice session",
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
        async with self._lock:
            bucket = self._bucket(user_id)
            status_set = set(statuses or [])
            items = []
            for item in bucket.practice_sessions.values():
                if item.get("status") == "deleted" and not include_deleted:
                    continue
                if material_id and item.get("materialId") != material_id:
                    continue
                if run_id and item.get("runId") != run_id:
                    continue
                if status_set and item.get("status") not in status_set:
                    continue
                if since and item.get("updatedAt", item.get("createdAt", "")) < since:
                    continue
                items.append(deepcopy(item))
            items.sort(
                key=lambda item: item.get("updatedAt", item.get("createdAt", "")), reverse=True
            )
            return items[:limit]

    async def update_practice_session(
        self, user_id: Id, practice_session_id: Id, updates: PracticeSessionUpdate
    ) -> PracticeSessionRecord:
        async with self._lock:
            bucket = self._bucket(user_id)
            record = get_visible(
                store=bucket.practice_sessions,
                record_id=practice_session_id,
                include_deleted=True,
                label="practice session",
            )
            record.update(deepcopy(updates))
            return deepcopy(record)

    async def delete_practice_session(
        self, user_id: Id, practice_session_id: Id, *, mode: DeletionMode
    ) -> None:
        async with self._lock:
            bucket = self._bucket(user_id)
            record = get_visible(
                store=bucket.practice_sessions,
                record_id=practice_session_id,
                include_deleted=True,
                label="practice session",
            )
            tombstone_record(record, mode=mode, erase_fields=("reason", "outcome"))
            if mode == "erase":
                record["instructions"] = []

    async def create_weekly_review(self, record: WeeklyReviewRecord) -> WeeklyReviewRecord:
        async with self._lock:
            bucket = self._bucket(record["userId"])
            ensure_unique(bucket.weekly_reviews, record["id"], "weekly review")
            bucket.weekly_reviews[record["id"]] = deepcopy(record)
            return deepcopy(record)

    async def get_weekly_review(
        self, user_id: Id, review_id: Id, *, include_deleted: bool = False
    ) -> WeeklyReviewRecord:
        async with self._lock:
            return deepcopy(
                get_visible(
                    store=self._bucket(user_id).weekly_reviews,
                    record_id=review_id,
                    include_deleted=include_deleted,
                    label="weekly review",
                )
            )

    async def list_weekly_reviews(
        self, user_id: Id, *, limit: int = 20
    ) -> list[WeeklyReviewRecord]:
        async with self._lock:
            bucket = self._bucket(user_id)
            items = [
                deepcopy(item)
                for item in bucket.weekly_reviews.values()
                if item.get("status") != "deleted"
            ]
            items.sort(key=lambda item: item.get("createdAt", ""), reverse=True)
            return items[:limit]

    async def delete_weekly_review(self, user_id: Id, review_id: Id, *, mode: DeletionMode) -> None:
        async with self._lock:
            bucket = self._bucket(user_id)
            review = get_visible(
                store=bucket.weekly_reviews,
                record_id=review_id,
                include_deleted=True,
                label="weekly review",
            )
            tombstone_record(review, mode=mode, erase_fields=())
            if mode == "erase":
                review["evidenceIds"] = []
                review["materialIds"] = []
                review["contextSnapshotIds"] = []
                review["recurringSymbolIds"] = []
                review["activePatternIds"] = []

    async def create_individuation_record(self, record: IndividuationRecord) -> IndividuationRecord:
        return await self._create_bucket_record(
            record["userId"], "individuation_records", record, "individuation record"
        )

    async def update_individuation_record(
        self, user_id: Id, record_id: Id, updates: IndividuationRecordUpdate
    ) -> IndividuationRecord:
        return await self._update_bucket_record(
            user_id, "individuation_records", record_id, updates, "individuation record"
        )

    async def get_individuation_record(
        self, user_id: Id, record_id: Id, *, include_deleted: bool = False
    ) -> IndividuationRecord:
        return await self._get_bucket_record(
            user_id,
            "individuation_records",
            record_id,
            include_deleted,
            "individuation record",
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
        type_set = set(record_types or [])
        status_set = set(statuses or [])
        return await self._list_bucket_records(
            user_id,
            "individuation_records",
            label="individuation record",
            predicate=lambda item: (
                (not type_set or item.get("recordType") in type_set)
                and (not status_set or item.get("status") in status_set)
                and (
                    window_start is None or item.get("windowEnd", window_end or "") >= window_start
                )
                and (
                    window_end is None or item.get("windowStart", window_start or "") <= window_end
                )
            ),
            limit=limit,
        )

    async def create_living_myth_record(self, record: LivingMythRecord) -> LivingMythRecord:
        return await self._create_bucket_record(
            record["userId"], "living_myth_records", record, "living myth record"
        )

    async def update_living_myth_record(
        self, user_id: Id, record_id: Id, updates: LivingMythRecordUpdate
    ) -> LivingMythRecord:
        return await self._update_bucket_record(
            user_id, "living_myth_records", record_id, updates, "living myth record"
        )

    async def get_living_myth_record(
        self, user_id: Id, record_id: Id, *, include_deleted: bool = False
    ) -> LivingMythRecord:
        return await self._get_bucket_record(
            user_id, "living_myth_records", record_id, include_deleted, "living myth record"
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
        type_set = set(record_types or [])
        status_set = set(statuses or [])
        return await self._list_bucket_records(
            user_id,
            "living_myth_records",
            label="living myth record",
            predicate=lambda item: (
                (not type_set or item.get("recordType") in type_set)
                and (not status_set or item.get("status") in status_set)
                and (
                    window_start is None or item.get("windowEnd", window_end or "") >= window_start
                )
                and (
                    window_end is None or item.get("windowStart", window_start or "") <= window_end
                )
            ),
            limit=limit,
        )

    async def create_living_myth_review(
        self, record: LivingMythReviewRecord
    ) -> LivingMythReviewRecord:
        return await self._create_bucket_record(
            record["userId"], "living_myth_reviews", record, "living myth review"
        )

    async def update_living_myth_review(
        self, user_id: Id, review_id: Id, updates: LivingMythReviewUpdate
    ) -> LivingMythReviewRecord:
        return await self._update_bucket_record(
            user_id, "living_myth_reviews", review_id, updates, "living myth review"
        )

    async def get_living_myth_review(
        self, user_id: Id, review_id: Id, *, include_deleted: bool = False
    ) -> LivingMythReviewRecord:
        return await self._get_bucket_record(
            user_id, "living_myth_reviews", review_id, include_deleted, "living myth review"
        )

    async def list_living_myth_reviews(
        self,
        user_id: Id,
        *,
        review_type: str | None = None,
        limit: int = 20,
    ) -> list[LivingMythReviewRecord]:
        return await self._list_bucket_records(
            user_id,
            "living_myth_reviews",
            label="living myth review",
            predicate=lambda item: not review_type or item.get("reviewType") == review_type,
            limit=limit,
        )

    async def create_analysis_packet(self, record: AnalysisPacketRecord) -> AnalysisPacketRecord:
        return await self._create_bucket_record(
            record["userId"], "analysis_packets", record, "analysis packet"
        )

    async def get_analysis_packet(
        self, user_id: Id, packet_id: Id, *, include_deleted: bool = False
    ) -> AnalysisPacketRecord:
        return await self._get_bucket_record(
            user_id, "analysis_packets", packet_id, include_deleted, "analysis packet"
        )

    async def list_analysis_packets(
        self, user_id: Id, *, limit: int = 20
    ) -> list[AnalysisPacketRecord]:
        return await self._list_bucket_records(
            user_id, "analysis_packets", label="analysis packet", limit=limit
        )

    async def create_integration_record(self, record: IntegrationRecord) -> IntegrationRecord:
        async with self._lock:
            bucket = self._bucket(record["userId"])
            ensure_unique(bucket.integrations, record["id"], "integration record")
            bucket.integrations[record["id"]] = deepcopy(record)
            return deepcopy(record)

    async def get_integration_record(self, user_id: Id, integration_id: Id) -> IntegrationRecord:
        async with self._lock:
            bucket = self._bucket(user_id)
            if integration_id not in bucket.integrations:
                raise EntityNotFoundError(f"Unknown integration record: {integration_id}")
            return deepcopy(bucket.integrations[integration_id])

    async def list_integration_records(
        self,
        user_id: Id,
        *,
        run_id: Id | None = None,
        material_id: Id | None = None,
        limit: int = 50,
    ) -> list[IntegrationRecord]:
        async with self._lock:
            bucket = self._bucket(user_id)
            items = []
            for item in bucket.integrations.values():
                if run_id and item.get("runId") != run_id:
                    continue
                if material_id and item.get("materialId") != material_id:
                    continue
                items.append(deepcopy(item))
            items.sort(key=lambda item: item.get("createdAt", ""), reverse=True)
            return items[:limit]

    async def update_proposal_decisions(
        self, user_id: Id, run_id: Id, decisions: list[ProposalDecisionRecord]
    ) -> InterpretationRunRecord:
        async with self._lock:
            bucket = self._bucket(user_id)
            run = get_visible(
                store=bucket.interpretation_runs,
                record_id=run_id,
                include_deleted=True,
                label="interpretation run",
            )
            decision_map = {item["proposalId"]: item for item in decisions}
            updated: list[ProposalDecisionRecord] = []
            for existing in run.get("proposalDecisions", []):
                if existing["proposalId"] in decision_map:
                    merged = deepcopy(existing)
                    merged.update(deepcopy(decision_map[existing["proposalId"]]))
                    updated.append(merged)
                else:
                    updated.append(existing)
            run["proposalDecisions"] = updated
            return deepcopy(run)

    async def create_conscious_attitude_snapshot(
        self, record: ConsciousAttitudeSnapshotRecord
    ) -> ConsciousAttitudeSnapshotRecord:
        return await self._create_bucket_record(
            record["userId"], "conscious_attitudes", record, "conscious attitude"
        )

    async def get_conscious_attitude_snapshot(
        self, user_id: Id, snapshot_id: Id, *, include_deleted: bool = False
    ) -> ConsciousAttitudeSnapshotRecord:
        return await self._get_bucket_record(
            user_id, "conscious_attitudes", snapshot_id, include_deleted, "conscious attitude"
        )

    async def list_conscious_attitude_snapshots(
        self,
        user_id: Id,
        *,
        filters: ConsciousAttitudeSnapshotFilters | None = None,
    ) -> list[ConsciousAttitudeSnapshotRecord]:
        criteria = filters or {}
        statuses = set(criteria.get("statuses", []))
        window_start = criteria.get("windowStart")
        window_end = criteria.get("windowEnd")
        limit = criteria.get("limit", 20)
        return await self._list_bucket_records(
            user_id,
            "conscious_attitudes",
            label="conscious attitude",
            predicate=lambda item: (
                (not statuses or item.get("status") in statuses)
                and (
                    not window_start
                    or not item.get("windowEnd")
                    or item["windowEnd"] >= window_start
                )
                and (
                    not window_end
                    or not item.get("windowStart")
                    or item["windowStart"] <= window_end
                )
            ),
            limit=limit,
        )

    async def update_conscious_attitude_snapshot(
        self, user_id: Id, snapshot_id: Id, updates: ConsciousAttitudeSnapshotUpdate
    ) -> ConsciousAttitudeSnapshotRecord:
        return await self._update_bucket_record(
            user_id, "conscious_attitudes", snapshot_id, updates, "conscious attitude"
        )

    async def delete_conscious_attitude_snapshot(
        self, user_id: Id, snapshot_id: Id, *, mode: DeletionMode, reason: str | None = None
    ) -> None:
        del reason
        await self._delete_bucket_record(
            user_id,
            "conscious_attitudes",
            snapshot_id,
            mode,
            "conscious attitude",
            erase_fields=("stanceSummary",),
        )

    async def create_amplification_prompt(
        self, record: AmplificationPromptRecord
    ) -> AmplificationPromptRecord:
        return await self._create_bucket_record(
            record["userId"], "amplification_prompts", record, "amplification prompt"
        )

    async def get_amplification_prompt(
        self, user_id: Id, prompt_id: Id, *, include_deleted: bool = False
    ) -> AmplificationPromptRecord:
        return await self._get_bucket_record(
            user_id, "amplification_prompts", prompt_id, include_deleted, "amplification prompt"
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
        status_set = set(statuses or [])
        return await self._list_bucket_records(
            user_id,
            "amplification_prompts",
            label="amplification prompt",
            predicate=lambda item: (
                (not material_id or item.get("materialId") == material_id)
                and (not run_id or item.get("runId") == run_id)
                and (not symbol_id or item.get("symbolId") == symbol_id)
                and (not status_set or item.get("status") in status_set)
            ),
            limit=limit,
        )

    async def update_amplification_prompt(
        self, user_id: Id, prompt_id: Id, updates: AmplificationPromptUpdate
    ) -> AmplificationPromptRecord:
        return await self._update_bucket_record(
            user_id, "amplification_prompts", prompt_id, updates, "amplification prompt"
        )

    async def create_personal_amplification(
        self, record: PersonalAmplificationRecord
    ) -> PersonalAmplificationRecord:
        return await self._create_bucket_record(
            record["userId"], "personal_amplifications", record, "personal amplification"
        )

    async def get_personal_amplification(
        self, user_id: Id, amplification_id: Id, *, include_deleted: bool = False
    ) -> PersonalAmplificationRecord:
        return await self._get_bucket_record(
            user_id,
            "personal_amplifications",
            amplification_id,
            include_deleted,
            "personal amplification",
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
        return await self._list_bucket_records(
            user_id,
            "personal_amplifications",
            label="personal amplification",
            predicate=lambda item: (
                (not material_id or item.get("materialId") == material_id)
                and (not run_id or item.get("runId") == run_id)
                and (not symbol_id or item.get("symbolId") == symbol_id)
            ),
            limit=limit,
        )

    async def update_personal_amplification(
        self, user_id: Id, amplification_id: Id, updates: PersonalAmplificationUpdate
    ) -> PersonalAmplificationRecord:
        return await self._update_bucket_record(
            user_id, "personal_amplifications", amplification_id, updates, "personal amplification"
        )

    async def delete_personal_amplification(
        self, user_id: Id, amplification_id: Id, *, mode: DeletionMode, reason: str | None = None
    ) -> None:
        del reason
        await self._delete_bucket_record(
            user_id,
            "personal_amplifications",
            amplification_id,
            mode,
            "personal amplification",
            erase_fields=("associationText",),
        )

    async def create_body_state(self, record: BodyStateRecord) -> BodyStateRecord:
        return await self._create_bucket_record(
            record["userId"], "body_states", record, "body state"
        )

    async def get_body_state(
        self, user_id: Id, body_state_id: Id, *, include_deleted: bool = False
    ) -> BodyStateRecord:
        return await self._get_bucket_record(
            user_id, "body_states", body_state_id, include_deleted, "body state"
        )

    async def list_body_states(
        self,
        user_id: Id,
        *,
        material_id: Id | None = None,
        run_id: Id | None = None,
        limit: int = 50,
    ) -> list[BodyStateRecord]:
        return await self._list_bucket_records(
            user_id,
            "body_states",
            label="body state",
            predicate=lambda item: (
                (
                    not material_id
                    or item.get("materialId") == material_id
                    or material_id in item.get("linkedMaterialIds", [])
                )
                and (not run_id or item.get("runId") == run_id)
            ),
            limit=limit,
        )

    async def update_body_state(
        self, user_id: Id, body_state_id: Id, updates: BodyStateUpdate
    ) -> BodyStateRecord:
        return await self._update_bucket_record(
            user_id, "body_states", body_state_id, updates, "body state"
        )

    async def delete_body_state(
        self, user_id: Id, body_state_id: Id, *, mode: DeletionMode, reason: str | None = None
    ) -> None:
        del reason
        await self._delete_bucket_record(
            user_id, "body_states", body_state_id, mode, "body state", erase_fields=("sensation",)
        )

    async def create_goal(self, record: GoalRecord) -> GoalRecord:
        return await self._create_bucket_record(record["userId"], "goals", record, "goal")

    async def get_goal(
        self, user_id: Id, goal_id: Id, *, include_deleted: bool = False
    ) -> GoalRecord:
        return await self._get_bucket_record(user_id, "goals", goal_id, include_deleted, "goal")

    async def list_goals(
        self, user_id: Id, *, include_deleted: bool = False, limit: int = 50
    ) -> list[GoalRecord]:
        return await self._list_bucket_records(
            user_id, "goals", include_deleted=include_deleted, label="goal", limit=limit
        )

    async def update_goal(self, user_id: Id, goal_id: Id, updates: GoalUpdate) -> GoalRecord:
        return await self._update_bucket_record(user_id, "goals", goal_id, updates, "goal")

    async def delete_goal(
        self, user_id: Id, goal_id: Id, *, mode: DeletionMode, reason: str | None = None
    ) -> None:
        del reason
        await self._delete_bucket_record(
            user_id, "goals", goal_id, mode, "goal", erase_fields=("description",)
        )

    async def create_goal_tension(self, record: GoalTensionRecord) -> GoalTensionRecord:
        return await self._create_bucket_record(
            record["userId"], "goal_tensions", record, "goal tension"
        )

    async def get_goal_tension(
        self, user_id: Id, tension_id: Id, *, include_deleted: bool = False
    ) -> GoalTensionRecord:
        return await self._get_bucket_record(
            user_id, "goal_tensions", tension_id, include_deleted, "goal tension"
        )

    async def list_goal_tensions(
        self, user_id: Id, *, include_deleted: bool = False, limit: int = 50
    ) -> list[GoalTensionRecord]:
        return await self._list_bucket_records(
            user_id,
            "goal_tensions",
            include_deleted=include_deleted,
            label="goal tension",
            limit=limit,
        )

    async def update_goal_tension(
        self, user_id: Id, tension_id: Id, updates: GoalTensionUpdate
    ) -> GoalTensionRecord:
        return await self._update_bucket_record(
            user_id, "goal_tensions", tension_id, updates, "goal tension"
        )

    async def delete_goal_tension(
        self, user_id: Id, tension_id: Id, *, mode: DeletionMode, reason: str | None = None
    ) -> None:
        del reason
        await self._delete_bucket_record(
            user_id,
            "goal_tensions",
            tension_id,
            mode,
            "goal tension",
            erase_fields=("tensionSummary",),
        )

    async def create_dream_series(self, record: DreamSeriesRecord) -> DreamSeriesRecord:
        return await self._create_bucket_record(
            record["userId"], "dream_series", record, "dream series"
        )

    async def get_dream_series(
        self, user_id: Id, series_id: Id, *, include_deleted: bool = False
    ) -> DreamSeriesRecord:
        return await self._get_bucket_record(
            user_id, "dream_series", series_id, include_deleted, "dream series"
        )

    async def list_dream_series(
        self, user_id: Id, *, include_deleted: bool = False, limit: int = 50
    ) -> list[DreamSeriesRecord]:
        return await self._list_bucket_records(
            user_id,
            "dream_series",
            include_deleted=include_deleted,
            label="dream series",
            limit=limit,
        )

    async def update_dream_series(
        self, user_id: Id, series_id: Id, updates: DreamSeriesUpdate
    ) -> DreamSeriesRecord:
        return await self._update_bucket_record(
            user_id, "dream_series", series_id, updates, "dream series"
        )

    async def delete_dream_series(
        self, user_id: Id, series_id: Id, *, mode: DeletionMode, reason: str | None = None
    ) -> None:
        del reason
        await self._delete_bucket_record(
            user_id,
            "dream_series",
            series_id,
            mode,
            "dream series",
            erase_fields=("progressionSummary",),
        )

    async def create_dream_series_membership(
        self, record: DreamSeriesMembershipRecord
    ) -> DreamSeriesMembershipRecord:
        return await self._create_bucket_record(
            record["userId"], "dream_series_memberships", record, "dream series membership"
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
        return await self._list_bucket_records(
            user_id,
            "dream_series_memberships",
            include_deleted=include_deleted,
            label="dream series membership",
            predicate=lambda item: (
                (not series_id or item.get("seriesId") == series_id)
                and (not material_id or item.get("materialId") == material_id)
            ),
            limit=limit,
        )

    async def update_dream_series_membership(
        self, user_id: Id, membership_id: Id, updates: DreamSeriesMembershipUpdate
    ) -> DreamSeriesMembershipRecord:
        return await self._update_bucket_record(
            user_id,
            "dream_series_memberships",
            membership_id,
            updates,
            "dream series membership",
        )

    async def create_cultural_frame(self, record: CulturalFrameRecord) -> CulturalFrameRecord:
        return await self._create_bucket_record(
            record["userId"], "cultural_frames", record, "cultural frame"
        )

    async def get_cultural_frame(
        self, user_id: Id, cultural_frame_id: Id, *, include_deleted: bool = False
    ) -> CulturalFrameRecord:
        return await self._get_bucket_record(
            user_id, "cultural_frames", cultural_frame_id, include_deleted, "cultural frame"
        )

    async def list_cultural_frames(
        self, user_id: Id, *, include_deleted: bool = False, limit: int = 50
    ) -> list[CulturalFrameRecord]:
        return await self._list_bucket_records(
            user_id,
            "cultural_frames",
            include_deleted=include_deleted,
            label="cultural frame",
            limit=limit,
        )

    async def update_cultural_frame(
        self, user_id: Id, cultural_frame_id: Id, updates: CulturalFrameUpdate
    ) -> CulturalFrameRecord:
        return await self._update_bucket_record(
            user_id, "cultural_frames", cultural_frame_id, updates, "cultural frame"
        )

    async def create_collective_amplification(
        self, record: CollectiveAmplificationRecord
    ) -> CollectiveAmplificationRecord:
        return await self._create_bucket_record(
            record["userId"], "collective_amplifications", record, "collective amplification"
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
        return await self._list_bucket_records(
            user_id,
            "collective_amplifications",
            label="collective amplification",
            predicate=lambda item: (
                (not material_id or item.get("materialId") == material_id)
                and (not run_id or item.get("runId") == run_id)
                and (not symbol_id or item.get("symbolId") == symbol_id)
            ),
            limit=limit,
        )

    async def update_collective_amplification(
        self, user_id: Id, amplification_id: Id, updates: CollectiveAmplificationUpdate
    ) -> CollectiveAmplificationRecord:
        return await self._update_bucket_record(
            user_id,
            "collective_amplifications",
            amplification_id,
            updates,
            "collective amplification",
        )

    async def create_consent_preference(
        self, record: ConsentPreferenceRecord
    ) -> ConsentPreferenceRecord:
        return await self._create_bucket_record(
            record["userId"], "consent_preferences", record, "consent preference"
        )

    async def list_consent_preferences(
        self, user_id: Id, *, limit: int = 50
    ) -> list[ConsentPreferenceRecord]:
        return await self._list_bucket_records(
            user_id, "consent_preferences", label="consent preference", limit=limit
        )

    async def update_consent_preference(
        self, user_id: Id, preference_id: Id, updates: ConsentPreferenceUpdate
    ) -> ConsentPreferenceRecord:
        return await self._update_bucket_record(
            user_id,
            "consent_preferences",
            preference_id,
            updates,
            "consent preference",
        )

    async def upsert_adaptation_profile(
        self, user_id: Id, record: UserAdaptationProfileRecord
    ) -> UserAdaptationProfileRecord:
        async with self._lock:
            bucket = self._bucket(user_id)
            bucket.adaptation_profiles[record["id"]] = deepcopy(record)
            return deepcopy(record)

    async def get_adaptation_profile(self, user_id: Id) -> UserAdaptationProfileRecord | None:
        async with self._lock:
            bucket = self._bucket(user_id)
            if not bucket.adaptation_profiles:
                return None
            profile = sorted(
                bucket.adaptation_profiles.values(),
                key=lambda item: item.get("updatedAt", item.get("createdAt", "")),
                reverse=True,
            )[0]
            if profile.get("status") == "deleted":
                return None
            return deepcopy(profile)

    async def update_adaptation_profile(
        self, user_id: Id, profile_id: Id, updates: UserAdaptationProfileUpdate
    ) -> UserAdaptationProfileRecord:
        return await self._update_bucket_record(
            user_id, "adaptation_profiles", profile_id, updates, "adaptation profile"
        )

    async def create_journey(self, record: JourneyRecord) -> JourneyRecord:
        return await self._create_bucket_record(record["userId"], "journeys", record, "journey")

    async def list_journeys(
        self, user_id: Id, *, include_deleted: bool = False, limit: int = 50
    ) -> list[JourneyRecord]:
        return await self._list_bucket_records(
            user_id, "journeys", include_deleted=include_deleted, label="journey", limit=limit
        )

    async def get_journey(
        self, user_id: Id, journey_id: Id, *, include_deleted: bool = False
    ) -> JourneyRecord:
        return await self._get_bucket_record(
            user_id, "journeys", journey_id, include_deleted, "journey"
        )

    async def update_journey(
        self, user_id: Id, journey_id: Id, updates: JourneyUpdate
    ) -> JourneyRecord:
        return await self._update_bucket_record(user_id, "journeys", journey_id, updates, "journey")

    async def create_proactive_brief(self, record: ProactiveBriefRecord) -> ProactiveBriefRecord:
        async with self._lock:
            bucket = self._bucket(record["userId"])
            trigger_key = str(record.get("triggerKey") or "").strip()
            if trigger_key:
                for existing in bucket.proactive_briefs.values():
                    if existing.get("status") == "deleted":
                        continue
                    if existing.get("triggerKey") != trigger_key:
                        continue
                    return deepcopy(existing)
            ensure_unique(bucket.proactive_briefs, record["id"], "proactive brief")
            bucket.proactive_briefs[record["id"]] = deepcopy(record)
            return deepcopy(record)

    async def get_proactive_brief(
        self, user_id: Id, brief_id: Id, *, include_deleted: bool = False
    ) -> ProactiveBriefRecord:
        return await self._get_bucket_record(
            user_id, "proactive_briefs", brief_id, include_deleted, "proactive brief"
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
        status_set = set(statuses or [])
        return await self._list_bucket_records(
            user_id,
            "proactive_briefs",
            include_deleted=include_deleted,
            label="proactive brief",
            predicate=lambda item: (
                (not status_set or item.get("status") in status_set)
                and (not brief_type or item.get("briefType") == brief_type)
                and (not since or item.get("updatedAt", item.get("createdAt", "")) >= since)
            ),
            limit=limit,
        )

    async def update_proactive_brief(
        self, user_id: Id, brief_id: Id, updates: ProactiveBriefUpdate
    ) -> ProactiveBriefRecord:
        return await self._update_bucket_record(
            user_id, "proactive_briefs", brief_id, updates, "proactive brief"
        )

    async def build_hermes_memory_context_from_records(
        self, user_id: Id, *, max_items: int | None = None
    ) -> HermesMemoryContext:
        async with self._lock:
            bucket = self._bucket(user_id)
            return build_memory_context_locked(bucket, max_items=max_items)

    async def build_memory_kernel_snapshot(
        self,
        user_id: Id,
        *,
        query: MemoryRetrievalQuery | None = None,
    ) -> MemoryKernelSnapshot:
        async with self._lock:
            bucket = self._bucket(user_id)
            return build_memory_kernel_snapshot_locked(bucket, user_id=user_id, query=query)

    async def query_graph(
        self,
        user_id: Id,
        *,
        query: GraphQuery | None = None,
    ) -> GraphQueryResult:
        async with self._lock:
            bucket = self._bucket(user_id)
            return query_graph_locked(bucket, user_id=user_id, query=query)

    async def build_life_context_snapshot_from_records(
        self,
        user_id: Id,
        *,
        window_start: str,
        window_end: str,
        exclude_material_id: Id | None = None,
    ) -> LifeContextSnapshot | None:
        async with self._lock:
            bucket = self._bucket(user_id)
            return build_life_context_snapshot_locked(
                bucket,
                user_id=user_id,
                window_start=window_start,
                window_end=window_end,
                exclude_material_id=exclude_material_id,
            )

    async def build_method_context_snapshot_from_records(
        self,
        user_id: Id,
        *,
        window_start: str,
        window_end: str,
        material_id: Id | None = None,
    ) -> MethodContextSnapshot | None:
        async with self._lock:
            bucket = self._bucket(user_id)
            return build_method_context_snapshot_locked(
                bucket,
                user_id=user_id,
                window_start=window_start,
                window_end=window_end,
                material_id=material_id,
            )

    async def build_circulation_summary_input(
        self,
        user_id: Id,
        *,
        window_start: str,
        window_end: str,
    ) -> CirculationSummaryInput:
        async with self._lock:
            bucket = self._bucket(user_id)
            return build_circulation_summary_input_locked(
                bucket, user_id=user_id, window_start=window_start, window_end=window_end
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
        async with self._lock:
            bucket = self._bucket(user_id)
            return build_threshold_review_input_locked(
                bucket,
                user_id=user_id,
                window_start=window_start,
                window_end=window_end,
                threshold_process_id=threshold_process_id,
                explicit_question=explicit_question,
            )

    async def build_living_myth_review_input(
        self,
        user_id: Id,
        *,
        window_start: str,
        window_end: str,
        explicit_question: str | None = None,
    ) -> LivingMythReviewInput:
        async with self._lock:
            bucket = self._bucket(user_id)
            return build_living_myth_review_input_locked(
                bucket,
                user_id=user_id,
                window_start=window_start,
                window_end=window_end,
                explicit_question=explicit_question,
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
        async with self._lock:
            bucket = self._bucket(user_id)
            return build_analysis_packet_input_locked(
                bucket,
                user_id=user_id,
                window_start=window_start,
                window_end=window_end,
                packet_focus=packet_focus,
                explicit_question=explicit_question,
            )

    async def get_dashboard_summary(self, user_id: Id) -> DashboardSummary:
        async with self._lock:
            bucket = self._bucket(user_id)
            return build_dashboard_summary_locked(bucket, user_id=user_id)

    async def get_hermes_memory_context(
        self, user_id: Id, *, max_items: int | None = None
    ) -> HermesMemoryContext:
        return await self.build_hermes_memory_context_from_records(user_id, max_items=max_items)

    async def get_symbolic_memory_snapshot(
        self, user_id: Id, *, max_items: int | None = None
    ) -> SymbolicMemorySnapshot:
        async with self._lock:
            bucket = self._bucket(user_id)
            return build_symbolic_memory_snapshot_locked(bucket, max_items=max_items)

    async def apply_approved_proposals(
        self, *, user_id: Id, memory_write_plan: MemoryWritePlan, approved_proposal_ids: list[Id]
    ) -> dict[str, list[Id]]:
        async with self._lock:
            return apply_approved_proposals_locked(
                bucket=self._bucket(user_id),
                user_id=user_id,
                memory_write_plan=memory_write_plan,
                approved_proposal_ids=approved_proposal_ids,
            )

    async def record_integration(
        self, input_data: RecordIntegrationInput
    ) -> RecordIntegrationResult:
        async with self._lock:
            bucket = self._bucket(input_data["userId"])
            applied = apply_approved_proposals_locked(
                bucket=bucket,
                user_id=input_data["userId"],
                memory_write_plan=input_data["memoryWritePlan"],
                approved_proposal_ids=input_data.get("approvedProposalIds", []),
            )
            suppressed_ids: list[Id] = []
            for hypothesis_id, feedback in input_data.get("feedbackByHypothesisId", {}).items():
                bucket.feedback.insert(
                    0,
                    {
                        "hypothesisId": hypothesis_id,
                        "runId": input_data["runId"],
                        "feedback": feedback["feedback"],
                        "note": feedback.get("note"),
                        "timestamp": now_iso(),
                        "normalizedClaimKey": feedback.get("normalizedClaimKey"),
                        "claimDomain": feedback.get("claimDomain"),
                    },
                )
                if feedback["feedback"] in {"rejected", "partially_refined"}:
                    suppressed = suppress_hypothesis_locked(
                        bucket,
                        {
                            "userId": input_data["userId"],
                            "hypothesisId": hypothesis_id,
                            "normalizedClaimKey": feedback.get("normalizedClaimKey", hypothesis_id),
                            "reason": "user_refined"
                            if feedback["feedback"] == "partially_refined"
                            else "user_rejected",
                            "note": feedback.get("note") or feedback.get("refinedClaim"),
                        },
                    )
                    suppressed_ids.append(suppressed["id"])
            run = bucket.interpretation_runs.get(input_data["runId"])
            if run:
                run["proposalDecisions"] = merge_decisions(
                    run.get("proposalDecisions", []),
                    [
                        {
                            "proposalId": proposal_id,
                            "action": proposal_action(input_data["memoryWritePlan"], proposal_id),
                            "entityType": proposal_entity_type(
                                input_data["memoryWritePlan"], proposal_id
                            ),
                            "status": "approved",
                            "decidedAt": now_iso(),
                        }
                        for proposal_id in input_data.get("approvedProposalIds", [])
                    ]
                    + [
                        {
                            "proposalId": proposal_id,
                            "action": proposal_action(input_data["memoryWritePlan"], proposal_id),
                            "entityType": proposal_entity_type(
                                input_data["memoryWritePlan"], proposal_id
                            ),
                            "status": "rejected",
                            "decidedAt": now_iso(),
                        }
                        for proposal_id in input_data.get("rejectedProposalIds", [])
                    ],
                )
            integration_id: Id | None = None
            if (
                applied["appliedProposalIds"]
                or input_data.get("rejectedProposalIds")
                or suppressed_ids
                or input_data.get("integrationNote")
            ):
                integration_id = create_id("integration")
                bucket.integrations[integration_id] = {
                    "id": integration_id,
                    "userId": input_data["userId"],
                    "runId": input_data["runId"],
                    "materialId": run["materialId"] if run else None,
                    "action": "approved_proposals"
                    if applied["appliedProposalIds"]
                    else "rejected_hypotheses",
                    "approvedProposalIds": list(applied["appliedProposalIds"]),
                    "rejectedProposalIds": list(input_data.get("rejectedProposalIds", [])),
                    "suppressedHypothesisIds": suppressed_ids,
                    "feedbackByHypothesisId": deepcopy(input_data.get("feedbackByHypothesisId", {}))
                    or None,
                    "affectedEntityIds": list(applied.get("affectedEntityIds", [])),
                    "note": input_data.get("integrationNote"),
                    "createdAt": now_iso(),
                }
            result: RecordIntegrationResult = {
                "appliedProposalIds": list(applied["appliedProposalIds"]),
                "suppressedHypothesisIds": suppressed_ids,
            }
            if integration_id is not None:
                result["integrationNoteId"] = integration_id
            return result

    async def suppress_hypothesis(
        self, request: SuppressHypothesisRequest
    ) -> SuppressedHypothesisSummary:
        async with self._lock:
            return deepcopy(suppress_hypothesis_locked(self._bucket(request["userId"]), request))

    async def revise_entity(self, request: ReviseGraphEntityRequest) -> None:
        async with self._lock:
            bucket = self._bucket(request["userId"])
            entity_type = request["entityType"]
            note = request.get("revisionNote")
            replacement = request.get("replacementSummary")
            if entity_type in {
                "MaterialEntry",
                "DreamEntry",
                "ReflectionEntry",
                "ChargedEventNote",
            }:
                material = get_visible(
                    store=bucket.materials,
                    record_id=request["entityId"],
                    include_deleted=True,
                    label="material",
                )
                revision_number = len(bucket.material_revisions.get(request["entityId"], [])) + 1
                revision: MaterialRevision = {
                    "id": create_id("material_revision"),
                    "userId": request["userId"],
                    "materialId": request["entityId"],
                    "revisionNumber": revision_number,
                    "previousText": material.get("text"),
                    "newText": material.get("text"),
                    "previousSummary": material.get("summary"),
                    "newSummary": replacement or material.get("summary"),
                    "reason": "user_requested",
                    "note": note,
                    "createdAt": now_iso(),
                }
                bucket.material_revisions.setdefault(request["entityId"], []).append(revision)
                material["summary"] = replacement or material.get("summary")
                material["updatedAt"] = now_iso()
                material["status"] = "revised"
                material["currentRevisionId"] = revision["id"]
            elif entity_type == "PersonalSymbol":
                symbol = get_visible(
                    store=bucket.symbols,
                    record_id=request["entityId"],
                    include_deleted=True,
                    label="symbol",
                )
                previous = deepcopy(symbol)
                if replacement:
                    symbol["canonicalName"] = replacement
                symbol["updatedAt"] = now_iso()
                symbol["status"] = "revised"
                append_symbol_history_locked(
                    bucket,
                    {
                        "id": create_id("symbol_history"),
                        "userId": request["userId"],
                        "symbolId": request["entityId"],
                        "eventType": "revised",
                        "evidenceIds": [],
                        "previousValue": previous,
                        "newValue": deepcopy(symbol),
                        "note": note,
                        "createdAt": now_iso(),
                    },
                )
            elif entity_type in {"Theme", "ComplexCandidate"}:
                pattern = get_visible(
                    store=bucket.patterns,
                    record_id=request["entityId"],
                    include_deleted=True,
                    label="pattern",
                )
                previous = deepcopy(pattern)
                if replacement:
                    pattern["formulation"] = replacement
                pattern["updatedAt"] = now_iso()
                append_pattern_history_locked(
                    bucket,
                    {
                        "id": create_id("pattern_history"),
                        "userId": request["userId"],
                        "patternId": request["entityId"],
                        "eventType": "formulation_revised",
                        "evidenceIds": [],
                        "previousValue": previous,
                        "newValue": deepcopy(pattern),
                        "note": note,
                        "createdAt": now_iso(),
                    },
                )
            elif entity_type == "TypologyLens":
                lens = get_visible(
                    store=bucket.typology_lenses,
                    record_id=request["entityId"],
                    include_deleted=True,
                    label="typology lens",
                )
                if replacement:
                    lens["claim"] = replacement
                lens["updatedAt"] = now_iso()
            elif entity_type in {"PracticePlan", "PracticeSession"}:
                practice = get_visible(
                    store=bucket.practice_sessions,
                    record_id=request["entityId"],
                    include_deleted=True,
                    label="practice session",
                )
                if replacement:
                    practice["reason"] = replacement
                practice["updatedAt"] = now_iso()
            elif entity_type == "WeeklyReview":
                review = get_visible(
                    store=bucket.weekly_reviews,
                    record_id=request["entityId"],
                    include_deleted=True,
                    label="weekly review",
                )
                review["status"] = "revised"
            elif entity_type == "ContextSnapshot":
                snapshot = get_visible(
                    store=bucket.context_snapshots,
                    record_id=request["entityId"],
                    include_deleted=True,
                    label="context snapshot",
                )
                if replacement:
                    snapshot["summary"] = replacement
            else:
                raise EntityNotFoundError(f"Unsupported entity type for revision: {entity_type}")

    async def delete_entity(self, request: DeleteGraphEntityRequest) -> None:
        async with self._lock:
            bucket = self._bucket(request["userId"])
            entity_type = request["entityType"]
            mode: DeletionMode = "erase" if request["reason"] == "privacy" else "tombstone"
            if entity_type in {
                "MaterialEntry",
                "DreamEntry",
                "ReflectionEntry",
                "ChargedEventNote",
            }:
                material = get_visible(
                    store=bucket.materials,
                    record_id=request["entityId"],
                    include_deleted=True,
                    label="material",
                )
                tombstone_record(material, mode=mode, erase_fields=("text", "summary"))
            elif entity_type == "PersonalSymbol":
                symbol = get_visible(
                    store=bucket.symbols,
                    record_id=request["entityId"],
                    include_deleted=True,
                    label="symbol",
                )
                previous = deepcopy(symbol)
                tombstone_record(symbol, mode=mode, erase_fields=("canonicalName",))
                append_symbol_history_locked(
                    bucket,
                    {
                        "id": create_id("symbol_history"),
                        "userId": request["userId"],
                        "symbolId": request["entityId"],
                        "eventType": "deleted",
                        "evidenceIds": [],
                        "previousValue": previous,
                        "newValue": deepcopy(symbol),
                        "note": request["reason"],
                        "createdAt": now_iso(),
                    },
                )
            elif entity_type in {"Theme", "ComplexCandidate"}:
                pattern = get_visible(
                    store=bucket.patterns,
                    record_id=request["entityId"],
                    include_deleted=True,
                    label="pattern",
                )
                previous = deepcopy(pattern)
                tombstone_record(pattern, mode=mode, erase_fields=("formulation",))
                append_pattern_history_locked(
                    bucket,
                    {
                        "id": create_id("pattern_history"),
                        "userId": request["userId"],
                        "patternId": request["entityId"],
                        "eventType": "deleted",
                        "evidenceIds": [],
                        "previousValue": previous,
                        "newValue": deepcopy(pattern),
                        "note": request["reason"],
                        "createdAt": now_iso(),
                    },
                )
            elif entity_type == "TypologyLens":
                lens = get_visible(
                    store=bucket.typology_lenses,
                    record_id=request["entityId"],
                    include_deleted=True,
                    label="typology lens",
                )
                tombstone_record(lens, mode=mode, erase_fields=("claim", "userTestPrompt"))
            elif entity_type in {"PracticePlan", "PracticeSession"}:
                practice = get_visible(
                    store=bucket.practice_sessions,
                    record_id=request["entityId"],
                    include_deleted=True,
                    label="practice session",
                )
                tombstone_record(practice, mode=mode, erase_fields=("reason", "outcome"))
            elif entity_type == "WeeklyReview":
                review = get_visible(
                    store=bucket.weekly_reviews,
                    record_id=request["entityId"],
                    include_deleted=True,
                    label="weekly review",
                )
                tombstone_record(review, mode=mode, erase_fields=())
                if mode == "erase":
                    review["evidenceIds"] = []
                    review["materialIds"] = []
                    review["contextSnapshotIds"] = []
                    review["recurringSymbolIds"] = []
                    review["activePatternIds"] = []
            elif entity_type == "ContextSnapshot":
                snapshot = get_visible(
                    store=bucket.context_snapshots,
                    record_id=request["entityId"],
                    include_deleted=True,
                    label="context snapshot",
                )
                tombstone_record(snapshot, mode=mode, erase_fields=("summary",))
                if mode == "erase":
                    snapshot.pop("sessionContext", None)
                    snapshot.pop("lifeContextSnapshot", None)
            elif request["entityId"] in bucket.evidence:
                if mode == "erase":
                    bucket.evidence.pop(request["entityId"], None)
                else:
                    bucket.evidence[request["entityId"]]["quoteOrSummary"] = ""
            else:
                raise EntityNotFoundError(f"Unsupported entity type for deletion: {entity_type}")

    def _bucket(self, user_id: Id) -> UserCirculatioBucket:
        if user_id not in self._users:
            self._users[user_id] = UserCirculatioBucket()
        return self._users[user_id]

    async def _create_bucket_record(self, user_id: Id, store_name: str, record: object, label: str):
        async with self._lock:
            bucket = self._bucket(user_id)
            store = getattr(bucket, store_name)
            ensure_unique(store, record["id"], label)
            store[record["id"]] = deepcopy(record)
            return deepcopy(record)

    async def _get_bucket_record(
        self, user_id: Id, store_name: str, record_id: Id, include_deleted: bool, label: str
    ):
        async with self._lock:
            bucket = self._bucket(user_id)
            store = getattr(bucket, store_name)
            return deepcopy(
                get_visible(
                    store=store, record_id=record_id, include_deleted=include_deleted, label=label
                )
            )

    async def _update_bucket_record(
        self, user_id: Id, store_name: str, record_id: Id, updates: object, label: str
    ):
        async with self._lock:
            bucket = self._bucket(user_id)
            store = getattr(bucket, store_name)
            record = get_visible(
                store=store, record_id=record_id, include_deleted=True, label=label
            )
            record.update(deepcopy(updates))
            return deepcopy(record)

    async def _list_bucket_records(
        self,
        user_id: Id,
        store_name: str,
        *,
        include_deleted: bool = False,
        label: str,
        predicate=None,
        limit: int = 50,
    ):
        async with self._lock:
            bucket = self._bucket(user_id)
            store = getattr(bucket, store_name)
            items = []
            for item in store.values():
                if not include_deleted and item.get("status") == "deleted":
                    continue
                if predicate is not None and not predicate(item):
                    continue
                items.append(deepcopy(item))
            items.sort(
                key=lambda item: item.get("updatedAt", item.get("createdAt", "")), reverse=True
            )
            return items[:limit]

    async def _delete_bucket_record(
        self,
        user_id: Id,
        store_name: str,
        record_id: Id,
        mode: DeletionMode,
        label: str,
        *,
        erase_fields: tuple[str, ...],
    ) -> None:
        async with self._lock:
            bucket = self._bucket(user_id)
            store = getattr(bucket, store_name)
            record = get_visible(
                store=store, record_id=record_id, include_deleted=True, label=label
            )
            tombstone_record(record, mode=mode, erase_fields=erase_fields)
