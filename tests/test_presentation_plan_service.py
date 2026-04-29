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

    def test_plan_ritual_photo_podcast_surfaces_are_allowed_and_read_only(self) -> None:
        async def run() -> None:
            repository, service, llm = self._service()
            workflow = await service.plan_ritual(
                {
                    "userId": "user_1",
                    "ritualIntent": "journey_broadcast",
                    "narrativeMode": "full_guided",
                    "windowStart": "2026-04-12T00:00:00Z",
                    "windowEnd": "2026-04-19T23:59:59Z",
                    "requestedSurfaces": {
                        "audio": {
                            "enabled": True,
                            "tone": "steady",
                            "pace": "measured",
                            "voiceId": "af_nicole",
                            "speed": 0.86,
                        },
                        "captions": {"enabled": True, "format": "webvtt"},
                        "image": {
                            "enabled": True,
                            "styleIntent": "symbolic_non_literal",
                            "allowExternalGeneration": True,
                        },
                        "cinema": {"enabled": False},
                    },
                    "renderPolicy": {
                        "mode": "render_static",
                        "defaultDurationSeconds": 150,
                        "maxDurationSeconds": 180,
                        "externalProvidersAllowed": True,
                        "videoAllowed": False,
                        "providerAllowlist": ["mock", "chutes"],
                        "maxCost": {"currency": "USD", "amount": 0.05},
                    },
                }
            )

            plan = workflow["plan"]
            self.assertEqual(plan["duration"]["targetSeconds"], 150)
            self.assertIn("audio", workflow["renderRequest"]["allowedSurfaces"])
            self.assertIn("captions", workflow["renderRequest"]["allowedSurfaces"])
            self.assertIn("image", workflow["renderRequest"]["allowedSurfaces"])
            self.assertNotIn("cinema", workflow["renderRequest"]["allowedSurfaces"])
            self.assertEqual(plan["speechMarkupPlan"]["voiceId"], "af_nicole")
            self.assertEqual(plan["speechMarkupPlan"]["speed"], 0.86)
            self.assertTrue(plan["visualPromptPlan"]["image"]["enabled"])
            self.assertEqual(
                plan["visualPromptPlan"]["image"]["providerPromptPolicy"],
                "sanitized_visual_only",
            )
            self.assertIn(
                "no_raw_material_to_external_provider",
                plan["safetyBoundary"]["providerRestrictions"],
            )
            self.assertEqual(llm.interpret_calls, [])
            self.assertEqual(await repository.list_interpretation_runs("user_1"), [])
            self.assertEqual(await repository.list_weekly_reviews("user_1"), [])
            self.assertEqual(await repository.list_practice_sessions("user_1"), [])

        asyncio.run(run())

    def test_plan_ritual_music_surface_is_allowed_when_external_providers_are_enabled(self) -> None:
        async def run() -> None:
            _, service, llm = self._service()
            workflow = await service.plan_ritual(
                {
                    "userId": "user_1",
                    "ritualIntent": "journey_broadcast",
                    "narrativeMode": "hybrid",
                    "windowStart": "2026-04-12T00:00:00Z",
                    "windowEnd": "2026-04-19T23:59:59Z",
                    "requestedSurfaces": {
                        "music": {
                            "enabled": True,
                            "allowExternalGeneration": True,
                            "styleIntent": "dream_integration",
                            "musicDurationSeconds": 15,
                        },
                    },
                    "renderPolicy": {
                        "mode": "render_static",
                        "externalProvidersAllowed": True,
                        "providerAllowlist": ["mock", "chutes"],
                        "maxCost": {"currency": "USD", "amount": 0.05},
                        "allowBetaMusic": True,
                        "musicSteps": 40,
                    },
                }
            )

            plan = workflow["plan"]
            self.assertEqual(plan["music"]["role"], "ambient_bed")
            self.assertEqual(plan["music"]["providerPromptPolicy"], "derived_user_facing_only")
            self.assertEqual(plan["music"]["styleIntent"], "dream_integration")
            self.assertEqual(plan["music"]["musicDurationSeconds"], 15)
            self.assertIn("instrumental", plan["music"]["stylePrompt"])
            self.assertIn("music", workflow["renderRequest"]["allowedSurfaces"])
            self.assertIn(
                "no_raw_material_to_external_provider",
                plan["safetyBoundary"]["providerRestrictions"],
            )
            self.assertEqual(llm.interpret_calls, [])

        asyncio.run(run())

    def test_plan_ritual_can_limit_plan_to_breath_and_music_surfaces(self) -> None:
        async def run() -> None:
            _, service, _ = self._service()
            workflow = await service.plan_ritual(
                {
                    "userId": "user_1",
                    "ritualIntent": "breath_container",
                    "narrativeMode": "breath_only",
                    "windowStart": "2026-04-12T00:00:00Z",
                    "windowEnd": "2026-04-19T23:59:59Z",
                    "requestedSurfaces": {
                        "breath": {"enabled": True, "request": {"pattern": "steadying"}},
                        "music": {
                            "enabled": True,
                            "allowExternalGeneration": True,
                            "styleIntent": "body_settling",
                            "musicDurationSeconds": 15,
                        },
                        "captions": {"enabled": False},
                        "meditation": {"enabled": False},
                        "audio": {"enabled": False},
                        "image": {"enabled": False},
                        "cinema": {"enabled": False},
                    },
                    "renderPolicy": {
                        "mode": "render_static",
                        "externalProvidersAllowed": True,
                        "providerAllowlist": ["mock", "chutes"],
                        "providerProfile": "chutes_music",
                        "surfaces": ["music"],
                        "maxCost": {"currency": "USD", "amount": 0.05},
                        "allowBetaMusic": True,
                    },
                }
            )

            plan = workflow["plan"]
            self.assertTrue(plan["breath"]["enabled"])
            self.assertFalse(plan["meditation"]["enabled"])
            self.assertEqual(plan["music"]["styleIntent"], "body_settling")
            self.assertEqual(
                workflow["renderRequest"]["allowedSurfaces"],
                ["text", "breath", "music"],
            )

        asyncio.run(run())

    def test_plan_ritual_cinema_surface_builds_sanitized_storyboard_when_gated(self) -> None:
        async def run() -> None:
            repository, service, llm = self._service()
            await service.store_material(
                {
                    "userId": "user_1",
                    "materialType": "reflection",
                    "text": "PRIVATE RAW DREAM TEXT: a red door opened under the stairs.",
                    "summary": "A threshold image kept returning.",
                    "materialDate": "2026-04-15T08:00:00Z",
                }
            )

            workflow = await service.plan_ritual(
                {
                    "userId": "user_1",
                    "ritualIntent": "journey_broadcast",
                    "narrativeMode": "hybrid",
                    "windowStart": "2026-04-12T00:00:00Z",
                    "windowEnd": "2026-04-19T23:59:59Z",
                    "requestedSurfaces": {
                        "audio": {"enabled": True},
                        "captions": {"enabled": True},
                        "image": {"enabled": True, "allowExternalGeneration": True},
                        "cinema": {"enabled": True, "maxDurationSeconds": 8},
                    },
                    "renderPolicy": {
                        "mode": "render_static",
                        "externalProvidersAllowed": True,
                        "videoAllowed": True,
                        "providerAllowlist": ["mock", "chutes"],
                        "maxCost": {"currency": "USD", "amount": 0.05},
                    },
                }
            )

            plan = workflow["plan"]
            cinema = plan["visualPromptPlan"]["cinema"]
            self.assertTrue(cinema["enabled"])
            self.assertEqual(cinema["providerPromptPolicy"], "sanitized_visual_only")
            self.assertEqual(cinema["maxDurationSeconds"], 8)
            self.assertTrue(cinema["storyboard"])
            prompt = cinema["storyboard"][0]["prompt"]
            self.assertNotIn("PRIVATE RAW DREAM TEXT", prompt)
            self.assertIn("cinema", workflow["renderRequest"]["allowedSurfaces"])
            self.assertIn(
                "no_raw_material_to_external_provider",
                plan["safetyBoundary"]["providerRestrictions"],
            )
            self.assertEqual(llm.interpret_calls, [])
            self.assertEqual(await repository.list_interpretation_runs("user_1"), [])

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
            self.assertIn("cinema_disabled_without_external_providers", workflow["warnings"])
            self.assertIn("cinema_disabled_without_video_allowed", workflow["warnings"])

        asyncio.run(run())

    def test_plan_ritual_normalizes_boolean_surface_aliases_without_writes(self) -> None:
        async def run() -> None:
            repository, service, llm = self._service()
            workflow = await service.plan_ritual(
                {
                    "userId": "user_1",
                    "ritualIntent": "alive_today",
                    "windowStart": "2026-04-12T00:00:00Z",
                    "windowEnd": "2026-04-19T23:59:59Z",
                    "requestedSurfaces": {
                        "breath": True,
                        "meditation": True,
                        "captions": True,
                        "music": True,
                        "video": True,
                    },
                    "renderPolicy": {"videoAllowed": False},
                }
            )

            plan = workflow["plan"]
            self.assertEqual(plan["schemaVersion"], "circulatio.presentation.plan.v1")
            self.assertTrue(plan["breath"]["enabled"])
            self.assertTrue(plan["meditation"]["enabled"])
            self.assertFalse(plan["visualPromptPlan"]["cinema"]["enabled"])
            self.assertIn("captions", workflow["renderRequest"]["allowedSurfaces"])
            self.assertIn("breath", workflow["renderRequest"]["allowedSurfaces"])
            self.assertIn("meditation", workflow["renderRequest"]["allowedSurfaces"])
            self.assertNotIn("music", workflow["renderRequest"]["allowedSurfaces"])
            self.assertIn("music", plan["safetyBoundary"]["blockedSurfaces"])
            self.assertNotIn("music", plan)
            self.assertIn("requested_surface_boolean_normalized:breath", workflow["warnings"])
            self.assertIn("requested_surface_boolean_normalized:meditation", workflow["warnings"])
            self.assertIn("requested_surface_boolean_normalized:captions", workflow["warnings"])
            self.assertIn("requested_surface_boolean_normalized:music", workflow["warnings"])
            self.assertIn("requested_surface_alias_normalized:video->cinema", workflow["warnings"])
            self.assertIn("requested_surface_boolean_normalized:cinema", workflow["warnings"])
            self.assertIn("music_disabled_without_external_providers", workflow["warnings"])
            self.assertIn("cinema_disabled_without_video_allowed", workflow["warnings"])
            self.assertEqual(len(llm.alive_today_calls), 1)
            self.assertEqual(await repository.list_interpretation_runs("user_1"), [])

        asyncio.run(run())

    def test_plan_ritual_invalid_nested_request_shape_is_warning_only(self) -> None:
        async def run() -> None:
            _, service, _ = self._service()
            workflow = await service.plan_ritual(
                {
                    "userId": "user_1",
                    "ritualIntent": "alive_today",
                    "windowStart": "2026-04-12T00:00:00Z",
                    "windowEnd": "2026-04-19T23:59:59Z",
                    "requestedSurfaces": {"breath": {"enabled": True, "request": "box"}},
                }
            )

            self.assertEqual(workflow["plan"]["breath"]["pattern"], "lengthened_exhale")
            self.assertIn(
                "requested_surface_invalid_request_omitted:breath.request",
                workflow["warnings"],
            )

        asyncio.run(run())

    def test_record_ritual_completion_is_idempotent_and_literal_only(self) -> None:
        async def run() -> None:
            repository, service, llm = self._service()
            first = await service.record_ritual_completion(
                {
                    "userId": "user_1",
                    "artifactId": "artifact_1",
                    "manifestVersion": "hermes_ritual_artifact.v1",
                    "idempotencyKey": "completion_1",
                    "completedAt": "2026-04-19T12:00:00Z",
                    "playbackState": "completed",
                    "planId": "ritual_plan_1",
                    "sourceRefs": [
                        {"sourceType": "surface_result", "recordId": "alive", "role": "primary"}
                    ],
                    "completedSections": ["arrival", "closing", "arrival"],
                    "reflectionText": "I felt more settled after the breath segment.",
                    "clientMetadata": {"transcript": "blocked", "device": "test"},
                }
            )
            replay = await service.record_ritual_completion(
                {
                    "userId": "user_1",
                    "artifactId": "artifact_1",
                    "manifestVersion": "hermes_ritual_artifact.v1",
                    "idempotencyKey": "completion_1",
                    "completedAt": "2026-04-19T12:00:00Z",
                    "playbackState": "completed",
                    "planId": "ritual_plan_1",
                    "sourceRefs": [
                        {"sourceType": "surface_result", "recordId": "alive", "role": "primary"}
                    ],
                    "completedSections": ["arrival", "closing", "arrival"],
                    "reflectionText": "I felt more settled after the breath segment.",
                    "clientMetadata": {"transcript": "blocked", "device": "test"},
                }
            )

            self.assertFalse(first["replayed"])
            self.assertTrue(replay["replayed"])
            self.assertEqual(first["event"]["id"], replay["event"]["id"])
            self.assertEqual(first["event"]["completedSections"], ["arrival", "closing"])
            self.assertEqual(first["event"]["metadata"], {"device": "test"})
            self.assertEqual(len(await repository.list_materials("user_1")), 1)
            self.assertEqual(await repository.list_interpretation_runs("user_1"), [])
            self.assertEqual(llm.interpret_calls, [])

        asyncio.run(run())

    def test_record_ritual_completion_stores_body_state_idempotently(self) -> None:
        async def run() -> None:
            repository, service, _ = self._service()
            payload = {
                "userId": "user_1",
                "artifactId": "artifact_1",
                "manifestVersion": "hermes_ritual_artifact.v1",
                "idempotencyKey": "completion_body_1",
                "completedAt": "2026-04-19T12:00:00Z",
                "playbackState": "completed",
                "bodyState": {
                    "sensation": "tightness",
                    "bodyRegion": "chest",
                    "activation": "high",
                    "tone": "charged",
                    "temporalContext": "post_ritual_completion",
                    "noteText": "My chest stayed tight after the closing breath.",
                    "privacyClass": "private",
                },
            }

            first = await service.record_ritual_completion(payload)
            replay = await service.record_ritual_completion(payload)
            body_states = await repository.list_body_states("user_1")

            self.assertFalse(first["replayed"])
            self.assertTrue(replay["replayed"])
            self.assertEqual(first["event"]["bodyStateId"], body_states[0]["id"])
            self.assertEqual(replay["event"]["bodyStateId"], first["event"]["bodyStateId"])
            self.assertEqual(len(body_states), 1)
            self.assertEqual(body_states[0]["bodyRegion"], "chest")
            self.assertEqual(body_states[0]["activation"], "high")
            self.assertEqual(len(await repository.list_materials("user_1")), 1)
            self.assertEqual(await repository.list_interpretation_runs("user_1"), [])

        asyncio.run(run())

    def test_record_ritual_completion_rejects_body_state_without_sensation(self) -> None:
        async def run() -> None:
            _, service, _ = self._service()
            with self.assertRaises(Exception):
                await service.record_ritual_completion(
                    {
                        "userId": "user_1",
                        "artifactId": "artifact_1",
                        "manifestVersion": "hermes_ritual_artifact.v1",
                        "idempotencyKey": "completion_body_invalid_1",
                        "completedAt": "2026-04-19T12:00:00Z",
                        "playbackState": "completed",
                        "bodyState": {"bodyRegion": "chest"},
                    }
                )

        asyncio.run(run())

    def test_record_ritual_completion_rejects_idempotency_conflict(self) -> None:
        async def run() -> None:
            _, service, _ = self._service()
            payload = {
                "userId": "user_1",
                "artifactId": "artifact_1",
                "manifestVersion": "hermes_ritual_artifact.v1",
                "idempotencyKey": "completion_1",
                "completedAt": "2026-04-19T12:00:00Z",
                "playbackState": "completed",
            }
            await service.record_ritual_completion(payload)
            with self.assertRaises(Exception):
                await service.record_ritual_completion({**payload, "playbackState": "partial"})

        asyncio.run(run())
