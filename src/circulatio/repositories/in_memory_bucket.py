from __future__ import annotations

from dataclasses import dataclass, field

from ..domain.adaptation import UserAdaptationProfileRecord
from ..domain.amplifications import AmplificationPromptRecord, PersonalAmplificationRecord
from ..domain.clarifications import ClarificationAnswerRecord, ClarificationPromptRecord
from ..domain.conscious_attitude import ConsciousAttitudeSnapshotRecord
from ..domain.context import ContextSnapshot
from ..domain.culture import CollectiveAmplificationRecord, CulturalFrameRecord
from ..domain.dream_series import DreamSeriesMembershipRecord, DreamSeriesRecord
from ..domain.feedback import InteractionFeedbackRecord
from ..domain.goals import GoalRecord, GoalTensionRecord
from ..domain.individuation import IndividuationRecord
from ..domain.integration import IntegrationRecord
from ..domain.interpretations import InterpretationRunRecord
from ..domain.journey_experiments import JourneyExperimentRecord
from ..domain.journeys import JourneyRecord
from ..domain.living_myth import AnalysisPacketRecord, LivingMythRecord, LivingMythReviewRecord
from ..domain.materials import MaterialRecord, MaterialRevision
from ..domain.method_state import MethodStateCaptureRunRecord
from ..domain.patterns import PatternHistoryEntry, PatternRecord
from ..domain.practices import PracticeSessionRecord
from ..domain.proactive import ProactiveBriefRecord
from ..domain.readiness import ConsentPreferenceRecord
from ..domain.reviews import WeeklyReviewRecord
from ..domain.soma import BodyStateRecord
from ..domain.symbols import SymbolHistoryEntry, SymbolRecord
from ..domain.types import (
    CulturalOriginSummary,
    EvidenceItem,
    Id,
    InterpretationFeedbackSummary,
    MaterialSummary,
    SuppressedHypothesisSummary,
)
from ..domain.typology import TypologyLensRecord


@dataclass
class UserCirculatioBucket:
    materials: dict[Id, MaterialRecord] = field(default_factory=dict)
    material_revisions: dict[Id, list[MaterialRevision]] = field(default_factory=dict)
    material_summaries: dict[Id, MaterialSummary] = field(default_factory=dict)
    context_snapshots: dict[Id, ContextSnapshot] = field(default_factory=dict)
    interpretation_runs: dict[Id, InterpretationRunRecord] = field(default_factory=dict)
    clarification_prompts: dict[Id, ClarificationPromptRecord] = field(default_factory=dict)
    clarification_answers: dict[Id, ClarificationAnswerRecord] = field(default_factory=dict)
    evidence: dict[Id, EvidenceItem] = field(default_factory=dict)
    symbols: dict[Id, SymbolRecord] = field(default_factory=dict)
    symbol_name_index: dict[str, Id] = field(default_factory=dict)
    symbol_history: dict[Id, list[SymbolHistoryEntry]] = field(default_factory=dict)
    patterns: dict[Id, PatternRecord] = field(default_factory=dict)
    pattern_history: dict[Id, list[PatternHistoryEntry]] = field(default_factory=dict)
    typology_lenses: dict[Id, TypologyLensRecord] = field(default_factory=dict)
    practice_sessions: dict[Id, PracticeSessionRecord] = field(default_factory=dict)
    integrations: dict[Id, IntegrationRecord] = field(default_factory=dict)
    weekly_reviews: dict[Id, WeeklyReviewRecord] = field(default_factory=dict)
    individuation_records: dict[Id, IndividuationRecord] = field(default_factory=dict)
    living_myth_records: dict[Id, LivingMythRecord] = field(default_factory=dict)
    living_myth_reviews: dict[Id, LivingMythReviewRecord] = field(default_factory=dict)
    analysis_packets: dict[Id, AnalysisPacketRecord] = field(default_factory=dict)
    method_state_capture_runs: dict[Id, MethodStateCaptureRunRecord] = field(default_factory=dict)
    conscious_attitudes: dict[Id, ConsciousAttitudeSnapshotRecord] = field(default_factory=dict)
    amplification_prompts: dict[Id, AmplificationPromptRecord] = field(default_factory=dict)
    personal_amplifications: dict[Id, PersonalAmplificationRecord] = field(default_factory=dict)
    body_states: dict[Id, BodyStateRecord] = field(default_factory=dict)
    goals: dict[Id, GoalRecord] = field(default_factory=dict)
    goal_tensions: dict[Id, GoalTensionRecord] = field(default_factory=dict)
    dream_series: dict[Id, DreamSeriesRecord] = field(default_factory=dict)
    dream_series_memberships: dict[Id, DreamSeriesMembershipRecord] = field(default_factory=dict)
    cultural_frames: dict[Id, CulturalFrameRecord] = field(default_factory=dict)
    collective_amplifications: dict[Id, CollectiveAmplificationRecord] = field(default_factory=dict)
    consent_preferences: dict[Id, ConsentPreferenceRecord] = field(default_factory=dict)
    adaptation_profiles: dict[Id, UserAdaptationProfileRecord] = field(default_factory=dict)
    journeys: dict[Id, JourneyRecord] = field(default_factory=dict)
    journey_experiments: dict[Id, JourneyExperimentRecord] = field(default_factory=dict)
    proactive_briefs: dict[Id, ProactiveBriefRecord] = field(default_factory=dict)
    feedback: list[InterpretationFeedbackSummary] = field(default_factory=list)
    interaction_feedback: list[InteractionFeedbackRecord] = field(default_factory=list)
    cultural_origins: list[CulturalOriginSummary] = field(default_factory=list)
    suppressed: dict[str, SuppressedHypothesisSummary] = field(default_factory=dict)
    applied_proposal_ids: set[Id] = field(default_factory=set)
