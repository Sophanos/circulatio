from __future__ import annotations

import asyncio
import os
import sys
import unittest

sys.path.insert(0, os.path.abspath("src"))

from circulatio.adapters.context_adapter import ContextAdapter
from circulatio.adapters.context_builder import CirculatioLifeContextBuilder
from circulatio.adapters.method_context_builder import CirculatioMethodContextBuilder
from circulatio.application.circulatio_service import CirculatioService
from circulatio.core.circulatio_core import CirculatioCore
from circulatio.hermes.amplification_sources import default_trusted_amplification_sources
from circulatio.repositories.in_memory_circulatio_repository import InMemoryCirculatioRepository
from tests._helpers import FakeCirculatioLlm


class FakeLifeOs:
    async def get_life_context_snapshot(self, *, user_id: str, window_start: str, window_end: str):
        del user_id
        return {
            "windowStart": window_start,
            "windowEnd": window_end,
            "lifeEventRefs": [
                {
                    "id": "life_event_1",
                    "summary": "Repeated conflict with manager",
                    "symbolicAnnotation": "authority conflict",
                }
            ],
            "focusSummary": "Focus has been low all week",
            "source": "hermes-life-os",
        }


class PresentationPlanServiceTests(unittest.TestCase):
    def _service(self) -> tuple[InMemoryCirculatioRepository, CirculatioService, FakeCirculatioLlm]:
        repository = InMemoryCirculatioRepository()
        llm = FakeCirculatioLlm()
        core = CirculatioCore(repository, llm=llm)
        context_adapter = ContextAdapter(
            repository,
            life_os=FakeLifeOs(),
            life_context_builder=CirculatioLifeContextBuilder(repository),
            method_context_builder=CirculatioMethodContextBuilder(repository),
        )
        service = CirculatioService(
            repository,
            core,
            context_adapter=context_adapter,
            method_state_llm=llm,
            trusted_amplification_sources=default_trusted_amplification_sources(),
        )
        return repository, service, llm

    def test_plan_ritual_weekly_integration_uses_read_only_source_without_writes(self) -> None:
        async def run() -> None:
            repository, service, llm = self._service()
            await service.store_material(
                {
                    "userId": "user_1",
                    "materialType": "reflection",
                    "text": "The snake image returned after the meeting.",
                    "materialDate": "2026-04-15T08:00:00Z",
                }
            )

            workflow = await service.plan_ritual(
                {
                    "userId": "user_1",
                    "ritualIntent": "weekly_integration",
                    "narrativeMode": "hybrid",
                    "windowStart": "2026-04-12T00:00:00Z",
                    "windowEnd": "2026-04-19T23:59:59Z",
                    "requestedSurfaces": {
                        "breath": {"enabled": True},
                        "meditation": {"enabled": True},
                        "captions": {"enabled": True},
                        "cinema": {"enabled": False},
                    },
                    "renderPolicy": {
                        "mode": "dry_run_manifest",
                        "externalProvidersAllowed": False,
                        "videoAllowed": False,
                    },
                }
            )

            plan = workflow["plan"]
            self.assertEqual(plan["schemaVersion"], "circulatio.presentation.plan.v1")
            self.assertEqual(plan["sourceType"], "weekly_review_summary")
            self.assertEqual(plan["privacyClass"], "private")
            self.assertTrue(plan["voiceScript"]["segments"])
            self.assertTrue(plan["breath"]["enabled"])
            self.assertTrue(plan["meditation"]["enabled"])
            self.assertEqual(workflow["costEstimate"]["totalEstimated"], 0.0)
            self.assertIn("captions", workflow["renderRequest"]["allowedSurfaces"])
            self.assertNotIn("cinema", workflow["renderRequest"]["allowedSurfaces"])
            self.assertEqual(len(llm.review_calls), 1)
            self.assertEqual(llm.interpret_calls, [])
            self.assertEqual(await repository.list_interpretation_runs("user_1"), [])
            self.assertEqual(await repository.list_weekly_reviews("user_1"), [])
            self.assertEqual(await repository.list_practice_sessions("user_1"), [])

        asyncio.run(run())

    def test_plan_ritual_high_activation_disables_holds_and_cinema(self) -> None:
        async def run() -> None:
            repository, service, llm = self._service()
            workflow = await service.plan_ritual(
                {
                    "userId": "user_1",
                    "ritualIntent": "alive_today",
                    "windowStart": "2026-04-12T00:00:00Z",
                    "windowEnd": "2026-04-19T23:59:59Z",
                    "requestedSurfaces": {
                        "breath": {
                            "enabled": True,
                            "request": {"pattern": "box_breath", "cycles": 3},
                        },
                        "cinema": {"enabled": True, "maxDurationSeconds": 30},
                    },
                    "renderPolicy": {"videoAllowed": True},
                    "safetyContext": {"userReportedActivation": "high"},
                }
            )

            plan = workflow["plan"]
            self.assertEqual(plan["breath"]["pattern"], "orienting")
            self.assertEqual(plan["breath"]["holdSeconds"], 0)
            self.assertFalse(plan["visualPromptPlan"]["cinema"]["enabled"])
            self.assertIn("cinema", plan["safetyBoundary"]["blockedSurfaces"])
            self.assertIn("presentation_grounding_only_safety_adjustment", workflow["warnings"])
            self.assertEqual(len(llm.alive_today_calls), 1)
            self.assertEqual(await repository.list_interpretation_runs("user_1"), [])
            self.assertEqual(await repository.list_weekly_reviews("user_1"), [])

        asyncio.run(run())

    def test_plan_ritual_omits_pending_refs_and_external_image_prompt_when_disabled(self) -> None:
        async def run() -> None:
            _, service, _ = self._service()
            workflow = await service.plan_ritual(
                {
                    "userId": "user_1",
                    "ritualIntent": "guided_ritual",
                    "windowStart": "2026-04-12T00:00:00Z",
                    "windowEnd": "2026-04-19T23:59:59Z",
                    "sourceRefs": [
                        {
                            "sourceType": "material",
                            "recordId": "material_safe_summary",
                            "title": "Dream summary",
                            "approvalState": "approved",
                        },
                        {
                            "sourceType": "weekly_review",
                            "recordId": "weekly_review_pending",
                            "title": "Pending review",
                            "approvalState": "pending",
                        },
                    ],
                    "requestedSurfaces": {
                        "image": {"enabled": True},
                        "cinema": {"enabled": True},
                    },
                    "renderPolicy": {
                        "externalProvidersAllowed": False,
                        "videoAllowed": False,
                    },
                }
            )

            plan = workflow["plan"]
            self.assertEqual(len(plan["sourceRefs"]), 1)
            self.assertEqual(plan["sourceRefs"][0]["recordId"], "material_safe_summary")
            self.assertFalse(plan["visualPromptPlan"]["image"]["enabled"])
            self.assertNotIn("prompt", plan["visualPromptPlan"]["image"])
            self.assertFalse(plan["visualPromptPlan"]["cinema"]["enabled"])
            self.assertIn("pending_source_ref_omitted", workflow["warnings"])
            self.assertIn("image_disabled_without_external_providers", workflow["warnings"])
            self.assertIn("cinema_disabled_without_video_allowed", workflow["warnings"])

        asyncio.run(run())

