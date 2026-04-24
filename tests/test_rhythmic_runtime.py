from __future__ import annotations

import asyncio
import os
import sys
import unittest

sys.path.insert(0, os.path.abspath("src"))

from circulatio.adapters.context_adapter import ContextAdapter
from circulatio.adapters.context_builder import CirculatioLifeContextBuilder
from circulatio.application.circulatio_service import CirculatioService
from circulatio.core.circulatio_core import CirculatioCore
from circulatio.domain.ids import create_id
from circulatio.repositories.in_memory_circulatio_repository import InMemoryCirculatioRepository
from tests._helpers import FakeCirculatioLlm


class RhythmicRuntimeTests(unittest.TestCase):
    def _service(self) -> tuple[InMemoryCirculatioRepository, CirculatioService]:
        repository = InMemoryCirculatioRepository()
        llm = FakeCirculatioLlm()
        core = CirculatioCore(repository, llm=llm)
        adapter = ContextAdapter(
            repository,
            life_context_builder=CirculatioLifeContextBuilder(repository),
        )
        service = CirculatioService(repository, core, context_adapter=adapter)
        return repository, service

    async def _seed_practice_followup(self, repository: InMemoryCirculatioRepository) -> None:
        await repository.create_practice_session(
            {
                "id": "practice_1",
                "userId": "user_1",
                "practiceType": "journaling",
                "reason": "Hold the image lightly.",
                "instructions": ["Write it down."],
                "durationMinutes": 5,
                "contraindicationsChecked": ["none"],
                "requiresConsent": False,
                "status": "recommended",
                "followUpPrompt": "What changed after staying with it?",
                "nextFollowUpDueAt": "2026-04-19T00:00:00Z",
                "createdAt": "2026-04-18T00:00:00Z",
                "updatedAt": "2026-04-18T00:00:00Z",
            }
        )

    async def _seed_journey(self, repository: InMemoryCirculatioRepository) -> None:
        await repository.create_journey(
            {
                "id": "journey_1",
                "userId": "user_1",
                "label": "House sequence",
                "status": "active",
                "relatedMaterialIds": [],
                "relatedSymbolIds": [],
                "relatedPatternIds": [],
                "relatedDreamSeriesIds": [],
                "relatedGoalIds": [],
                "currentQuestion": "What is shifting?",
                "nextReviewDueAt": "2026-04-19T00:00:00Z",
                "createdAt": "2026-04-10T00:00:00Z",
                "updatedAt": "2026-04-10T00:00:00Z",
            }
        )

    def test_candidate_dedupe_by_trigger_key(self) -> None:
        async def run() -> None:
            repository, service = self._service()
            await self._seed_practice_followup(repository)
            first = await service.generate_rhythmic_briefs({"userId": "user_1", "limit": 1})
            second = await service.generate_rhythmic_briefs({"userId": "user_1", "limit": 1})
            self.assertEqual(len(first["briefs"]), 1)
            self.assertEqual(second["briefs"], [])

        asyncio.run(run())

    def test_dismissed_cooldown_suppresses_repeat(self) -> None:
        async def run() -> None:
            repository, service = self._service()
            await self._seed_practice_followup(repository)
            first = await service.generate_rhythmic_briefs({"userId": "user_1"})
            await service.respond_rhythmic_brief(
                {"userId": "user_1", "briefId": first["briefs"][0]["id"], "action": "dismissed"}
            )
            second = await service.generate_rhythmic_briefs({"userId": "user_1"})
            self.assertEqual(second["briefs"], [])

        asyncio.run(run())

    def test_daily_max_suppresses_scheduled_spam(self) -> None:
        async def run() -> None:
            repository, service = self._service()
            await self._seed_practice_followup(repository)
            await service.set_consent_preference(
                {"userId": "user_1", "scope": "proactive_briefing", "status": "allow"}
            )
            first = await service.generate_rhythmic_briefs(
                {"userId": "user_1", "source": "scheduled", "limit": 1}
            )
            if first["briefs"]:
                await service.respond_rhythmic_brief(
                    {"userId": "user_1", "briefId": first["briefs"][0]["id"], "action": "shown"}
                )
            second = await service.generate_rhythmic_briefs(
                {"userId": "user_1", "source": "scheduled", "limit": 1}
            )
            self.assertEqual(second["briefs"], [])

        asyncio.run(run())

    def test_manual_source_bypasses_daily_max_but_not_active_duplicate(self) -> None:
        async def run() -> None:
            repository, service = self._service()
            await self._seed_practice_followup(repository)
            first = await service.generate_rhythmic_briefs(
                {"userId": "user_1", "source": "manual", "limit": 1}
            )
            second = await service.generate_rhythmic_briefs(
                {"userId": "user_1", "source": "manual", "limit": 1}
            )
            self.assertEqual(len(first["briefs"]), 1)
            self.assertEqual(second["briefs"], [])

        asyncio.run(run())

    def test_shown_updates_journey_last_briefed_at(self) -> None:
        async def run() -> None:
            repository, service = self._service()
            await self._seed_journey(repository)
            brief = await repository.create_proactive_brief(
                {
                    "id": create_id("proactive_brief"),
                    "userId": "user_1",
                    "briefType": "journey_checkin",
                    "status": "candidate",
                    "title": "Journey check-in",
                    "summary": "An active journey may be ready for a bounded check-in.",
                    "relatedJourneyIds": ["journey_1"],
                    "relatedMaterialIds": [],
                    "relatedSymbolIds": [],
                    "relatedPracticeSessionIds": [],
                    "evidenceIds": [],
                    "createdAt": "2026-04-19T00:00:00Z",
                    "updatedAt": "2026-04-19T00:00:00Z",
                }
            )
            await service.respond_rhythmic_brief(
                {"userId": "user_1", "briefId": brief["id"], "action": "shown"}
            )
            journeys = await repository.list_journeys("user_1")
            self.assertTrue(journeys[0]["lastBriefedAt"])

        asyncio.run(run())

    def test_grounding_first_filters_symbolic_briefs_before_generation(self) -> None:
        async def run() -> None:
            repository, service = self._service()
            await self._seed_practice_followup(repository)
            await self._seed_journey(repository)
            await service.capture_reality_anchors(
                {
                    "userId": "user_1",
                    "summary": "Containment is thin and ordinary support needs to lead.",
                    "anchorSummary": "Grounding comes before symbolic invitations right now.",
                    "groundingRecommendation": "grounding_first",
                }
            )
            result = await service.generate_rhythmic_briefs(
                {"userId": "user_1", "source": "manual", "limit": 5}
            )
            self.assertTrue(result["briefs"])
            self.assertTrue(
                all(brief["briefType"] == "practice_followup" for brief in result["briefs"])
            )

        asyncio.run(run())

    def test_adaptation_profile_personalizes_rhythmic_brief_action(self) -> None:
        async def run() -> None:
            repository, service = self._service()
            await self._seed_journey(repository)
            await service.capture_reality_anchors(
                {
                    "userId": "user_1",
                    "summary": "Outer life is steady enough for light contact.",
                    "anchorSummary": "Containment can hold a simple check-in.",
                    "groundingRecommendation": "clear_for_depth",
                }
            )
            await service.set_adaptation_preferences(
                user_id="user_1",
                scope="interpretation",
                preferences={"modalityBias": "body"},
            )
            result = await service.generate_rhythmic_briefs(
                {"userId": "user_1", "source": "manual", "limit": 1}
            )
            self.assertEqual(len(result["briefs"]), 1)
            self.assertEqual(
                result["briefs"][0]["suggestedAction"],
                "You can notice what your body does around this before naming meaning.",
            )

        asyncio.run(run())

    def test_goal_tension_brief_inherits_related_journey_from_thread_digest(self) -> None:
        async def run() -> None:
            _, service = self._service()
            first_goal = await service.upsert_goal(
                {"userId": "user_1", "label": "Speak directly", "status": "active"}
            )
            second_goal = await service.upsert_goal(
                {"userId": "user_1", "label": "Stay safe", "status": "active"}
            )
            await service.upsert_goal_tension(
                {
                    "userId": "user_1",
                    "goalIds": [first_goal["id"], second_goal["id"]],
                    "tensionSummary": "Directness and safety are both alive.",
                    "polarityLabels": ["directness", "safety"],
                    "status": "active",
                }
            )
            journey = await service.create_journey(
                {
                    "userId": "user_1",
                    "label": "Directness thread",
                    "currentQuestion": "How can directness stay embodied?",
                    "relatedGoalIds": [first_goal["id"]],
                    "nextReviewDueAt": "2999-01-01T00:00:00Z",
                }
            )

            result = await service.generate_rhythmic_briefs(
                {"userId": "user_1", "source": "manual", "limit": 5}
            )

            goal_tension_brief = next(
                brief
                for brief in result["briefs"]
                if str(brief.get("triggerKey") or "").startswith("daily:goal_tension:")
            )
            self.assertEqual(goal_tension_brief["relatedJourneyIds"], [journey["id"]])

        asyncio.run(run())

    def test_acted_and_dismissed_update_adaptation_counts(self) -> None:
        async def run() -> None:
            repository, service = self._service()
            brief = await repository.create_proactive_brief(
                {
                    "id": create_id("proactive_brief"),
                    "userId": "user_1",
                    "briefType": "daily",
                    "status": "candidate",
                    "title": "Daily pattern note",
                    "summary": "A recent thread may be ready for a light surfacing.",
                    "relatedJourneyIds": [],
                    "relatedMaterialIds": [],
                    "relatedSymbolIds": [],
                    "relatedPracticeSessionIds": [],
                    "evidenceIds": [],
                    "createdAt": "2026-04-19T00:00:00Z",
                    "updatedAt": "2026-04-19T00:00:00Z",
                }
            )
            await service.respond_rhythmic_brief(
                {"userId": "user_1", "briefId": brief["id"], "action": "dismissed"}
            )
            acted = await repository.create_proactive_brief(
                {
                    "id": create_id("proactive_brief"),
                    "userId": "user_1",
                    "briefType": "daily",
                    "status": "candidate",
                    "title": "Daily pattern note",
                    "summary": "A recent thread may be ready for a light surfacing.",
                    "relatedJourneyIds": [],
                    "relatedMaterialIds": [],
                    "relatedSymbolIds": [],
                    "relatedPracticeSessionIds": [],
                    "evidenceIds": [],
                    "createdAt": "2026-04-19T01:00:00Z",
                    "updatedAt": "2026-04-19T01:00:00Z",
                }
            )
            await service.respond_rhythmic_brief(
                {"userId": "user_1", "briefId": acted["id"], "action": "acted_on"}
            )
            profile = await repository.get_adaptation_profile("user_1")
            self.assertEqual(profile["sampleCounts"]["rhythmic_brief_dismissed"], 1)
            self.assertEqual(profile["sampleCounts"]["rhythmic_brief_acted_on"], 1)

        asyncio.run(run())


if __name__ == "__main__":
    unittest.main()
