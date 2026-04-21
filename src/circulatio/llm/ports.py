from __future__ import annotations

from typing import Protocol

from ..domain.method_state import MethodStateRoutingInput
from ..domain.types import (
    AnalysisPacketInput,
    CirculationSummaryInput,
    LifeContextSnapshot,
    LivingMythReviewInput,
    MaterialInterpretationInput,
    PracticeRecommendationInput,
    RhythmicBriefInput,
    ThresholdReviewInput,
)
from .contracts import (
    LlmAliveTodayOutput,
    LlmAnalysisPacketOutput,
    LlmInterpretationOutput,
    LlmLivingMythReviewOutput,
    LlmMethodStateRoutingOutput,
    LlmPracticeOutput,
    LlmRhythmicBriefOutput,
    LlmThresholdReviewOutput,
    LlmWeeklyReviewOutput,
)


class CirculatioLlmPort(Protocol):
    async def interpret_material(
        self,
        input_data: MaterialInterpretationInput,
    ) -> LlmInterpretationOutput: ...

    async def generate_weekly_review(
        self,
        input_data: CirculationSummaryInput,
    ) -> LlmWeeklyReviewOutput: ...

    async def generate_alive_today(
        self,
        input_data: CirculationSummaryInput,
    ) -> LlmAliveTodayOutput: ...

    async def generate_practice(
        self,
        input_data: PracticeRecommendationInput,
    ) -> LlmPracticeOutput: ...

    async def generate_rhythmic_brief(
        self,
        input_data: RhythmicBriefInput,
    ) -> LlmRhythmicBriefOutput: ...

    async def generate_threshold_review(
        self,
        input_data: ThresholdReviewInput,
    ) -> LlmThresholdReviewOutput: ...

    async def generate_living_myth_review(
        self,
        input_data: LivingMythReviewInput,
    ) -> LlmLivingMythReviewOutput: ...

    async def generate_analysis_packet(
        self,
        input_data: AnalysisPacketInput,
    ) -> LlmAnalysisPacketOutput: ...

    async def summarize_life_context(
        self,
        *,
        user_id: str,
        window_start: str,
        window_end: str,
        raw_context: dict[str, object],
    ) -> LifeContextSnapshot: ...


class CirculatioMethodStateLlmPort(Protocol):
    async def route_method_state_response(
        self,
        input_data: MethodStateRoutingInput,
    ) -> LlmMethodStateRoutingOutput: ...
