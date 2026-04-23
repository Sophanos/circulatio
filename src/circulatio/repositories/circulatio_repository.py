from __future__ import annotations

from abc import abstractmethod

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
from ..domain.feedback import InteractionFeedbackRecord
from ..domain.goals import GoalRecord, GoalTensionRecord, GoalTensionUpdate, GoalUpdate
from ..domain.graph import GraphQuery, GraphQueryResult
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
from ..domain.journey_experiments import (
    JourneyExperimentRecord,
    JourneyExperimentStatus,
    JourneyExperimentUpdate,
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
    ISODateString,
    LifeContextSnapshot,
    LivingMythReviewInput,
    MethodContextSnapshot,
    ThreadDigest,
    ThresholdReviewInput,
)
from ..domain.typology import TypologyLensRecord, TypologyLensUpdate
from .graph_memory_repository import GraphMemoryRepository


class CirculatioRepository(GraphMemoryRepository):
    @abstractmethod
    async def create_material(self, record: MaterialRecord) -> MaterialRecord:
        raise NotImplementedError

    @abstractmethod
    async def get_material(
        self, user_id: Id, material_id: Id, *, include_deleted: bool = False
    ) -> MaterialRecord:
        raise NotImplementedError

    @abstractmethod
    async def list_materials(
        self, user_id: Id, filters: MaterialListFilters | None = None
    ) -> list[MaterialRecord]:
        raise NotImplementedError

    @abstractmethod
    async def update_material(
        self, user_id: Id, material_id: Id, updates: MaterialUpdate
    ) -> MaterialRecord:
        raise NotImplementedError

    @abstractmethod
    async def create_material_revision(self, revision: MaterialRevision) -> MaterialRevision:
        raise NotImplementedError

    @abstractmethod
    async def list_material_revisions(self, user_id: Id, material_id: Id) -> list[MaterialRevision]:
        raise NotImplementedError

    @abstractmethod
    async def delete_material(
        self, user_id: Id, material_id: Id, *, mode: DeletionMode, reason: str | None = None
    ) -> None:
        raise NotImplementedError

    @abstractmethod
    async def create_context_snapshot(self, snapshot: ContextSnapshot) -> ContextSnapshot:
        raise NotImplementedError

    @abstractmethod
    async def get_context_snapshot(
        self, user_id: Id, snapshot_id: Id, *, include_deleted: bool = False
    ) -> ContextSnapshot:
        raise NotImplementedError

    @abstractmethod
    async def list_context_snapshots(
        self,
        user_id: Id,
        *,
        material_id: Id | None = None,
        window_start: str | None = None,
        window_end: str | None = None,
    ) -> list[ContextSnapshot]:
        raise NotImplementedError

    @abstractmethod
    async def delete_context_snapshot(
        self, user_id: Id, snapshot_id: Id, *, mode: DeletionMode
    ) -> None:
        raise NotImplementedError

    @abstractmethod
    async def store_interpretation_run(
        self, run: InterpretationRunRecord
    ) -> InterpretationRunRecord:
        raise NotImplementedError

    @abstractmethod
    async def get_interpretation_run(self, user_id: Id, run_id: Id) -> InterpretationRunRecord:
        raise NotImplementedError

    @abstractmethod
    async def list_interpretation_runs(
        self, user_id: Id, *, material_id: Id | None = None, limit: int = 20
    ) -> list[InterpretationRunRecord]:
        raise NotImplementedError

    @abstractmethod
    async def update_interpretation_run(
        self, user_id: Id, run_id: Id, updates: InterpretationRunUpdate
    ) -> InterpretationRunRecord:
        raise NotImplementedError

    @abstractmethod
    async def create_clarification_prompt(
        self, record: ClarificationPromptRecord
    ) -> ClarificationPromptRecord:
        raise NotImplementedError

    @abstractmethod
    async def get_clarification_prompt(
        self, user_id: Id, prompt_id: Id, *, include_deleted: bool = False
    ) -> ClarificationPromptRecord:
        raise NotImplementedError

    @abstractmethod
    async def update_clarification_prompt(
        self, user_id: Id, prompt_id: Id, updates: ClarificationPromptUpdate
    ) -> ClarificationPromptRecord:
        raise NotImplementedError

    @abstractmethod
    async def list_clarification_prompts(
        self,
        user_id: Id,
        *,
        status: ClarificationPromptStatus | None = None,
        material_id: Id | None = None,
        run_id: Id | None = None,
        limit: int = 50,
    ) -> list[ClarificationPromptRecord]:
        raise NotImplementedError

    @abstractmethod
    async def create_clarification_answer(
        self, record: ClarificationAnswerRecord
    ) -> ClarificationAnswerRecord:
        raise NotImplementedError

    @abstractmethod
    async def get_clarification_answer(
        self, user_id: Id, answer_id: Id, *, include_deleted: bool = False
    ) -> ClarificationAnswerRecord:
        raise NotImplementedError

    @abstractmethod
    async def update_clarification_answer(
        self, user_id: Id, answer_id: Id, updates: ClarificationAnswerUpdate
    ) -> ClarificationAnswerRecord:
        raise NotImplementedError

    @abstractmethod
    async def list_clarification_answers(
        self,
        user_id: Id,
        *,
        prompt_id: Id | None = None,
        run_id: Id | None = None,
        limit: int = 50,
    ) -> list[ClarificationAnswerRecord]:
        raise NotImplementedError

    @abstractmethod
    async def create_method_state_capture_run(
        self, record: MethodStateCaptureRunRecord
    ) -> MethodStateCaptureRunRecord:
        raise NotImplementedError

    @abstractmethod
    async def get_method_state_capture_run(
        self, user_id: Id, capture_run_id: Id, *, include_deleted: bool = False
    ) -> MethodStateCaptureRunRecord:
        raise NotImplementedError

    @abstractmethod
    async def get_method_state_capture_run_by_idempotency_key(
        self, user_id: Id, idempotency_key: str
    ) -> MethodStateCaptureRunRecord | None:
        raise NotImplementedError

    @abstractmethod
    async def update_method_state_capture_run(
        self, user_id: Id, capture_run_id: Id, updates: MethodStateCaptureRunUpdate
    ) -> MethodStateCaptureRunRecord:
        raise NotImplementedError

    @abstractmethod
    async def list_method_state_capture_runs(
        self, user_id: Id, *, limit: int = 50
    ) -> list[MethodStateCaptureRunRecord]:
        raise NotImplementedError

    @abstractmethod
    async def store_evidence_items(
        self, user_id: Id, items: list[EvidenceItem]
    ) -> list[EvidenceItem]:
        raise NotImplementedError

    @abstractmethod
    async def get_evidence_item(self, user_id: Id, evidence_id: Id) -> EvidenceItem:
        raise NotImplementedError

    @abstractmethod
    async def list_evidence_for_run(self, user_id: Id, run_id: Id) -> list[EvidenceItem]:
        raise NotImplementedError

    @abstractmethod
    async def create_symbol(self, record: SymbolRecord) -> SymbolRecord:
        raise NotImplementedError

    @abstractmethod
    async def get_symbol(
        self, user_id: Id, symbol_id: Id, *, include_deleted: bool = False
    ) -> SymbolRecord:
        raise NotImplementedError

    @abstractmethod
    async def find_symbol_by_name(self, user_id: Id, canonical_name: str) -> SymbolRecord | None:
        raise NotImplementedError

    @abstractmethod
    async def list_symbols(
        self, user_id: Id, *, include_deleted: bool = False, limit: int = 50
    ) -> list[SymbolRecord]:
        raise NotImplementedError

    @abstractmethod
    async def update_symbol(
        self, user_id: Id, symbol_id: Id, updates: SymbolUpdate
    ) -> SymbolRecord:
        raise NotImplementedError

    @abstractmethod
    async def append_symbol_history(self, entry: SymbolHistoryEntry) -> SymbolHistoryEntry:
        raise NotImplementedError

    @abstractmethod
    async def list_symbol_history(
        self, user_id: Id, symbol_id: Id, *, limit: int = 50
    ) -> list[SymbolHistoryEntry]:
        raise NotImplementedError

    @abstractmethod
    async def delete_symbol(
        self, user_id: Id, symbol_id: Id, *, mode: DeletionMode, reason: str | None = None
    ) -> None:
        raise NotImplementedError

    @abstractmethod
    async def create_pattern(self, record: PatternRecord) -> PatternRecord:
        raise NotImplementedError

    @abstractmethod
    async def get_pattern(
        self, user_id: Id, pattern_id: Id, *, include_deleted: bool = False
    ) -> PatternRecord:
        raise NotImplementedError

    @abstractmethod
    async def list_patterns(
        self,
        user_id: Id,
        *,
        pattern_type: PatternType | None = None,
        include_deleted: bool = False,
        limit: int = 50,
    ) -> list[PatternRecord]:
        raise NotImplementedError

    @abstractmethod
    async def update_pattern(
        self, user_id: Id, pattern_id: Id, updates: PatternUpdate
    ) -> PatternRecord:
        raise NotImplementedError

    @abstractmethod
    async def append_pattern_history(self, entry: PatternHistoryEntry) -> PatternHistoryEntry:
        raise NotImplementedError

    @abstractmethod
    async def list_pattern_history(
        self, user_id: Id, pattern_id: Id, *, limit: int = 50
    ) -> list[PatternHistoryEntry]:
        raise NotImplementedError

    @abstractmethod
    async def delete_pattern(
        self, user_id: Id, pattern_id: Id, *, mode: DeletionMode, reason: str | None = None
    ) -> None:
        raise NotImplementedError

    @abstractmethod
    async def create_typology_lens(self, record: TypologyLensRecord) -> TypologyLensRecord:
        raise NotImplementedError

    @abstractmethod
    async def get_typology_lens(
        self, user_id: Id, lens_id: Id, *, include_deleted: bool = False
    ) -> TypologyLensRecord:
        raise NotImplementedError

    @abstractmethod
    async def list_typology_lenses(
        self, user_id: Id, *, include_deleted: bool = False, limit: int = 20
    ) -> list[TypologyLensRecord]:
        raise NotImplementedError

    @abstractmethod
    async def update_typology_lens(
        self, user_id: Id, lens_id: Id, updates: TypologyLensUpdate
    ) -> TypologyLensRecord:
        raise NotImplementedError

    @abstractmethod
    async def delete_typology_lens(
        self, user_id: Id, lens_id: Id, *, mode: DeletionMode, reason: str | None = None
    ) -> None:
        raise NotImplementedError

    @abstractmethod
    async def create_practice_session(self, record: PracticeSessionRecord) -> PracticeSessionRecord:
        raise NotImplementedError

    @abstractmethod
    async def get_practice_session(
        self, user_id: Id, practice_session_id: Id, *, include_deleted: bool = False
    ) -> PracticeSessionRecord:
        raise NotImplementedError

    @abstractmethod
    async def list_practice_sessions(
        self,
        user_id: Id,
        *,
        material_id: Id | None = None,
        run_id: Id | None = None,
        statuses: list[PracticeSessionStatus] | None = None,
        since: ISODateString | None = None,
        include_deleted: bool = False,
        limit: int = 50,
    ) -> list[PracticeSessionRecord]:
        raise NotImplementedError

    @abstractmethod
    async def update_practice_session(
        self, user_id: Id, practice_session_id: Id, updates: PracticeSessionUpdate
    ) -> PracticeSessionRecord:
        raise NotImplementedError

    @abstractmethod
    async def delete_practice_session(
        self, user_id: Id, practice_session_id: Id, *, mode: DeletionMode
    ) -> None:
        raise NotImplementedError

    @abstractmethod
    async def create_weekly_review(self, record: WeeklyReviewRecord) -> WeeklyReviewRecord:
        raise NotImplementedError

    @abstractmethod
    async def get_weekly_review(
        self, user_id: Id, review_id: Id, *, include_deleted: bool = False
    ) -> WeeklyReviewRecord:
        raise NotImplementedError

    @abstractmethod
    async def list_weekly_reviews(
        self, user_id: Id, *, limit: int = 20
    ) -> list[WeeklyReviewRecord]:
        raise NotImplementedError

    @abstractmethod
    async def delete_weekly_review(self, user_id: Id, review_id: Id, *, mode: DeletionMode) -> None:
        raise NotImplementedError

    @abstractmethod
    async def create_individuation_record(self, record: IndividuationRecord) -> IndividuationRecord:
        raise NotImplementedError

    @abstractmethod
    async def update_individuation_record(
        self, user_id: Id, record_id: Id, updates: IndividuationRecordUpdate
    ) -> IndividuationRecord:
        raise NotImplementedError

    @abstractmethod
    async def get_individuation_record(
        self, user_id: Id, record_id: Id, *, include_deleted: bool = False
    ) -> IndividuationRecord:
        raise NotImplementedError

    @abstractmethod
    async def list_individuation_records(
        self,
        user_id: Id,
        *,
        record_types: list[IndividuationRecordType] | None = None,
        statuses: list[IndividuationRecordStatus] | None = None,
        window_start: ISODateString | None = None,
        window_end: ISODateString | None = None,
        limit: int = 50,
    ) -> list[IndividuationRecord]:
        raise NotImplementedError

    @abstractmethod
    async def create_living_myth_record(self, record: LivingMythRecord) -> LivingMythRecord:
        raise NotImplementedError

    @abstractmethod
    async def update_living_myth_record(
        self, user_id: Id, record_id: Id, updates: LivingMythRecordUpdate
    ) -> LivingMythRecord:
        raise NotImplementedError

    @abstractmethod
    async def get_living_myth_record(
        self, user_id: Id, record_id: Id, *, include_deleted: bool = False
    ) -> LivingMythRecord:
        raise NotImplementedError

    @abstractmethod
    async def list_living_myth_records(
        self,
        user_id: Id,
        *,
        record_types: list[LivingMythRecordType] | None = None,
        statuses: list[LivingMythRecordStatus] | None = None,
        window_start: ISODateString | None = None,
        window_end: ISODateString | None = None,
        limit: int = 50,
    ) -> list[LivingMythRecord]:
        raise NotImplementedError

    @abstractmethod
    async def create_living_myth_review(
        self, record: LivingMythReviewRecord
    ) -> LivingMythReviewRecord:
        raise NotImplementedError

    @abstractmethod
    async def update_living_myth_review(
        self, user_id: Id, review_id: Id, updates: LivingMythReviewUpdate
    ) -> LivingMythReviewRecord:
        raise NotImplementedError

    @abstractmethod
    async def get_living_myth_review(
        self, user_id: Id, review_id: Id, *, include_deleted: bool = False
    ) -> LivingMythReviewRecord:
        raise NotImplementedError

    @abstractmethod
    async def list_living_myth_reviews(
        self,
        user_id: Id,
        *,
        review_type: str | None = None,
        limit: int = 20,
    ) -> list[LivingMythReviewRecord]:
        raise NotImplementedError

    @abstractmethod
    async def create_analysis_packet(self, record: AnalysisPacketRecord) -> AnalysisPacketRecord:
        raise NotImplementedError

    @abstractmethod
    async def get_analysis_packet(
        self, user_id: Id, packet_id: Id, *, include_deleted: bool = False
    ) -> AnalysisPacketRecord:
        raise NotImplementedError

    @abstractmethod
    async def list_analysis_packets(
        self, user_id: Id, *, limit: int = 20
    ) -> list[AnalysisPacketRecord]:
        raise NotImplementedError

    @abstractmethod
    async def create_integration_record(self, record: IntegrationRecord) -> IntegrationRecord:
        raise NotImplementedError

    @abstractmethod
    async def get_integration_record(self, user_id: Id, integration_id: Id) -> IntegrationRecord:
        raise NotImplementedError

    @abstractmethod
    async def list_integration_records(
        self,
        user_id: Id,
        *,
        run_id: Id | None = None,
        material_id: Id | None = None,
        limit: int = 50,
    ) -> list[IntegrationRecord]:
        raise NotImplementedError

    @abstractmethod
    async def update_proposal_decisions(
        self, user_id: Id, run_id: Id, decisions: list[ProposalDecisionRecord]
    ) -> InterpretationRunRecord:
        raise NotImplementedError

    @abstractmethod
    async def create_conscious_attitude_snapshot(
        self, record: ConsciousAttitudeSnapshotRecord
    ) -> ConsciousAttitudeSnapshotRecord:
        raise NotImplementedError

    @abstractmethod
    async def get_conscious_attitude_snapshot(
        self, user_id: Id, snapshot_id: Id, *, include_deleted: bool = False
    ) -> ConsciousAttitudeSnapshotRecord:
        raise NotImplementedError

    @abstractmethod
    async def list_conscious_attitude_snapshots(
        self,
        user_id: Id,
        *,
        filters: ConsciousAttitudeSnapshotFilters | None = None,
    ) -> list[ConsciousAttitudeSnapshotRecord]:
        raise NotImplementedError

    @abstractmethod
    async def update_conscious_attitude_snapshot(
        self, user_id: Id, snapshot_id: Id, updates: ConsciousAttitudeSnapshotUpdate
    ) -> ConsciousAttitudeSnapshotRecord:
        raise NotImplementedError

    @abstractmethod
    async def delete_conscious_attitude_snapshot(
        self, user_id: Id, snapshot_id: Id, *, mode: DeletionMode, reason: str | None = None
    ) -> None:
        raise NotImplementedError

    @abstractmethod
    async def create_amplification_prompt(
        self, record: AmplificationPromptRecord
    ) -> AmplificationPromptRecord:
        raise NotImplementedError

    @abstractmethod
    async def get_amplification_prompt(
        self, user_id: Id, prompt_id: Id, *, include_deleted: bool = False
    ) -> AmplificationPromptRecord:
        raise NotImplementedError

    @abstractmethod
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
        raise NotImplementedError

    @abstractmethod
    async def update_amplification_prompt(
        self, user_id: Id, prompt_id: Id, updates: AmplificationPromptUpdate
    ) -> AmplificationPromptRecord:
        raise NotImplementedError

    @abstractmethod
    async def create_personal_amplification(
        self, record: PersonalAmplificationRecord
    ) -> PersonalAmplificationRecord:
        raise NotImplementedError

    @abstractmethod
    async def get_personal_amplification(
        self, user_id: Id, amplification_id: Id, *, include_deleted: bool = False
    ) -> PersonalAmplificationRecord:
        raise NotImplementedError

    @abstractmethod
    async def list_personal_amplifications(
        self,
        user_id: Id,
        *,
        material_id: Id | None = None,
        run_id: Id | None = None,
        symbol_id: Id | None = None,
        limit: int = 50,
    ) -> list[PersonalAmplificationRecord]:
        raise NotImplementedError

    @abstractmethod
    async def update_personal_amplification(
        self, user_id: Id, amplification_id: Id, updates: PersonalAmplificationUpdate
    ) -> PersonalAmplificationRecord:
        raise NotImplementedError

    @abstractmethod
    async def delete_personal_amplification(
        self, user_id: Id, amplification_id: Id, *, mode: DeletionMode, reason: str | None = None
    ) -> None:
        raise NotImplementedError

    @abstractmethod
    async def create_body_state(self, record: BodyStateRecord) -> BodyStateRecord:
        raise NotImplementedError

    @abstractmethod
    async def get_body_state(
        self, user_id: Id, body_state_id: Id, *, include_deleted: bool = False
    ) -> BodyStateRecord:
        raise NotImplementedError

    @abstractmethod
    async def list_body_states(
        self,
        user_id: Id,
        *,
        material_id: Id | None = None,
        run_id: Id | None = None,
        limit: int = 50,
    ) -> list[BodyStateRecord]:
        raise NotImplementedError

    @abstractmethod
    async def update_body_state(
        self, user_id: Id, body_state_id: Id, updates: BodyStateUpdate
    ) -> BodyStateRecord:
        raise NotImplementedError

    @abstractmethod
    async def delete_body_state(
        self, user_id: Id, body_state_id: Id, *, mode: DeletionMode, reason: str | None = None
    ) -> None:
        raise NotImplementedError

    @abstractmethod
    async def create_goal(self, record: GoalRecord) -> GoalRecord:
        raise NotImplementedError

    @abstractmethod
    async def get_goal(
        self, user_id: Id, goal_id: Id, *, include_deleted: bool = False
    ) -> GoalRecord:
        raise NotImplementedError

    @abstractmethod
    async def list_goals(
        self, user_id: Id, *, include_deleted: bool = False, limit: int = 50
    ) -> list[GoalRecord]:
        raise NotImplementedError

    @abstractmethod
    async def update_goal(self, user_id: Id, goal_id: Id, updates: GoalUpdate) -> GoalRecord:
        raise NotImplementedError

    @abstractmethod
    async def delete_goal(
        self, user_id: Id, goal_id: Id, *, mode: DeletionMode, reason: str | None = None
    ) -> None:
        raise NotImplementedError

    @abstractmethod
    async def create_goal_tension(self, record: GoalTensionRecord) -> GoalTensionRecord:
        raise NotImplementedError

    @abstractmethod
    async def get_goal_tension(
        self, user_id: Id, tension_id: Id, *, include_deleted: bool = False
    ) -> GoalTensionRecord:
        raise NotImplementedError

    @abstractmethod
    async def list_goal_tensions(
        self, user_id: Id, *, include_deleted: bool = False, limit: int = 50
    ) -> list[GoalTensionRecord]:
        raise NotImplementedError

    @abstractmethod
    async def update_goal_tension(
        self, user_id: Id, tension_id: Id, updates: GoalTensionUpdate
    ) -> GoalTensionRecord:
        raise NotImplementedError

    @abstractmethod
    async def delete_goal_tension(
        self, user_id: Id, tension_id: Id, *, mode: DeletionMode, reason: str | None = None
    ) -> None:
        raise NotImplementedError

    @abstractmethod
    async def create_dream_series(self, record: DreamSeriesRecord) -> DreamSeriesRecord:
        raise NotImplementedError

    @abstractmethod
    async def get_dream_series(
        self, user_id: Id, series_id: Id, *, include_deleted: bool = False
    ) -> DreamSeriesRecord:
        raise NotImplementedError

    @abstractmethod
    async def list_dream_series(
        self, user_id: Id, *, include_deleted: bool = False, limit: int = 50
    ) -> list[DreamSeriesRecord]:
        raise NotImplementedError

    @abstractmethod
    async def update_dream_series(
        self, user_id: Id, series_id: Id, updates: DreamSeriesUpdate
    ) -> DreamSeriesRecord:
        raise NotImplementedError

    @abstractmethod
    async def delete_dream_series(
        self, user_id: Id, series_id: Id, *, mode: DeletionMode, reason: str | None = None
    ) -> None:
        raise NotImplementedError

    @abstractmethod
    async def create_dream_series_membership(
        self, record: DreamSeriesMembershipRecord
    ) -> DreamSeriesMembershipRecord:
        raise NotImplementedError

    @abstractmethod
    async def list_dream_series_memberships(
        self,
        user_id: Id,
        *,
        series_id: Id | None = None,
        material_id: Id | None = None,
        include_deleted: bool = False,
        limit: int = 50,
    ) -> list[DreamSeriesMembershipRecord]:
        raise NotImplementedError

    @abstractmethod
    async def update_dream_series_membership(
        self, user_id: Id, membership_id: Id, updates: DreamSeriesMembershipUpdate
    ) -> DreamSeriesMembershipRecord:
        raise NotImplementedError

    @abstractmethod
    async def create_cultural_frame(self, record: CulturalFrameRecord) -> CulturalFrameRecord:
        raise NotImplementedError

    @abstractmethod
    async def get_cultural_frame(
        self, user_id: Id, cultural_frame_id: Id, *, include_deleted: bool = False
    ) -> CulturalFrameRecord:
        raise NotImplementedError

    @abstractmethod
    async def list_cultural_frames(
        self, user_id: Id, *, include_deleted: bool = False, limit: int = 50
    ) -> list[CulturalFrameRecord]:
        raise NotImplementedError

    @abstractmethod
    async def update_cultural_frame(
        self, user_id: Id, cultural_frame_id: Id, updates: CulturalFrameUpdate
    ) -> CulturalFrameRecord:
        raise NotImplementedError

    @abstractmethod
    async def create_collective_amplification(
        self, record: CollectiveAmplificationRecord
    ) -> CollectiveAmplificationRecord:
        raise NotImplementedError

    @abstractmethod
    async def list_collective_amplifications(
        self,
        user_id: Id,
        *,
        material_id: Id | None = None,
        run_id: Id | None = None,
        symbol_id: Id | None = None,
        limit: int = 50,
    ) -> list[CollectiveAmplificationRecord]:
        raise NotImplementedError

    @abstractmethod
    async def update_collective_amplification(
        self, user_id: Id, amplification_id: Id, updates: CollectiveAmplificationUpdate
    ) -> CollectiveAmplificationRecord:
        raise NotImplementedError

    @abstractmethod
    async def create_consent_preference(
        self, record: ConsentPreferenceRecord
    ) -> ConsentPreferenceRecord:
        raise NotImplementedError

    @abstractmethod
    async def list_consent_preferences(
        self, user_id: Id, *, limit: int = 50
    ) -> list[ConsentPreferenceRecord]:
        raise NotImplementedError

    @abstractmethod
    async def update_consent_preference(
        self, user_id: Id, preference_id: Id, updates: ConsentPreferenceUpdate
    ) -> ConsentPreferenceRecord:
        raise NotImplementedError

    @abstractmethod
    async def upsert_adaptation_profile(
        self, user_id: Id, record: UserAdaptationProfileRecord
    ) -> UserAdaptationProfileRecord:
        raise NotImplementedError

    @abstractmethod
    async def get_adaptation_profile(self, user_id: Id) -> UserAdaptationProfileRecord | None:
        raise NotImplementedError

    @abstractmethod
    async def update_adaptation_profile(
        self, user_id: Id, profile_id: Id, updates: UserAdaptationProfileUpdate
    ) -> UserAdaptationProfileRecord:
        raise NotImplementedError

    @abstractmethod
    async def create_interaction_feedback(
        self, record: InteractionFeedbackRecord
    ) -> InteractionFeedbackRecord:
        raise NotImplementedError

    @abstractmethod
    async def list_interaction_feedback(
        self,
        user_id: Id,
        *,
        domain: str | None = None,
        target_id: Id | None = None,
        limit: int = 50,
    ) -> list[InteractionFeedbackRecord]:
        raise NotImplementedError

    @abstractmethod
    async def create_journey(self, record: JourneyRecord) -> JourneyRecord:
        raise NotImplementedError

    @abstractmethod
    async def list_journeys(
        self, user_id: Id, *, include_deleted: bool = False, limit: int = 50
    ) -> list[JourneyRecord]:
        raise NotImplementedError

    @abstractmethod
    async def get_journey(
        self, user_id: Id, journey_id: Id, *, include_deleted: bool = False
    ) -> JourneyRecord:
        raise NotImplementedError

    @abstractmethod
    async def update_journey(
        self, user_id: Id, journey_id: Id, updates: JourneyUpdate
    ) -> JourneyRecord:
        raise NotImplementedError

    @abstractmethod
    async def create_journey_experiment(
        self, record: JourneyExperimentRecord
    ) -> JourneyExperimentRecord:
        raise NotImplementedError

    @abstractmethod
    async def list_journey_experiments(
        self,
        user_id: Id,
        *,
        journey_ids: list[Id] | None = None,
        statuses: list[JourneyExperimentStatus] | None = None,
        include_deleted: bool = False,
        limit: int = 50,
    ) -> list[JourneyExperimentRecord]:
        raise NotImplementedError

    @abstractmethod
    async def get_journey_experiment(
        self, user_id: Id, experiment_id: Id, *, include_deleted: bool = False
    ) -> JourneyExperimentRecord:
        raise NotImplementedError

    @abstractmethod
    async def update_journey_experiment(
        self, user_id: Id, experiment_id: Id, updates: JourneyExperimentUpdate
    ) -> JourneyExperimentRecord:
        raise NotImplementedError

    @abstractmethod
    async def create_proactive_brief(self, record: ProactiveBriefRecord) -> ProactiveBriefRecord:
        raise NotImplementedError

    @abstractmethod
    async def list_proactive_briefs(
        self,
        user_id: Id,
        *,
        statuses: list[ProactiveBriefStatus] | None = None,
        brief_type: ProactiveBriefType | None = None,
        since: ISODateString | None = None,
        include_deleted: bool = False,
        limit: int = 50,
    ) -> list[ProactiveBriefRecord]:
        raise NotImplementedError

    @abstractmethod
    async def update_proactive_brief(
        self, user_id: Id, brief_id: Id, updates: ProactiveBriefUpdate
    ) -> ProactiveBriefRecord:
        raise NotImplementedError

    @abstractmethod
    async def get_proactive_brief(
        self, user_id: Id, brief_id: Id, *, include_deleted: bool = False
    ) -> ProactiveBriefRecord:
        raise NotImplementedError

    @abstractmethod
    async def build_hermes_memory_context_from_records(
        self, user_id: Id, *, max_items: int | None = None
    ) -> HermesMemoryContext:
        raise NotImplementedError

    @abstractmethod
    async def build_memory_kernel_snapshot(
        self,
        user_id: Id,
        *,
        query: MemoryRetrievalQuery | None = None,
    ) -> MemoryKernelSnapshot:
        raise NotImplementedError

    @abstractmethod
    async def query_graph(
        self,
        user_id: Id,
        *,
        query: GraphQuery | None = None,
    ) -> GraphQueryResult:
        raise NotImplementedError

    @abstractmethod
    async def build_life_context_snapshot_from_records(
        self,
        user_id: Id,
        *,
        window_start: ISODateString,
        window_end: ISODateString,
        exclude_material_id: Id | None = None,
    ) -> LifeContextSnapshot | None:
        raise NotImplementedError

    @abstractmethod
    async def build_method_context_snapshot_from_records(
        self,
        user_id: Id,
        *,
        window_start: ISODateString,
        window_end: ISODateString,
        material_id: Id | None = None,
    ) -> MethodContextSnapshot | None:
        raise NotImplementedError

    @abstractmethod
    async def build_thread_digests_from_records(
        self,
        user_id: Id,
        *,
        window_start: ISODateString,
        window_end: ISODateString,
        material_id: Id | None = None,
    ) -> list[ThreadDigest]:
        raise NotImplementedError

    @abstractmethod
    async def build_circulation_summary_input(
        self,
        user_id: Id,
        *,
        window_start: ISODateString,
        window_end: ISODateString,
    ) -> CirculationSummaryInput:
        raise NotImplementedError

    @abstractmethod
    async def build_threshold_review_input(
        self,
        user_id: Id,
        *,
        window_start: ISODateString,
        window_end: ISODateString,
        threshold_process_id: Id | None = None,
        explicit_question: str | None = None,
    ) -> ThresholdReviewInput:
        raise NotImplementedError

    @abstractmethod
    async def build_living_myth_review_input(
        self,
        user_id: Id,
        *,
        window_start: ISODateString,
        window_end: ISODateString,
        explicit_question: str | None = None,
    ) -> LivingMythReviewInput:
        raise NotImplementedError

    @abstractmethod
    async def build_analysis_packet_input(
        self,
        user_id: Id,
        *,
        window_start: ISODateString,
        window_end: ISODateString,
        packet_focus: str | None = None,
        explicit_question: str | None = None,
    ) -> AnalysisPacketInput:
        raise NotImplementedError

    @abstractmethod
    async def get_dashboard_summary(self, user_id: Id) -> DashboardSummary:
        raise NotImplementedError
