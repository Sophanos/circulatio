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
from circulatio.domain.errors import ConflictError, ValidationError
from circulatio.domain.ids import create_id
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


class CirculatioServiceTests(unittest.TestCase):
    def _service(self) -> tuple[InMemoryCirculatioRepository, CirculatioService, FakeCirculatioLlm]:
        repository = InMemoryCirculatioRepository()
        llm = FakeCirculatioLlm()
        service = self._service_with_llm(repository=repository, llm=llm)
        return repository, service, llm

    def _service_with_llm(
        self,
        *,
        repository: InMemoryCirculatioRepository | None = None,
        llm: object,
    ) -> CirculatioService:
        if repository is None:
            repository = InMemoryCirculatioRepository()
        core = CirculatioCore(repository, llm=llm)
        builder = CirculatioLifeContextBuilder(repository)
        context_adapter = ContextAdapter(
            repository,
            life_os=FakeLifeOs(),
            life_context_builder=builder,
            method_context_builder=CirculatioMethodContextBuilder(repository),
        )
        service = CirculatioService(
            repository,
            core,
            context_adapter=context_adapter,
            method_state_llm=llm,
            trusted_amplification_sources=default_trusted_amplification_sources(),
        )
        return service

    def test_create_material_and_llm_interpretation_persists_run_and_evidence(self) -> None:
        async def run() -> None:
            repository, service, llm = self._service()
            workflow = await service.create_and_interpret_material(
                {
                    "userId": "user_1",
                    "materialType": "reflection",
                    "text": "I walked through a house and found a snake image returning after the conflict.",
                }
            )
            self.assertEqual(workflow["material"]["id"], workflow["interpretation"]["materialId"])
            stored_run = await repository.get_interpretation_run("user_1", workflow["run"]["id"])
            self.assertEqual(stored_run["materialId"], workflow["material"]["id"])
            evidence = await repository.list_evidence_for_run("user_1", workflow["run"]["id"])
            self.assertTrue(evidence)
            self.assertTrue(workflow["pendingProposals"])
            self.assertEqual(len(llm.interpret_calls), 1)

        asyncio.run(run())

    def test_store_material_tools_only_create_material_records(self) -> None:
        async def run() -> None:
            repository, service, _ = self._service()
            stored_types = {
                "dream": await service.store_material(
                    {
                        "userId": "user_1",
                        "materialType": "dream",
                        "text": "A serpent moved through the house.",
                    }
                ),
                "charged_event": await service.store_material(
                    {
                        "userId": "user_1",
                        "materialType": "charged_event",
                        "text": "The meeting with my manager felt electric and unsettling.",
                    }
                ),
                "reflection": await service.store_material(
                    {
                        "userId": "user_1",
                        "materialType": "reflection",
                        "text": "The image stayed with me all day.",
                    }
                ),
                "symbolic_motif": await service.store_material(
                    {
                        "userId": "user_1",
                        "materialType": "symbolic_motif",
                        "text": "Snake, stairs, and water keep repeating.",
                    }
                ),
            }
            materials = await repository.list_materials("user_1")
            runs = await repository.list_interpretation_runs("user_1")
            self.assertEqual({item["materialType"] for item in materials}, set(stored_types))
            self.assertEqual(runs, [])

        asyncio.run(run())

    def test_fallback_interpretations_allocate_fresh_practice_sessions(self) -> None:
        class TimeoutLlm:
            async def interpret_material(self, input_data: dict[str, object]) -> dict[str, object]:
                del input_data
                raise TimeoutError("timed out")

        async def run() -> None:
            repository = InMemoryCirculatioRepository()
            service = self._service_with_llm(repository=repository, llm=TimeoutLlm())
            first = await service.create_and_interpret_material(
                {
                    "userId": "user_1",
                    "materialType": "reflection",
                    "text": "A bear moved through the trees.",
                }
            )
            second = await service.create_and_interpret_material(
                {
                    "userId": "user_1",
                    "materialType": "reflection",
                    "text": "A wolf stood at the edge of the clearing.",
                }
            )
            self.assertNotEqual(first["practiceSession"]["id"], second["practiceSession"]["id"])
            self.assertEqual(first["interpretation"]["llmInterpretationHealth"]["status"], "opened")
            self.assertEqual(
                second["interpretation"]["llmInterpretationHealth"]["status"], "opened"
            )

        asyncio.run(run())

    def test_fallback_interpretation_creates_context_only_clarification(self) -> None:
        class TimeoutLlm:
            async def interpret_material(self, input_data: dict[str, object]) -> dict[str, object]:
                del input_data
                raise TimeoutError("timed out")

        async def run() -> None:
            repository = InMemoryCirculatioRepository()
            service = self._service_with_llm(repository=repository, llm=TimeoutLlm())
            workflow = await service.create_and_interpret_material(
                {
                    "userId": "user_1",
                    "materialType": "reflection",
                    "text": "A bear moved through the trees.",
                }
            )
            self.assertEqual(
                workflow["interpretation"]["clarificationPlan"]["captureTarget"],
                "personal_amplification",
            )
            self.assertEqual(
                workflow["interpretation"]["clarificationIntent"]["expectedTargets"],
                ["personal_amplification"],
            )
            self.assertEqual(
                workflow["interpretation"]["clarificationIntent"]["storagePolicy"],
                "no_storage_without_confirmation",
            )
            self.assertEqual(
                workflow["pendingClarificationPrompts"][0]["captureTarget"],
                "personal_amplification",
            )

        asyncio.run(run())

    def test_interpret_existing_material_reuses_latest_open_run_for_duplicate_bare_request(
        self,
    ) -> None:
        async def run() -> None:
            _, service, llm = self._service()
            dream = await service.store_material(
                {
                    "userId": "user_1",
                    "materialType": "dream",
                    "text": "There was a snake in the house.",
                }
            )
            first = await service.interpret_existing_material(
                user_id="user_1",
                material_id=dream["id"],
            )
            second = await service.interpret_existing_material(
                user_id="user_1",
                material_id=dream["id"],
            )
            self.assertEqual(len(llm.interpret_calls), 1)
            self.assertEqual(second["run"]["id"], first["run"]["id"])
            self.assertEqual(second["practiceSession"]["id"], first["practiceSession"]["id"])
            self.assertEqual(
                second["interpretation"]["methodGate"]["depthLevel"],
                "personal_amplification_needed",
            )
            self.assertEqual(len(second["pendingProposals"]), len(first["pendingProposals"]))
            self.assertIn("continuity", second)
            self.assertTrue(second["continuity"]["threadDigests"])

        asyncio.run(run())

    def test_interpret_existing_material_uses_canonical_continuity_bundle(self) -> None:
        async def run() -> None:
            repository, service, llm = self._service()
            material = await service.store_material(
                {
                    "userId": "user_1",
                    "materialType": "reflection",
                    "text": "A snake image returned when I thought about the threshold at work.",
                    "materialDate": "2026-04-18T08:00:00Z",
                }
            )
            journey = await service.create_journey(
                {
                    "userId": "user_1",
                    "label": "Threshold return",
                    "currentQuestion": "What is trying to come through carefully?",
                    "relatedMaterialIds": [material["id"]],
                }
            )
            await service.capture_reality_anchors(
                {
                    "userId": "user_1",
                    "summary": "Outer life can hold a paced reading.",
                    "anchorSummary": "Containment is present if the pace stays gentle.",
                    "groundingRecommendation": "pace_gently",
                }
            )

            workflow = await service.interpret_existing_material(
                user_id="user_1",
                material_id=material["id"],
                explicit_question="What does this seem connected to?",
            )

            self.assertEqual(len(llm.interpret_calls), 1)
            interpret_input = llm.interpret_calls[0]
            self.assertTrue(interpret_input["threadDigests"])
            self.assertTrue(
                any(
                    journey["id"] in item["journeyIds"] for item in interpret_input["threadDigests"]
                )
            )
            self.assertIn("witnessState", interpret_input["methodContextSnapshot"])
            self.assertIn("continuity", workflow)
            self.assertTrue(workflow["continuity"]["threadDigests"])
            self.assertIn("witnessState", workflow["continuity"]["methodContextSnapshot"])
            stored_run = await repository.get_interpretation_run("user_1", workflow["run"]["id"])
            snapshot = await repository.get_context_snapshot(
                "user_1", stored_run["inputSnapshotId"]
            )
            self.assertIn("witnessState", snapshot["methodContextSnapshot"])

        asyncio.run(run())

    def test_process_method_state_response_treats_fallback_clarification_as_context_only(
        self,
    ) -> None:
        class TimeoutLlm:
            async def interpret_material(self, input_data: dict[str, object]) -> dict[str, object]:
                del input_data
                raise TimeoutError("timed out")

            async def route_method_state_response(
                self, input_data: dict[str, object]
            ) -> dict[str, object]:
                del input_data
                raise AssertionError(
                    "Fallback clarification answers should not hit method-state routing."
                )

        async def run() -> None:
            repository = InMemoryCirculatioRepository()
            service = self._service_with_llm(repository=repository, llm=TimeoutLlm())
            workflow = await service.create_and_interpret_material(
                {
                    "userId": "user_1",
                    "materialType": "reflection",
                    "text": "A bear moved through the trees.",
                }
            )
            prompt = await repository.update_clarification_prompt(
                "user_1",
                workflow["pendingClarificationPrompts"][0]["id"],
                {
                    "captureTarget": "personal_amplification",
                    "updatedAt": "2026-04-22T10:00:00Z",
                },
            )
            result = await service.process_method_state_response(
                {
                    "userId": "user_1",
                    "idempotencyKey": "fallback_clarification_answer_1",
                    "source": "clarifying_answer",
                    "responseText": "The image of the bear still feels the most alive.",
                    "anchorRefs": {
                        "promptId": prompt["id"],
                        "materialId": workflow["material"]["id"],
                        "runId": workflow["run"]["id"],
                        "clarificationRefKey": workflow["interpretation"]["clarificationIntent"][
                            "refKey"
                        ],
                    },
                    "expectedTargets": ["body_state", "personal_amplification"],
                }
            )
            updated_prompt = await repository.get_clarification_prompt("user_1", prompt["id"])
            answers = await repository.list_clarification_answers(
                "user_1",
                prompt_id=prompt["id"],
            )
            amplifications = await repository.list_personal_amplifications(
                "user_1",
                run_id=workflow["run"]["id"],
            )
            self.assertEqual(result["captureRun"]["status"], "no_capture")
            self.assertEqual(result["warnings"], [])
            self.assertEqual(updated_prompt["status"], "answered_unrouted")
            self.assertEqual(updated_prompt["captureTarget"], "answer_only")
            self.assertEqual(len(answers), 1)
            self.assertEqual(answers[0]["captureTarget"], "answer_only")
            self.assertEqual(answers[0]["routingStatus"], "unrouted")
            self.assertEqual(amplifications, [])

        asyncio.run(run())

    def test_interpret_existing_material_does_not_reuse_answered_fallback_run(self) -> None:
        class TimeoutLlm:
            async def interpret_material(self, input_data: dict[str, object]) -> dict[str, object]:
                del input_data
                raise TimeoutError("timed out")

            async def route_method_state_response(
                self, input_data: dict[str, object]
            ) -> dict[str, object]:
                del input_data
                raise AssertionError(
                    "Fallback clarification answers should not hit method-state routing."
                )

        async def run() -> None:
            repository = InMemoryCirculatioRepository()
            service = self._service_with_llm(repository=repository, llm=TimeoutLlm())
            first = await service.create_and_interpret_material(
                {
                    "userId": "user_1",
                    "materialType": "reflection",
                    "text": "A wolf stood at the edge of the clearing.",
                }
            )
            await service.process_method_state_response(
                {
                    "userId": "user_1",
                    "idempotencyKey": "fallback_clarification_answer_2",
                    "source": "clarifying_answer",
                    "responseText": "The wolf at the edge still feels the most alive.",
                    "anchorRefs": {
                        "promptId": first["pendingClarificationPrompts"][0]["id"],
                        "materialId": first["material"]["id"],
                        "runId": first["run"]["id"],
                        "clarificationRefKey": first["interpretation"]["clarificationIntent"][
                            "refKey"
                        ],
                    },
                }
            )
            second = await service.interpret_existing_material(
                user_id="user_1",
                material_id=first["material"]["id"],
            )
            runs = await repository.list_interpretation_runs(
                "user_1",
                material_id=first["material"]["id"],
            )
            self.assertNotEqual(second["run"]["id"], first["run"]["id"])
            self.assertEqual(len(runs), 2)

        asyncio.run(run())

    def test_store_material_with_intake_context_returns_host_only_factual_packet(self) -> None:
        async def run() -> None:
            repository, service, llm = self._service()
            prior_material = await service.store_material(
                {
                    "userId": "user_1",
                    "materialType": "reflection",
                    "text": "The authority thread has been circling all week.",
                    "materialDate": "2026-04-14T09:00:00Z",
                }
            )
            goal = await service.upsert_goal(
                {
                    "userId": "user_1",
                    "label": "Speak more directly",
                    "status": "active",
                    "linkedMaterialIds": [prior_material["id"]],
                }
            )
            await service.store_body_state(
                {
                    "userId": "user_1",
                    "sensation": "tightness",
                    "observedAt": "2026-04-16T09:00:00Z",
                    "bodyRegion": "chest",
                    "activation": "high",
                    "linkedGoalIds": [goal["id"]],
                    "linkedMaterialIds": [prior_material["id"]],
                }
            )
            await service.create_journey(
                {
                    "userId": "user_1",
                    "label": "Authority thread",
                    "currentQuestion": "How do I stay in contact without collapsing?",
                    "relatedMaterialIds": [prior_material["id"]],
                    "relatedGoalIds": [goal["id"]],
                }
            )
            await service.capture_reality_anchors(
                {
                    "userId": "user_1",
                    "summary": "Outer life is steady enough for careful reflection.",
                    "anchorSummary": "Work and relationships are holding.",
                    "workDailyLifeContinuity": "stable",
                    "sleepBodyRegulation": "stable",
                    "relationshipContact": "available",
                    "reflectiveCapacity": "steady",
                    "groundingRecommendation": "pace_gently",
                }
            )

            workflow = await service.store_material_with_intake_context(
                {
                    "userId": "user_1",
                    "materialType": "dream",
                    "text": "A bear waited at the doorway.",
                    "materialDate": "2026-04-18T10:00:00Z",
                }
            )

            packet = workflow["intakeContext"]
            self.assertEqual(workflow["material"]["id"], packet["materialId"])
            self.assertEqual(packet["visibility"], "host_only")
            self.assertEqual(packet["source"], "circulatio-post-store")
            self.assertTrue(packet["hostGuidance"]["holdFirst"])
            self.assertFalse(packet["hostGuidance"]["allowAutoInterpretation"])
            self.assertLessEqual(packet["hostGuidance"]["maxQuestions"], 1)
            self.assertEqual(packet["windowStart"], "2026-04-11T10:00:00Z")
            self.assertEqual(packet["windowEnd"], "2026-04-18T10:00:00Z")
            criteria = {
                criterion for item in packet["items"] for criterion in item.get("criteria", [])
            }
            self.assertGreaterEqual(packet["sourceCounts"]["threadDigestCount"], 1)
            self.assertEqual(packet["sourceCounts"]["intakeItemCount"], len(packet["items"]))
            self.assertIn("thread_digest", criteria)
            self.assertIn("method_context_recent_body_state", criteria)
            self.assertIn("method_context_active_journey", criteria)
            self.assertIn("method_context_reality_anchor", criteria)
            self.assertIn("dashboard_recent_material", criteria)
            self.assertFalse(any(item.get("kind") == "coach_loop" for item in packet["items"]))
            self.assertIn("continuity", workflow)
            self.assertTrue(workflow["continuity"]["threadDigests"])
            self.assertEqual(
                workflow["continuity"]["methodContextSnapshot"]["windowEnd"],
                packet["windowEnd"],
            )
            runs = await repository.list_interpretation_runs("user_1")
            reviews = await repository.list_weekly_reviews("user_1")
            practices = await repository.list_practice_sessions("user_1")
            self.assertEqual(runs, [])
            self.assertEqual(reviews, [])
            self.assertEqual(practices, [])
            self.assertEqual(llm.interpret_calls, [])
            self.assertEqual(workflow["material"]["linkedContextSnapshotIds"], [])
            self.assertEqual(workflow["material"]["linkedPracticeSessionIds"], [])

        asyncio.run(run())

    def test_store_material_with_intake_context_handles_empty_context_without_interpretation(
        self,
    ) -> None:
        async def run() -> None:
            repository, service, _ = self._service()
            workflow = await service.store_material_with_intake_context(
                {
                    "userId": "user_1",
                    "materialType": "reflection",
                    "text": "A quiet note.",
                    "materialDate": "2026-04-18T10:00:00Z",
                }
            )

            packet = workflow["intakeContext"]
            self.assertEqual(packet["status"], "complete")
            self.assertEqual(packet["items"], [])
            self.assertTrue(packet["hostGuidance"]["holdFirst"])
            self.assertFalse(packet["hostGuidance"]["allowAutoInterpretation"])
            self.assertEqual(packet["hostGuidance"]["mentionRecommendation"], "acknowledge_only")
            self.assertEqual(packet["hostGuidance"]["followupQuestionStyle"], "none")
            runs = await repository.list_interpretation_runs("user_1")
            self.assertEqual(runs, [])

        asyncio.run(run())

    def test_store_material_with_intake_context_returns_partial_packet_when_projection_fails(
        self,
    ) -> None:
        class FaultyProjectionRepository(InMemoryCirculatioRepository):
            async def build_method_context_snapshot_from_records(
                self,
                user_id: str,
                *,
                window_start: str,
                window_end: str,
                material_id: str | None = None,
            ):
                del user_id, window_start, window_end, material_id
                raise RuntimeError("method context unavailable")

            async def get_dashboard_summary(self, user_id: str):
                del user_id
                raise RuntimeError("dashboard unavailable")

        async def run() -> None:
            repository = FaultyProjectionRepository()
            llm = FakeCirculatioLlm()
            core = CirculatioCore(repository, llm=llm)
            builder = CirculatioLifeContextBuilder(repository)
            context_adapter = ContextAdapter(
                repository,
                life_os=FakeLifeOs(),
                life_context_builder=builder,
                method_context_builder=CirculatioMethodContextBuilder(repository),
            )
            service = CirculatioService(
                repository,
                core,
                context_adapter=context_adapter,
                method_state_llm=llm,
                trusted_amplification_sources=default_trusted_amplification_sources(),
            )

            workflow = await service.store_material_with_intake_context(
                {
                    "userId": "user_1",
                    "materialType": "reflection",
                    "text": "Something happened, but I only want it held.",
                }
            )

            packet = workflow["intakeContext"]
            self.assertEqual(packet["status"], "partial")
            self.assertIn("method_context_unavailable", packet["warnings"])
            self.assertIn("dashboard_summary_unavailable", packet["warnings"])
            self.assertIn("intake_context_partial", packet["warnings"])
            self.assertEqual(workflow["material"]["id"], packet["materialId"])
            materials = await repository.list_materials("user_1")
            self.assertEqual(len(materials), 1)

        asyncio.run(run())

    def test_store_material_with_intake_context_falls_back_after_invalid_material_date(
        self,
    ) -> None:
        async def run() -> None:
            repository, service, llm = self._service()
            workflow = await service.store_material_with_intake_context(
                {
                    "userId": "user_1",
                    "materialType": "reflection",
                    "text": "Hold this even though the original timestamp is malformed.",
                    "materialDate": "not-a-date",
                }
            )

            packet = workflow["intakeContext"]
            self.assertEqual(packet["status"], "partial")
            self.assertIn("intake_window_fallback", packet["warnings"])
            self.assertIn("intake_context_partial", packet["warnings"])
            self.assertEqual(workflow["material"]["id"], packet["materialId"])
            self.assertTrue(packet["windowStart"])
            self.assertTrue(packet["windowEnd"])
            self.assertEqual(workflow["material"]["linkedContextSnapshotIds"], [])
            self.assertEqual(workflow["material"]["linkedPracticeSessionIds"], [])
            self.assertEqual(await repository.list_interpretation_runs("user_1"), [])
            self.assertEqual(await repository.list_weekly_reviews("user_1"), [])
            self.assertEqual(await repository.list_practice_sessions("user_1"), [])
            self.assertEqual(llm.interpret_calls, [])

        asyncio.run(run())

    def test_store_body_state_creates_real_body_state_and_optional_soma_note(self) -> None:
        async def run() -> None:
            repository, service, _ = self._service()
            goal = await repository.create_goal(
                {
                    "id": create_id("goal"),
                    "userId": "user_1",
                    "label": "Speak more directly",
                    "status": "active",
                    "valueTags": ["truth"],
                    "linkedMaterialIds": [],
                    "linkedSymbolIds": [],
                    "createdAt": "2026-04-14T08:00:00Z",
                    "updatedAt": "2026-04-14T08:00:00Z",
                }
            )
            stored = await service.store_body_state(
                {
                    "userId": "user_1",
                    "sensation": "tightness",
                    "observedAt": "2026-04-16T09:00:00Z",
                    "bodyRegion": "chest",
                    "activation": "high",
                    "linkedGoalIds": [goal["id"]],
                    "noteText": "My chest locked the moment the email arrived.",
                }
            )
            body_states = await repository.list_body_states("user_1")
            materials = await repository.list_materials("user_1")
            self.assertEqual(len(body_states), 1)
            self.assertEqual(body_states[0]["sensation"], "tightness")
            self.assertEqual(body_states[0]["linkedGoalIds"], [goal["id"]])
            self.assertEqual(len(materials), 1)
            self.assertEqual(materials[0]["materialType"], "reflection")
            self.assertIn("soma", materials[0]["tags"])
            self.assertEqual(stored["bodyState"]["materialId"], stored["noteMaterial"]["id"])

        asyncio.run(run())

    def test_approve_proposal_persists_symbol_and_rejects_duplicate_transition(self) -> None:
        async def run() -> None:
            repository, service, _ = self._service()
            workflow = await service.create_and_interpret_material(
                {
                    "userId": "user_1",
                    "materialType": "reflection",
                    "text": "The snake image came back after the conflict.",
                }
            )
            proposal = next(
                item
                for item in workflow["pendingProposals"]
                if item["action"] == "upsert_personal_symbol"
            )
            await service.approve_proposals(
                user_id="user_1",
                run_id=workflow["run"]["id"],
                proposal_ids=[proposal["id"]],
            )
            with self.assertRaises(ValidationError):
                await service.approve_proposals(
                    user_id="user_1",
                    run_id=workflow["run"]["id"],
                    proposal_ids=[proposal["id"]],
                )
            symbols = await repository.list_symbols("user_1")
            snake = next(item for item in symbols if item["canonicalName"] == "snake")
            self.assertEqual(snake["recurrenceCount"], 1)

        asyncio.run(run())

    def test_reject_hypothesis_creates_suppression(self) -> None:
        async def run() -> None:
            repository, service, _ = self._service()
            workflow = await service.create_and_interpret_material(
                {
                    "userId": "user_1",
                    "materialType": "reflection",
                    "text": "A snake crossed the room and would not leave me alone.",
                }
            )
            rejected = workflow["interpretation"]["hypotheses"][0]
            await service.reject_hypotheses(
                user_id="user_1",
                run_id=workflow["run"]["id"],
                feedback_by_hypothesis_id={
                    rejected["id"]: {"feedback": "rejected", "note": "This feels like day residue."}
                },
            )
            memory = await repository.get_hermes_memory_context("user_1")
            self.assertTrue(
                any(
                    item["normalizedClaimKey"] == rejected["normalizedClaimKey"]
                    for item in memory["suppressedHypotheses"]
                )
            )

        asyncio.run(run())

    def test_interpretation_persists_amplification_prompts(self) -> None:
        async def run() -> None:
            repository, service, _ = self._service()
            workflow = await service.create_and_interpret_material(
                {
                    "userId": "user_1",
                    "materialType": "dream",
                    "text": "A snake moved through the house at dusk.",
                }
            )
            prompts = await repository.list_amplification_prompts(
                "user_1",
                run_id=workflow["run"]["id"],
            )
            self.assertEqual(len(prompts), 1)
            self.assertEqual(prompts[0]["runId"], workflow["run"]["id"])
            self.assertEqual(prompts[0]["status"], "pending")
            self.assertEqual(prompts[0]["canonicalName"], "snake")
            self.assertTrue(prompts[0].get("symbolMentionId"))

        asyncio.run(run())

    def test_answer_amplification_prompt_creates_personal_amplification_and_updates_prompt(
        self,
    ) -> None:
        async def run() -> None:
            repository, service, _ = self._service()
            workflow = await service.create_and_interpret_material(
                {
                    "userId": "user_1",
                    "materialType": "dream",
                    "text": "A snake appeared beside the stairs.",
                }
            )
            prompt = (
                await repository.list_amplification_prompts(
                    "user_1",
                    run_id=workflow["run"]["id"],
                )
            )[0]
            amplification = await service.answer_amplification_prompt(
                {
                    "userId": "user_1",
                    "promptId": prompt["id"],
                    "associationText": "It feels ancient and watchful.",
                    "feelingTone": "uneasy",
                }
            )
            stored_prompt = await repository.get_amplification_prompt("user_1", prompt["id"])
            self.assertEqual(amplification["promptId"], prompt["id"])
            self.assertEqual(amplification["source"], "user_answered_prompt")
            self.assertEqual(stored_prompt["status"], "answered")
            self.assertEqual(stored_prompt["responseAmplificationId"], amplification["id"])

        asyncio.run(run())

    def test_personal_amplification_enters_next_method_context(self) -> None:
        async def run() -> None:
            repository, service, llm = self._service()
            first = await service.create_and_interpret_material(
                {
                    "userId": "user_1",
                    "materialType": "dream",
                    "text": "A snake stood in the doorway.",
                }
            )
            prompt = (
                await repository.list_amplification_prompts(
                    "user_1",
                    run_id=first["run"]["id"],
                )
            )[0]
            await service.answer_amplification_prompt(
                {
                    "userId": "user_1",
                    "promptId": prompt["id"],
                    "associationText": "It feels like a threshold guardian from childhood.",
                    "bodySensations": ["chest tightness"],
                }
            )
            await service.create_and_interpret_material(
                {
                    "userId": "user_1",
                    "materialType": "dream",
                    "text": "The snake returned in the same house.",
                }
            )
            method_context = llm.interpret_calls[-1]["methodContextSnapshot"]
            self.assertTrue(method_context["personalAmplifications"])
            self.assertEqual(
                method_context["personalAmplifications"][0]["canonicalName"],
                "snake",
            )
            self.assertEqual(
                method_context["personalAmplifications"][0]["associationText"],
                "It feels like a threshold guardian from childhood.",
            )

        asyncio.run(run())

    def test_process_method_state_response_answers_amplification_prompt_and_is_idempotent(
        self,
    ) -> None:
        async def run() -> None:
            repository, service, llm = self._service()
            workflow = await service.create_and_interpret_material(
                {
                    "userId": "user_1",
                    "materialType": "dream",
                    "text": "A snake stood in the doorway.",
                }
            )
            prompt = (
                await repository.list_amplification_prompts(
                    "user_1",
                    run_id=workflow["run"]["id"],
                )
            )[0]
            result = await service.process_method_state_response(
                {
                    "userId": "user_1",
                    "idempotencyKey": "method_state_prompt_1",
                    "source": "amplification_answer",
                    "responseText": "It feels ancient and watchful.",
                    "anchorRefs": {
                        "promptId": prompt["id"],
                        "runId": workflow["run"]["id"],
                    },
                    "expectedTargets": ["personal_amplification"],
                }
            )
            replay = await service.process_method_state_response(
                {
                    "userId": "user_1",
                    "idempotencyKey": "method_state_prompt_1",
                    "source": "amplification_answer",
                    "responseText": "It feels ancient and watchful.",
                    "anchorRefs": {
                        "promptId": prompt["id"],
                        "runId": workflow["run"]["id"],
                    },
                    "expectedTargets": ["personal_amplification"],
                }
            )
            amplifications = await repository.list_personal_amplifications(
                "user_1",
                run_id=workflow["run"]["id"],
            )
            self.assertEqual(len(amplifications), 1)
            self.assertEqual(amplifications[0]["associationText"], "It feels ancient and watchful.")
            self.assertEqual(result["appliedEntityRefs"][0]["entityType"], "PersonalAmplification")
            self.assertEqual(replay["captureRun"]["id"], result["captureRun"]["id"])
            self.assertEqual(len(llm.method_state_route_calls), 1)

        asyncio.run(run())

    def test_process_method_state_response_updates_dream_dynamics_and_method_context(self) -> None:
        async def run() -> None:
            repository, service, _ = self._service()
            material = await service.store_material(
                {
                    "userId": "user_1",
                    "materialType": "dream",
                    "text": "I stood at the doorway while the figure moved deeper into the house.",
                    "materialDate": "2026-04-18T08:00:00Z",
                }
            )
            result = await service.process_method_state_response(
                {
                    "userId": "user_1",
                    "idempotencyKey": "method_state_dream_1",
                    "source": "dream_dynamics",
                    "responseText": "I kept watching from the doorway and my jaw locked at the end.",
                    "observedAt": "2026-04-18T09:00:00Z",
                    "anchorRefs": {"materialId": material["id"]},
                    "expectedTargets": ["dream_dynamics", "body_state"],
                }
            )
            updated_material = await repository.get_material("user_1", material["id"])
            state = await service.get_witness_state(
                user_id="user_1",
                window_start="2026-04-12T00:00:00Z",
                window_end="2026-04-19T23:59:59Z",
                material_id=material["id"],
            )
            self.assertEqual(result["captureRun"]["status"], "completed")
            self.assertIn("continuity", result)
            self.assertTrue(result["continuity"]["threadDigests"])
            self.assertTrue(updated_material["dreamStructure"]["methodDynamics"])
            self.assertTrue(state["recentDreamDynamics"])
            self.assertEqual(state["recentDreamDynamics"][0]["materialId"], material["id"])
            body_states = await repository.list_body_states("user_1")
            self.assertEqual(len(body_states), 1)

        asyncio.run(run())

    def test_process_method_state_response_keeps_projection_hypothesis_approval_gated(self) -> None:
        async def run() -> None:
            _, service, _ = self._service()
            material = await service.store_material(
                {
                    "userId": "user_1",
                    "materialType": "reflection",
                    "text": "I keep reacting to him like he already decided against me.",
                }
            )
            result = await service.process_method_state_response(
                {
                    "userId": "user_1",
                    "idempotencyKey": "method_state_projection_1",
                    "source": "freeform_followup",
                    "responseText": "It may be my own old authority pattern landing on him.",
                    "anchorRefs": {"materialId": material["id"]},
                    "expectedTargets": ["projection_hypothesis"],
                }
            )
            self.assertEqual(result["appliedEntityRefs"], [])
            self.assertEqual(len(result["pendingProposals"]), 1)
            self.assertEqual(result["pendingProposals"][0]["entityType"], "ProjectionHypothesis")

        asyncio.run(run())

    def test_process_method_state_response_withholds_projection_hypothesis_when_grounding_first(
        self,
    ) -> None:
        async def run() -> None:
            _, service, _ = self._service()
            await service.capture_reality_anchors(
                {
                    "userId": "user_1",
                    "summary": "The body and daily life both need immediate grounding.",
                    "anchorSummary": "Containment is thin and deeper symbolic work should pause.",
                    "groundingRecommendation": "grounding_first",
                }
            )
            material = await service.store_material(
                {
                    "userId": "user_1",
                    "materialType": "reflection",
                    "text": "I keep reacting to him like he already decided against me.",
                }
            )
            result = await service.process_method_state_response(
                {
                    "userId": "user_1",
                    "idempotencyKey": "method_state_projection_grounding_first_1",
                    "source": "freeform_followup",
                    "responseText": "It may be my own old authority pattern landing on him.",
                    "anchorRefs": {"materialId": material["id"]},
                    "expectedTargets": ["projection_hypothesis"],
                }
            )
            self.assertEqual(result["captureRun"]["status"], "no_capture")
            self.assertEqual(result["pendingProposals"], [])
            self.assertEqual(
                result["withheldCandidates"],
                [
                    {
                        "targetKind": "projection_hypothesis",
                        "reason": "method_state_policy_grounding_only:projection_hypothesis",
                    }
                ],
            )

        asyncio.run(run())

    def test_process_method_state_response_withholds_threshold_process_when_grounding_only(
        self,
    ) -> None:
        async def run() -> None:
            _, service, _ = self._service()
            await service.capture_reality_anchors(
                {
                    "userId": "user_1",
                    "summary": "Daily life needs grounding before threshold work.",
                    "anchorSummary": "Containment is thin and symbolic depth should pause.",
                    "groundingRecommendation": "grounding_first",
                }
            )
            material = await service.store_material(
                {
                    "userId": "user_1",
                    "materialType": "reflection",
                    "text": "Something old is ending, but I need steadier footing first.",
                }
            )
            result = await service.process_method_state_response(
                {
                    "userId": "user_1",
                    "idempotencyKey": "method_state_threshold_grounding_only_1",
                    "source": "freeform_followup",
                    "responseText": "An older work identity is ending, but I need steadier footing first.",
                    "anchorRefs": {"materialId": material["id"]},
                    "expectedTargets": ["threshold_process"],
                }
            )
            self.assertEqual(result["captureRun"]["status"], "no_capture")
            self.assertEqual(
                result["withheldCandidates"],
                [
                    {
                        "targetKind": "threshold_process",
                        "reason": "method_state_policy_grounding_only:threshold_process",
                    }
                ],
            )

        asyncio.run(run())

    def test_process_method_state_response_allows_body_state_during_grounding_only(
        self,
    ) -> None:
        async def run() -> None:
            repository, service, _ = self._service()
            await service.capture_reality_anchors(
                {
                    "userId": "user_1",
                    "summary": "Daily life needs grounding before symbolic depth.",
                    "anchorSummary": "Containment is thin and the body needs primary attention.",
                    "groundingRecommendation": "grounding_first",
                }
            )
            result = await service.process_method_state_response(
                {
                    "userId": "user_1",
                    "idempotencyKey": "method_state_body_grounding_only_1",
                    "source": "body_note",
                    "responseText": "My chest tightens the moment I think about the transition.",
                    "expectedTargets": ["body_state"],
                }
            )
            body_states = await repository.list_body_states("user_1")
            self.assertEqual(result["captureRun"]["status"], "completed")
            self.assertEqual(result["withheldCandidates"], [])
            self.assertEqual(result["appliedEntityRefs"][0]["entityType"], "BodyState")
            self.assertEqual(len(body_states), 1)

        asyncio.run(run())

    def test_process_method_state_response_updates_practice_preferences(self) -> None:
        async def run() -> None:
            repository, service, _ = self._service()
            workflow = await service.generate_practice_recommendation({"userId": "user_1"})
            result = await service.process_method_state_response(
                {
                    "userId": "user_1",
                    "idempotencyKey": "method_state_practice_preference_1",
                    "source": "practice_feedback",
                    "responseText": "Writing for five minutes works best for me.",
                    "anchorRefs": {"practiceSessionId": workflow["practiceSession"]["id"]},
                    "expectedTargets": ["practice_preference"],
                }
            )
            profile = await repository.get_adaptation_profile("user_1")
            self.assertEqual(result["captureRun"]["status"], "completed")
            entity_types = {item["entityType"] for item in result["appliedEntityRefs"]}
            self.assertIn("AdaptationProfile", entity_types)
            self.assertEqual(
                profile["explicitPreferences"]["practice"]["preferredModalities"],
                ["writing"],
            )
            self.assertEqual(
                profile["explicitPreferences"]["practice"]["maxDurationMinutes"],
                5,
            )

        asyncio.run(run())

    def test_process_method_state_response_writes_reality_anchors_and_threshold_process(
        self,
    ) -> None:
        async def run() -> None:
            repository, service, _ = self._service()
            await service.capture_reality_anchors(
                {
                    "userId": "user_1",
                    "summary": "Daily life is steady enough to hold a threshold carefully.",
                    "anchorSummary": "Outer life has enough continuity for depth work.",
                    "groundingRecommendation": "clear_for_depth",
                }
            )
            material = await service.store_material(
                {
                    "userId": "user_1",
                    "materialType": "reflection",
                    "text": "Work is stable, but something old is ending.",
                }
            )
            result = await service.process_method_state_response(
                {
                    "userId": "user_1",
                    "idempotencyKey": "method_state_threshold_1",
                    "source": "freeform_followup",
                    "responseText": "Work is steady enough, and an older work identity is ending.",
                    "anchorRefs": {"materialId": material["id"]},
                    "expectedTargets": ["reality_anchors", "threshold_process"],
                }
            )
            records = await repository.list_individuation_records(
                "user_1",
                record_types=["reality_anchor_summary", "threshold_process"],
                limit=20,
            )
            record_types = {record["recordType"] for record in records}
            self.assertEqual(result["captureRun"]["status"], "completed")
            self.assertIn("reality_anchor_summary", record_types)
            self.assertIn("threshold_process", record_types)

        asyncio.run(run())

    def test_process_method_state_response_withholds_threshold_process_when_reflective_capacity_is_fragile(
        self,
    ) -> None:
        async def run() -> None:
            repository, service, _ = self._service()
            original_build = repository.build_method_context_snapshot_from_records

            async def fragile_method_context(
                user_id: str,
                *,
                window_start: str,
                window_end: str,
                material_id: str | None = None,
            ) -> dict[str, object]:
                context = await original_build(
                    user_id,
                    window_start=window_start,
                    window_end=window_end,
                    material_id=material_id,
                )
                context["methodState"] = {
                    "grounding": {"recommendation": "clear_for_depth"},
                    "containment": {"status": "steady"},
                    "egoCapacity": {"reflectiveCapacity": "fragile"},
                }
                return context

            repository.build_method_context_snapshot_from_records = fragile_method_context
            material = await service.store_material(
                {
                    "userId": "user_1",
                    "materialType": "reflection",
                    "text": "Work is stable, but something old is ending.",
                }
            )
            result = await service.process_method_state_response(
                {
                    "userId": "user_1",
                    "idempotencyKey": "method_state_threshold_fragile_1",
                    "source": "freeform_followup",
                    "responseText": "Work is steady enough, and an older work identity is ending.",
                    "anchorRefs": {"materialId": material["id"]},
                    "expectedTargets": ["threshold_process"],
                }
            )
            self.assertEqual(result["captureRun"]["status"], "no_capture")
            self.assertEqual(result["appliedEntityRefs"], [])
            self.assertEqual(
                result["withheldCandidates"],
                [
                    {
                        "targetKind": "threshold_process",
                        "reason": "method_state_policy_blocked_move:active_imagination",
                    }
                ],
            )

        asyncio.run(run())

    def test_conscious_attitude_capture_enables_depth_method_context(self) -> None:
        async def run() -> None:
            _, service, llm = self._service()
            await service.capture_conscious_attitude(
                {
                    "userId": "user_1",
                    "windowStart": "2026-04-12T00:00:00Z",
                    "windowEnd": "2026-04-19T23:59:59Z",
                    "stanceSummary": "I am trying to stay composed around authority conflict.",
                    "activeConflicts": ["directness vs safety"],
                    "emotionalTone": "guarded",
                }
            )
            await service.capture_reality_anchors(
                {
                    "userId": "user_1",
                    "summary": "Daily life is stable.",
                    "anchorSummary": "Daily life is stable enough for depth work.",
                    "groundingRecommendation": "clear_for_depth",
                }
            )
            await service.set_consent_preference(
                {
                    "userId": "user_1",
                    "scope": "active_imagination",
                    "status": "allow",
                }
            )
            workflow = await service.create_and_interpret_material(
                {
                    "userId": "user_1",
                    "materialType": "dream",
                    "text": "A snake coiled in the house while I watched.",
                    "materialDate": "2026-04-18T08:00:00Z",
                }
            )
            self.assertEqual(
                workflow["interpretation"]["methodGate"]["depthLevel"],
                "depth_interpretation_allowed",
            )
            self.assertEqual(
                workflow["interpretation"]["practiceRecommendation"]["type"],
                "active_imagination",
            )
            self.assertEqual(
                llm.interpret_calls[-1]["methodContextSnapshot"]["consciousAttitude"][
                    "stanceSummary"
                ],
                "I am trying to stay composed around authority conflict.",
            )

        asyncio.run(run())

    def test_consent_preference_is_projected_into_method_context(self) -> None:
        async def run() -> None:
            _, service, _ = self._service()
            await service.set_consent_preference(
                {
                    "userId": "user_1",
                    "scope": "collective_amplification",
                    "status": "allow",
                    "note": "Only when clearly optional.",
                }
            )
            state = await service.get_witness_state(
                user_id="user_1",
                window_start="2026-04-12T00:00:00Z",
                window_end="2026-04-19T23:59:59Z",
            )
            self.assertEqual(state["consentPreferences"][0]["scope"], "collective_amplification")
            self.assertEqual(state["consentPreferences"][0]["status"], "allow")

        asyncio.run(run())

    def test_get_witness_state_returns_distinct_witness_behavior_contract(self) -> None:
        async def run() -> None:
            _, service, _ = self._service()
            await service.capture_reality_anchors(
                {
                    "userId": "user_1",
                    "summary": "Containment is thin and ordinary contact needs to lead.",
                    "anchorSummary": "Grounding needs to come before symbolic deepening.",
                    "groundingRecommendation": "grounding_first",
                    "relationshipContact": "thin",
                    "reflectiveCapacity": "fragile",
                }
            )
            await service.set_adaptation_preferences(
                user_id="user_1",
                scope="interpretation",
                preferences={"modalityBias": "body"},
            )
            state = await service.get_witness_state(
                user_id="user_1",
                window_start="2026-04-12T00:00:00Z",
                window_end="2026-04-19T23:59:59Z",
            )
            witness_state = state["witnessState"]
            self.assertEqual(witness_state["stance"], "grounding_first")
            self.assertEqual(witness_state["startingMove"], "grounding")
            self.assertIn("body_first", witness_state["preferredQuestionStyles"])
            self.assertIn("body_state", witness_state["preferredClarificationTargets"])
            self.assertIn("active_imagination", witness_state["blockedMoves"])

        asyncio.run(run())

    def test_active_imagination_is_downgraded_when_method_gate_blocks_it(self) -> None:
        async def run() -> None:
            _, service, llm = self._service()
            original = llm.interpret_material

            async def blocked_active_imagination(
                input_data: dict[str, object],
            ) -> dict[str, object]:
                result = await original(input_data)
                result["practiceRecommendation"]["type"] = "active_imagination"
                result["practiceRecommendation"]["requiresConsent"] = True
                result["methodGate"]["blockedMoves"] = [
                    *result["methodGate"].get("blockedMoves", []),
                    "active_imagination",
                ]
                result["depthReadiness"]["allowedMoves"]["active_imagination"] = "withhold"
                return result

            llm.interpret_material = blocked_active_imagination
            workflow = await service.create_and_interpret_material(
                {
                    "userId": "user_1",
                    "materialType": "dream",
                    "text": "A snake waited behind the locked door.",
                }
            )
            self.assertEqual(
                workflow["interpretation"]["practiceRecommendation"]["type"],
                "journaling",
            )

        asyncio.run(run())

    def test_generate_practice_recommendation_persists_session(self) -> None:
        async def run() -> None:
            repository, service, llm = self._service()
            await service.capture_conscious_attitude(
                {
                    "userId": "user_1",
                    "windowStart": "2026-04-12T00:00:00Z",
                    "windowEnd": "2026-04-19T23:59:59Z",
                    "stanceSummary": "I can stay with the image a little longer.",
                }
            )
            await service.set_consent_preference(
                {"userId": "user_1", "scope": "active_imagination", "status": "allow"}
            )
            workflow = await service.generate_practice_recommendation({"userId": "user_1"})
            self.assertIn("practiceSession", workflow)
            self.assertEqual(workflow["practiceSession"]["status"], "recommended")
            self.assertEqual(len(llm.practice_calls), 1)
            profile = await repository.get_adaptation_profile("user_1")
            self.assertEqual(profile["sampleCounts"]["practice_recommended"], 1)
            modality = workflow["practiceRecommendation"]["modality"]
            self.assertEqual(
                profile["learnedSignals"]["practiceStats"]["byModality"][modality]["recommended"],
                1,
            )
            self.assertEqual(
                profile["learnedSignals"]["practiceStats"]["byTemplateId"]["llm-practice"][
                    "recommended"
                ],
                1,
            )

        asyncio.run(run())

    def test_generate_practice_recommendation_uses_goal_tension_and_practice_loop(self) -> None:
        async def run() -> None:
            repository, service, _ = self._service()
            first_goal = await service.upsert_goal(
                {"userId": "user_1", "label": "Speak directly", "status": "active"}
            )
            second_goal = await service.upsert_goal(
                {"userId": "user_1", "label": "Keep the peace", "status": "active"}
            )
            await service.upsert_goal_tension(
                {
                    "userId": "user_1",
                    "goalIds": [first_goal["id"], second_goal["id"]],
                    "tensionSummary": "Directness and safety are both live.",
                    "polarityLabels": ["directness", "safety"],
                    "status": "active",
                }
            )
            await repository.create_practice_session(
                {
                    "id": "practice_history_1",
                    "userId": "user_1",
                    "practiceType": "journaling",
                    "reason": "Track the authority pattern.",
                    "instructions": ["Write for five minutes."],
                    "durationMinutes": 8,
                    "contraindicationsChecked": ["none"],
                    "requiresConsent": False,
                    "status": "completed",
                    "activationBefore": "low",
                    "activationAfter": "high",
                    "createdAt": "2026-04-18T09:00:00Z",
                    "updatedAt": "2026-04-18T09:05:00Z",
                }
            )
            workflow = await service.generate_practice_recommendation({"userId": "user_1"})
            practice = workflow["practiceRecommendation"]
            self.assertEqual(practice["durationMinutes"], 6)
            self.assertIn(
                "Hold directness and safety together before choosing a side.",
                practice["instructions"],
            )
            self.assertIn("goal_tension_frame_added", practice["adaptationNotes"])
            self.assertIn("duration_shortened_for_low_intensity", practice["adaptationNotes"])

        asyncio.run(run())

    def test_practice_accept_and_skip_update_status_and_adaptation(self) -> None:
        async def run() -> None:
            repository, service, _ = self._service()
            first = await service.generate_practice_recommendation({"userId": "user_1"})
            accepted = await service.respond_practice_recommendation(
                {
                    "userId": "user_1",
                    "practiceSessionId": first["practiceSession"]["id"],
                    "action": "accepted",
                    "activationBefore": "high",
                }
            )
            second = await service.generate_practice_recommendation({"userId": "user_1"})
            skipped = await service.respond_practice_recommendation(
                {
                    "userId": "user_1",
                    "practiceSessionId": second["practiceSession"]["id"],
                    "action": "skipped",
                    "note": "Not today.",
                }
            )
            profile = await repository.get_adaptation_profile("user_1")
            self.assertEqual(accepted["practiceSession"]["status"], "accepted")
            self.assertEqual(skipped["practiceSession"]["status"], "skipped")
            self.assertIn("continuity", accepted)
            self.assertIn("continuity", skipped)
            self.assertEqual(profile["sampleCounts"]["practice_accepted"], 1)
            self.assertEqual(profile["sampleCounts"]["practice_skipped"], 1)

        asyncio.run(run())

    def test_practice_outcome_completion_records_integration_once(self) -> None:
        async def run() -> None:
            repository, service, _ = self._service()
            workflow = await service.generate_practice_recommendation({"userId": "user_1"})
            practice_id = workflow["practiceSession"]["id"]
            completed = await service.record_practice_outcome(
                user_id="user_1",
                practice_session_id=practice_id,
                material_id=None,
                outcome={
                    "practiceType": "journaling",
                    "outcome": "The image softened after writing.",
                    "activationBefore": "high",
                    "activationAfter": "moderate",
                },
            )
            again = await service.record_practice_outcome(
                user_id="user_1",
                practice_session_id=practice_id,
                material_id=None,
                outcome={
                    "practiceType": "journaling",
                    "outcome": "The image softened after writing.",
                    "activationBefore": "high",
                    "activationAfter": "moderate",
                },
            )
            integrations = await repository.list_integration_records("user_1")
            practice_integrations = [
                item for item in integrations if item["action"] == "practice_outcome"
            ]
            self.assertEqual(completed["practiceSession"]["status"], "completed")
            self.assertEqual(completed["practiceSession"]["id"], again["practiceSession"]["id"])
            self.assertTrue(completed["continuity"]["threadDigests"])
            self.assertEqual(len(practice_integrations), 1)

        asyncio.run(run())

    def test_active_imagination_practice_falls_back_when_consent_revoked(self) -> None:
        async def run() -> None:
            _, service, llm = self._service()
            original = llm.generate_practice

            async def forced_active_imagination(input_data: dict[str, object]) -> dict[str, object]:
                result = await original(input_data)
                result["practiceRecommendation"]["type"] = "active_imagination"
                result["practiceRecommendation"]["requiresConsent"] = True
                result["practiceRecommendation"]["modality"] = "imaginal"
                result["practiceRecommendation"]["intensity"] = "moderate"
                return result

            llm.generate_practice = forced_active_imagination
            await service.capture_conscious_attitude(
                {
                    "userId": "user_1",
                    "windowStart": "2026-04-12T00:00:00Z",
                    "windowEnd": "2026-04-19T23:59:59Z",
                    "stanceSummary": "I can stay with the image.",
                }
            )
            await service.set_consent_preference(
                {"userId": "user_1", "scope": "active_imagination", "status": "revoked"}
            )
            workflow = await service.generate_practice_recommendation({"userId": "user_1"})
            self.assertEqual(workflow["practiceRecommendation"]["type"], "journaling")
            self.assertIn(
                "active_imagination_blocked_by_consent_fallback_to_journaling",
                workflow["practiceRecommendation"]["adaptationNotes"],
            )

        asyncio.run(run())

    def test_practice_adaptation_hints_mature_after_threshold(self) -> None:
        async def run() -> None:
            repository, service, _ = self._service()
            for _ in range(10):
                workflow = await service.generate_practice_recommendation({"userId": "user_1"})
                await service.respond_practice_recommendation(
                    {
                        "userId": "user_1",
                        "practiceSessionId": workflow["practiceSession"]["id"],
                        "action": "accepted",
                    }
                )
            profile = await repository.get_adaptation_profile("user_1")
            hints = service._adaptation_engine.derive_practice_hints(profile=profile)
            self.assertEqual(hints["maturity"], "mature")

        asyncio.run(run())

    def test_interpretation_feedback_persists_locale_and_stays_separate_from_hypothesis_feedback(
        self,
    ) -> None:
        async def run() -> None:
            repository, service, _ = self._service()
            workflow = await service.create_and_interpret_material(
                {
                    "userId": "user_1",
                    "materialType": "reflection",
                    "text": "The same image kept circling after the meeting.",
                }
            )
            feedback = await service.record_interpretation_feedback(
                "user_1",
                workflow["run"]["id"],
                "too_much",
                note="Zu viel auf einmal.",
                locale="de-DE",
            )
            stored = await repository.list_interaction_feedback("user_1", domain="interpretation")
            memory = await repository.build_hermes_memory_context_from_records("user_1")
            self.assertEqual(feedback["locale"], "de-DE")
            self.assertEqual(stored[0]["note"], "Zu viel auf einmal.")
            self.assertEqual(stored[0]["feedback"], "too_much")
            self.assertEqual(memory["recentInterpretationFeedback"], [])

        asyncio.run(run())

    def test_practice_feedback_persists_locale_and_note_verbatim(self) -> None:
        async def run() -> None:
            repository, service, _ = self._service()
            workflow = await service.generate_practice_recommendation({"userId": "user_1"})
            practice_id = workflow["practiceSession"]["id"]
            feedback = await service.record_practice_feedback(
                "user_1",
                practice_id,
                "too_long",
                note="Demasiado largo para hoy.",
                locale="es-ES",
            )
            stored = await repository.list_interaction_feedback("user_1", domain="practice")
            self.assertEqual(feedback["locale"], "es-ES")
            self.assertEqual(stored[0]["note"], "Demasiado largo para hoy.")
            self.assertEqual(stored[0]["targetId"], practice_id)

        asyncio.run(run())

    def test_invalid_adaptation_preferences_are_rejected_by_scope(self) -> None:
        async def run() -> None:
            _, service, _ = self._service()
            with self.assertRaises(ValidationError):
                await service.set_adaptation_preferences(
                    user_id="user_1",
                    scope="practice",
                    preferences={"maxDurationMinutes": 0},
                )
            with self.assertRaises(ValidationError):
                await service.set_adaptation_preferences(
                    user_id="user_1",
                    scope="communication",
                    preferences={"tone": "blunt"},
                )

        asyncio.run(run())

    def test_explicit_preferences_override_learned_policy_without_mutation(self) -> None:
        async def run() -> None:
            repository, service, _ = self._service()
            await service.set_adaptation_preferences(
                user_id="user_1",
                scope="communication",
                preferences={"tone": "gentle", "questioningStyle": "reflective"},
            )
            await service.apply_learned_policy_update(
                user_id="user_1",
                scope="communication",
                policy={"tone": "direct", "symbolicDensity": "dense"},
            )
            profile = await repository.get_adaptation_profile("user_1")
            hints = service._adaptation_engine.derive_communication_hints(profile=profile)
            self.assertEqual(profile["explicitPreferences"]["communication"]["tone"], "gentle")
            self.assertEqual(profile["learnedSignals"]["communicationPolicy"]["tone"], "direct")
            self.assertEqual(hints["tone"], "gentle")
            self.assertEqual(hints["symbolicDensity"], "dense")

        asyncio.run(run())

    def test_explicit_practice_preferences_override_learned_policy_at_runtime(self) -> None:
        async def run() -> None:
            _, service, _ = self._service()
            await service.set_adaptation_preferences(
                user_id="user_1",
                scope="practice",
                preferences={"maxDurationMinutes": 5},
            )
            await service.apply_learned_policy_update(
                user_id="user_1",
                scope="practice",
                policy={"maxDurationMinutes": 12},
            )
            workflow = await service.generate_practice_recommendation({"userId": "user_1"})
            self.assertEqual(workflow["practiceRecommendation"]["durationMinutes"], 5)

        asyncio.run(run())

    def test_dream_series_suggestion_becomes_pending_proposal_and_can_be_approved(self) -> None:
        async def run() -> None:
            repository, service, _ = self._service()
            await repository.create_dream_series(
                {
                    "id": "series_house_snake",
                    "userId": "user_1",
                    "label": "House / snake sequence",
                    "status": "active",
                    "seedMaterialId": "seed_material",
                    "materialIds": ["seed_material"],
                    "symbolIds": [],
                    "motifKeys": ["containment"],
                    "settingKeys": ["house"],
                    "figureKeys": [],
                    "confidence": "medium",
                    "evidenceIds": ["evidence_seed"],
                    "createdAt": "2026-04-10T08:00:00Z",
                    "updatedAt": "2026-04-10T08:00:00Z",
                    "lastSeen": "2026-04-10T08:00:00Z",
                }
            )
            workflow = await service.create_and_interpret_material(
                {
                    "userId": "user_1",
                    "materialType": "dream",
                    "text": "A snake returned in the house cellar.",
                }
            )
            link_proposal = next(
                proposal
                for proposal in workflow["pendingProposals"]
                if proposal["action"] == "link_material_to_dream_series"
            )
            integration = await service.approve_proposals(
                user_id="user_1",
                run_id=workflow["run"]["id"],
                proposal_ids=[link_proposal["id"]],
            )
            memberships = await repository.list_dream_series_memberships(
                "user_1",
                series_id="series_house_snake",
            )
            self.assertEqual(len(memberships), 1)
            self.assertEqual(memberships[0]["materialId"], workflow["material"]["id"])
            self.assertIn(memberships[0]["id"], integration["affectedEntityIds"])

        asyncio.run(run())

    def test_collective_amplification_proposal_requires_consent_and_context(self) -> None:
        async def run() -> None:
            _, service, _ = self._service()
            baseline = await service.create_and_interpret_material(
                {
                    "userId": "user_1",
                    "materialType": "dream",
                    "text": "A snake moved through the house.",
                }
            )
            self.assertFalse(
                any(
                    proposal["action"] == "create_collective_amplification"
                    for proposal in baseline["pendingProposals"]
                )
            )
            await service.capture_conscious_attitude(
                {
                    "userId": "user_1",
                    "windowStart": "2026-04-12T00:00:00Z",
                    "windowEnd": "2026-04-19T23:59:59Z",
                    "stanceSummary": "I am trying to understand what this recurring image asks of me.",
                }
            )
            await service.set_consent_preference(
                {
                    "userId": "user_1",
                    "scope": "collective_amplification",
                    "status": "allow",
                }
            )
            allowed = await service.create_and_interpret_material(
                {
                    "userId": "user_1",
                    "materialType": "dream",
                    "text": "The same snake was waiting in the house.",
                    "userAssociations": [
                        {
                            "surfaceText": "snake",
                            "association": "It feels ancient and initiatory.",
                            "tone": "charged",
                        }
                    ],
                    "options": {"allowCulturalAmplification": True},
                }
            )
            self.assertTrue(
                any(
                    proposal["action"] == "create_collective_amplification"
                    for proposal in allowed["pendingProposals"]
                )
            )

        asyncio.run(run())

    def test_direct_capture_methods_create_phase8_records(self) -> None:
        async def run() -> None:
            repository, service, _ = self._service()
            journey = await service.create_journey(
                {
                    "userId": "user_1",
                    "label": "Threshold thread",
                    "currentQuestion": "What is asking for careful passage?",
                }
            )
            anchors = await service.capture_reality_anchors(
                {
                    "userId": "user_1",
                    "summary": "Outer life feels steady enough for careful depth work.",
                    "anchorSummary": "Work and relationships are holding well enough for reflection.",
                    "workDailyLifeContinuity": "stable",
                    "sleepBodyRegulation": "stable",
                    "relationshipContact": "available",
                    "reflectiveCapacity": "steady",
                    "groundingRecommendation": "clear_for_depth",
                    "relatedGoalIds": ["goal_1"],
                    "relatedJourneyIds": [journey["id"]],
                }
            )
            numinous = await service.record_numinous_encounter(
                {
                    "userId": "user_1",
                    "summary": "A charged place encounter stayed alive all day.",
                    "encounterMedium": "place",
                    "affectTone": "awe",
                    "containmentNeed": "pace_gently",
                    "interpretationConstraint": "Hold the charge without forcing a meaning claim.",
                    "relatedJourneyIds": [journey["id"]],
                }
            )
            aesthetic = await service.record_aesthetic_resonance(
                {
                    "userId": "user_1",
                    "summary": "A painting kept resonating after the session.",
                    "medium": "painting",
                    "objectDescription": "A dark river under a narrow bridge.",
                    "resonanceSummary": "The image felt like a threshold rather than decoration.",
                    "bodySensations": ["chest warmth"],
                    "relatedJourneyIds": [journey["id"]],
                }
            )
            records = await repository.list_individuation_records("user_1", limit=20)
            self.assertEqual(len(records), 3)
            self.assertEqual(anchors["recordType"], "reality_anchor_summary")
            self.assertEqual(anchors["status"], "user_confirmed")
            self.assertEqual(numinous["recordType"], "numinous_encounter")
            self.assertEqual(aesthetic["recordType"], "aesthetic_resonance")
            self.assertEqual(anchors["relatedJourneyIds"], [journey["id"]])
            self.assertEqual(numinous["relatedJourneyIds"], [journey["id"]])
            self.assertEqual(aesthetic["relatedJourneyIds"], [journey["id"]])

        asyncio.run(run())

    def test_direct_upsert_phase8_capture_methods_merge_existing_records(self) -> None:
        async def run() -> None:
            repository, service, _ = self._service()
            first_threshold = await service.upsert_threshold_process(
                {
                    "userId": "user_1",
                    "summary": "A work transition still feels unfinished.",
                    "thresholdName": "Work transition",
                    "phase": "liminal",
                    "whatIsEnding": "The old team role is dissolving.",
                    "notYetBegun": "The next position is not settled.",
                    "groundingStatus": "steady",
                    "invitationReadiness": "ask",
                    "normalizedThresholdKey": "work-transition",
                    "relatedMaterialIds": ["material_1"],
                    "relatedJourneyIds": ["journey_1"],
                }
            )
            second_threshold = await service.upsert_threshold_process(
                {
                    "userId": "user_1",
                    "summary": "The same work transition remains active.",
                    "thresholdName": "Work transition",
                    "phase": "reorientation",
                    "whatIsEnding": "The old team role is dissolving.",
                    "notYetBegun": "A clearer vocation is still emerging.",
                    "groundingStatus": "steady",
                    "invitationReadiness": "ready",
                    "normalizedThresholdKey": "work-transition",
                    "relatedMaterialIds": ["material_2"],
                    "relatedJourneyIds": ["journey_2"],
                }
            )
            first_scene = await service.record_relational_scene(
                {
                    "userId": "user_1",
                    "summary": "The same authority scene keeps repeating.",
                    "sceneSummary": "Authority becomes charged when the user feels small.",
                    "chargedRoles": [{"roleLabel": "authority", "affectTone": "pressure"}],
                    "recurringAffect": ["pressure"],
                    "recurrenceContexts": ["work"],
                    "normalizedSceneKey": "authority-scene",
                    "relatedJourneyIds": ["journey_1"],
                }
            )
            second_scene = await service.record_relational_scene(
                {
                    "userId": "user_1",
                    "summary": "The same authority scene keeps repeating.",
                    "sceneSummary": "Authority becomes charged when the user feels observed.",
                    "chargedRoles": [{"roleLabel": "observer", "affectTone": "shame"}],
                    "recurringAffect": ["shame"],
                    "recurrenceContexts": ["group"],
                    "normalizedSceneKey": "authority-scene",
                    "relatedJourneyIds": ["journey_2"],
                }
            )
            first_correspondence = await service.record_inner_outer_correspondence(
                {
                    "userId": "user_1",
                    "summary": "The snake image crossed from dream into waking life.",
                    "correspondenceSummary": "The same charged image appeared in dream and in a daytime encounter.",
                    "innerRefs": ["material_1"],
                    "outerRefs": ["event_1"],
                    "symbolIds": ["symbol_1"],
                    "userCharge": "explicitly_charged",
                    "caveat": "Hold this lightly without causal certainty.",
                    "normalizedCorrespondenceKey": "snake-crossing",
                    "relatedJourneyIds": ["journey_1"],
                }
            )
            second_correspondence = await service.record_inner_outer_correspondence(
                {
                    "userId": "user_1",
                    "summary": "The snake image crossed from dream into waking life.",
                    "correspondenceSummary": "The image stayed charged across inner and outer scenes.",
                    "innerRefs": ["material_2"],
                    "outerRefs": ["event_2"],
                    "symbolIds": ["symbol_2"],
                    "userCharge": "explicitly_charged",
                    "caveat": "Hold this lightly without causal certainty.",
                    "normalizedCorrespondenceKey": "snake-crossing",
                    "relatedJourneyIds": ["journey_2"],
                }
            )
            thresholds = await repository.list_individuation_records(
                "user_1",
                record_types=["threshold_process"],
                limit=20,
            )
            scenes = await repository.list_individuation_records(
                "user_1",
                record_types=["relational_scene"],
                limit=20,
            )
            correspondences = await repository.list_individuation_records(
                "user_1",
                record_types=["inner_outer_correspondence"],
                limit=20,
            )
            self.assertEqual(first_threshold["id"], second_threshold["id"])
            self.assertEqual(first_scene["id"], second_scene["id"])
            self.assertEqual(first_correspondence["id"], second_correspondence["id"])
            self.assertEqual(len(thresholds), 1)
            self.assertEqual(len(scenes), 1)
            self.assertEqual(len(correspondences), 1)
            self.assertEqual(second_threshold["relatedJourneyIds"], ["journey_1", "journey_2"])
            self.assertEqual(second_scene["relatedJourneyIds"], ["journey_1", "journey_2"])
            self.assertEqual(
                second_correspondence["relatedJourneyIds"],
                ["journey_1", "journey_2"],
            )
            self.assertEqual(
                thresholds[0]["details"]["invitationReadiness"],
                "ready",
            )
            self.assertEqual(len(scenes[0]["details"]["chargedRoles"]), 2)
            self.assertEqual(
                correspondences[0]["details"]["symbolIds"],
                ["symbol_1", "symbol_2"],
            )

        asyncio.run(run())

    def test_living_myth_review_proposal_approval_applies_records_and_updates_decisions(
        self,
    ) -> None:
        async def run() -> None:
            repository, service, _ = self._service()
            await service.create_and_interpret_material(
                {
                    "userId": "user_1",
                    "materialType": "dream",
                    "text": "A work threshold and authority scene returned in the dream.",
                    "materialDate": "2026-04-18T08:00:00Z",
                }
            )
            workflow = await service.generate_living_myth_review({"userId": "user_1"})
            self.assertEqual(
                workflow["review"]["proposalDecisions"][0]["status"],
                "pending",
            )
            proposal_ids = [item["id"] for item in workflow["pendingProposals"]]
            approved = await service.approve_living_myth_review_proposals(
                user_id="user_1",
                review_id=workflow["review"]["id"],
                proposal_ids=proposal_ids,
            )
            thresholds = await repository.list_individuation_records(
                "user_1",
                record_types=["threshold_process"],
                limit=20,
            )
            wellbeing = await repository.list_living_myth_records(
                "user_1",
                record_types=["symbolic_wellbeing_snapshot"],
                limit=20,
            )
            decision_statuses = {
                item["proposalId"]: item["status"] for item in approved["proposalDecisions"]
            }
            self.assertEqual(len(thresholds), 1)
            self.assertEqual(len(wellbeing), 1)
            self.assertTrue(proposal_ids)
            self.assertTrue(all(decision_statuses[item] == "approved" for item in proposal_ids))

        asyncio.run(run())

    def test_threshold_review_proposal_rejection_updates_review_without_applying(self) -> None:
        async def run() -> None:
            repository, service, _ = self._service()
            await service.create_and_interpret_material(
                {
                    "userId": "user_1",
                    "materialType": "reflection",
                    "text": "The same authority scene keeps repeating at work.",
                    "materialDate": "2026-04-18T08:00:00Z",
                }
            )
            workflow = await service.generate_threshold_review({"userId": "user_1"})
            proposal_id = workflow["pendingProposals"][0]["id"]
            rejected = await service.reject_living_myth_review_proposals(
                user_id="user_1",
                review_id=workflow["review"]["id"],
                proposal_ids=[proposal_id],
                reason="This does not feel like the right scene.",
            )
            scenes = await repository.list_individuation_records(
                "user_1",
                record_types=["relational_scene"],
                limit=20,
            )
            self.assertEqual(scenes, [])
            self.assertEqual(rejected["proposalDecisions"][0]["status"], "rejected")
            self.assertEqual(
                rejected["proposalDecisions"][0]["reason"],
                "This does not feel like the right scene.",
            )

        asyncio.run(run())

    def test_alive_today_uses_recent_material_body_and_goal_context_without_persisting_review(
        self,
    ) -> None:
        async def run() -> None:
            repository, service, llm = self._service()
            material = await service.store_material(
                {
                    "userId": "user_1",
                    "materialType": "reflection",
                    "text": "The snake image returned after the meeting.",
                    "materialDate": "2026-04-15T08:00:00Z",
                }
            )
            await service.store_body_state(
                {
                    "userId": "user_1",
                    "sensation": "tightness",
                    "observedAt": "2026-04-16T09:00:00Z",
                    "bodyRegion": "chest",
                    "noteText": "My chest tightened as soon as I thought about the meeting.",
                }
            )
            await repository.create_goal(
                {
                    "id": "goal_1",
                    "userId": "user_1",
                    "label": "Confront the authority tension directly",
                    "status": "active",
                    "valueTags": ["truth"],
                    "linkedMaterialIds": [material["id"]],
                    "linkedSymbolIds": [],
                    "createdAt": "2026-04-14T08:00:00Z",
                    "updatedAt": "2026-04-16T08:00:00Z",
                }
            )
            summary = await service.generate_alive_today(
                user_id="user_1",
                window_start="2026-04-12T00:00:00Z",
                window_end="2026-04-19T23:59:59Z",
                explicit_question="What seems connected here?",
            )
            reviews = await repository.list_weekly_reviews("user_1")
            self.assertEqual(reviews, [])
            self.assertEqual(len(llm.alive_today_calls), 1)
            self.assertTrue(
                llm.alive_today_calls[0]["hermesMemoryContext"]["recentMaterialSummaries"]
            )
            self.assertEqual(
                llm.alive_today_calls[0]["methodContextSnapshot"]["recentBodyStates"][0][
                    "bodyRegion"
                ],
                "chest",
            )
            self.assertEqual(
                llm.alive_today_calls[0]["methodContextSnapshot"]["activeGoals"][0]["id"],
                "goal_1",
            )
            self.assertTrue(summary["summary"]["userFacingResponse"].startswith("LLM alive today:"))

        asyncio.run(run())

    def test_interpret_existing_material_supports_store_first_then_interpret_later(self) -> None:
        async def run() -> None:
            repository, service, llm = self._service()
            material = await service.store_material(
                {
                    "userId": "user_1",
                    "materialType": "reflection",
                    "text": "A snake kept appearing in memory after the meeting.",
                }
            )
            workflow = await service.interpret_existing_material(
                user_id="user_1",
                material_id=material["id"],
                explicit_question="What does this seem connected to?",
            )
            self.assertEqual(workflow["material"]["id"], material["id"])
            self.assertEqual(workflow["run"]["materialId"], material["id"])
            self.assertEqual(len(llm.interpret_calls), 1)
            stored_run = await repository.get_interpretation_run("user_1", workflow["run"]["id"])
            self.assertEqual(stored_run["materialId"], material["id"])

        asyncio.run(run())

    def test_dream_interpretation_uses_llm_and_persists_method_gate_output(self) -> None:
        async def run() -> None:
            repository, service, llm = self._service()
            await service.capture_reality_anchors(
                {
                    "userId": "user_1",
                    "summary": "Daily life is stable.",
                    "anchorSummary": "Daily life is stable enough for depth work.",
                    "groundingRecommendation": "clear_for_depth",
                }
            )
            dream = await service.store_material(
                {
                    "userId": "user_1",
                    "materialType": "dream",
                    "text": "There was a snake in the house.",
                }
            )
            workflow = await service.interpret_existing_material(
                user_id="user_1",
                material_id=dream["id"],
            )
            self.assertEqual(len(llm.interpret_calls), 1)
            self.assertTrue(workflow["pendingProposals"])
            self.assertIn("methodGate", workflow["interpretation"])
            self.assertEqual(
                workflow["interpretation"]["methodGate"]["depthLevel"],
                "personal_amplification_needed",
            )
            self.assertIn(
                "conscious_attitude",
                workflow["interpretation"]["methodGate"]["missingPrerequisites"],
            )
            self.assertIn(
                "personal_amplification",
                workflow["interpretation"]["methodGate"]["missingPrerequisites"],
            )
            self.assertNotIn(
                "dream_narrative",
                workflow["interpretation"]["methodGate"]["missingPrerequisites"],
            )
            self.assertEqual(
                workflow["interpretation"]["practiceRecommendation"]["type"],
                "journaling",
            )
            self.assertTrue(workflow["interpretation"]["methodGate"]["requiredPrompts"])
            stored_run = await repository.get_interpretation_run("user_1", workflow["run"]["id"])
            self.assertEqual(
                stored_run["result"]["methodGate"]["depthLevel"],
                "personal_amplification_needed",
            )
            self.assertEqual(len(stored_run["proposalDecisions"]), 1)
            self.assertEqual(stored_run["proposalDecisions"][0]["status"], "pending")

        asyncio.run(run())

    def test_generate_weekly_review_persists_record_and_uses_native_life_context(self) -> None:
        async def run() -> None:
            repository, service, llm = self._service()
            await service.create_and_interpret_material(
                {
                    "userId": "user_1",
                    "materialType": "reflection",
                    "text": "I found a snake image in a flooded cellar after the meeting.",
                    "materialDate": "2026-04-15T08:00:00Z",
                }
            )
            review = await service.generate_weekly_review(
                user_id="user_1",
                window_start="2026-04-12T00:00:00Z",
                window_end="2026-04-19T23:59:59Z",
            )
            reviews = await repository.list_weekly_reviews("user_1")
            self.assertEqual(len(reviews), 1)
            self.assertEqual(reviews[0]["id"], review["id"])
            self.assertTrue(review["result"]["userFacingResponse"].startswith("LLM weekly review:"))
            self.assertEqual(len(llm.review_calls), 1)
            self.assertEqual(
                llm.review_calls[0]["lifeContextSnapshot"]["source"], "circulatio-backend"
            )

        asyncio.run(run())

    def test_generate_weekly_review_respects_grounding_first_method_state(self) -> None:
        async def run() -> None:
            _, service, _ = self._service()
            await service.capture_reality_anchors(
                {
                    "userId": "user_1",
                    "summary": "Outer life is too thin for depth work right now.",
                    "anchorSummary": "Sleep is strained and daily life needs stabilizing first.",
                    "workDailyLifeContinuity": "strained",
                    "sleepBodyRegulation": "strained",
                    "relationshipContact": "thin",
                    "reflectiveCapacity": "fragile",
                    "groundingRecommendation": "grounding_first",
                }
            )
            review = await service.generate_weekly_review(
                user_id="user_1",
                window_start="2026-04-12T00:00:00Z",
                window_end="2026-04-19T23:59:59Z",
            )
            practice = review["result"]["practiceSuggestion"]
            self.assertEqual(practice["type"], "grounding")
            self.assertIn("method_state_grounding_first_fallback", practice["adaptationNotes"])

        asyncio.run(run())

    def test_generate_discovery_surfaces_method_context_longitudinal_items(self) -> None:
        async def run() -> None:
            _, service, _ = self._service()
            await service.store_material(
                {
                    "userId": "user_1",
                    "materialType": "reflection",
                    "text": "The week has felt steady, but a work transition is active.",
                    "materialDate": "2026-04-16T08:00:00Z",
                }
            )
            await service.upsert_goal(
                {
                    "userId": "user_1",
                    "label": "Speak more directly",
                    "status": "active",
                }
            )
            await service.capture_reality_anchors(
                {
                    "userId": "user_1",
                    "summary": "Outer life is steady enough for careful reflection.",
                    "anchorSummary": "Work and relationships are holding.",
                    "workDailyLifeContinuity": "stable",
                    "sleepBodyRegulation": "stable",
                    "relationshipContact": "available",
                    "reflectiveCapacity": "steady",
                    "groundingRecommendation": "clear_for_depth",
                }
            )
            discovery = await service.generate_discovery(
                {
                    "userId": "user_1",
                    "windowStart": "2026-04-12T00:00:00Z",
                    "windowEnd": "2026-04-19T23:59:59Z",
                    "maxItems": 6,
                }
            )
            criteria = {
                criterion
                for section in discovery["sections"]
                for item in section["items"]
                for criterion in item["criteria"]
            }
            self.assertIn("method_context_reality_anchor", criteria)
            self.assertIn("method_context_active_goal", criteria)

        asyncio.run(run())

    def test_discovery_includes_method_state_sections(self) -> None:
        async def run() -> None:
            _, service, _ = self._service()
            material = await service.store_material(
                {
                    "userId": "user_1",
                    "materialType": "reflection",
                    "text": "A recurring work thread keeps returning with chest pressure.",
                    "materialDate": "2026-04-16T08:00:00Z",
                }
            )
            await service.capture_conscious_attitude(
                {
                    "userId": "user_1",
                    "windowStart": "2026-04-12T00:00:00Z",
                    "windowEnd": "2026-04-19T23:59:59Z",
                    "stanceSummary": "Trying to stay in contact without collapsing.",
                    "activeConflicts": ["directness vs safety"],
                }
            )
            await service.store_body_state(
                {
                    "userId": "user_1",
                    "sensation": "tightness",
                    "bodyRegion": "chest",
                    "observedAt": "2026-04-16T09:00:00Z",
                    "linkedMaterialIds": [material["id"]],
                }
            )
            await service.capture_reality_anchors(
                {
                    "userId": "user_1",
                    "summary": "Outer life is steady enough for careful contact.",
                    "anchorSummary": "Containment is present, but pacing still matters.",
                    "groundingRecommendation": "pace_gently",
                }
            )
            await service.create_journey(
                {
                    "userId": "user_1",
                    "label": "Authority thread",
                    "currentQuestion": "How do I stay in contact without armoring?",
                    "relatedMaterialIds": [material["id"]],
                }
            )
            discovery = await service.generate_discovery(
                {
                    "userId": "user_1",
                    "windowStart": "2026-04-12T00:00:00Z",
                    "windowEnd": "2026-04-19T23:59:59Z",
                    "maxItems": 4,
                }
            )
            sections_by_key = {section["key"]: section for section in discovery["sections"]}
            self.assertEqual(
                [section["key"] for section in discovery["sections"]],
                [
                    "recurring",
                    "dream_body_event_links",
                    "ripe_to_revisit",
                    "conscious_attitude",
                    "body_states",
                    "method_state",
                    "journey_threads",
                    "held_for_now",
                ],
            )
            self.assertTrue(sections_by_key["conscious_attitude"]["items"])
            self.assertTrue(sections_by_key["body_states"]["items"])
            self.assertTrue(sections_by_key["method_state"]["items"])
            self.assertTrue(sections_by_key["journey_threads"]["items"])
            self.assertGreaterEqual(discovery["sourceCounts"]["threadDigestCount"], 1)
            self.assertTrue(
                any(
                    "thread_digest" in item["criteria"]
                    for item in sections_by_key["journey_threads"]["items"]
                )
            )

        asyncio.run(run())

    def test_generate_discovery_surfaces_method_state_goal_and_practice_arc(self) -> None:
        async def run() -> None:
            repository, service, _ = self._service()
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
            await repository.create_practice_session(
                {
                    "id": "practice_arc_1",
                    "userId": "user_1",
                    "practiceType": "journaling",
                    "reason": "Track the work thread.",
                    "instructions": ["Write briefly."],
                    "durationMinutes": 8,
                    "contraindicationsChecked": ["none"],
                    "requiresConsent": False,
                    "status": "completed",
                    "activationBefore": "low",
                    "activationAfter": "high",
                    "createdAt": "2026-04-18T10:00:00Z",
                    "updatedAt": "2026-04-18T10:05:00Z",
                }
            )
            discovery = await service.generate_discovery(
                {
                    "userId": "user_1",
                    "windowStart": "2026-04-12T00:00:00Z",
                    "windowEnd": "2026-04-19T23:59:59Z",
                    "maxItems": 6,
                }
            )
            criteria = {
                criterion
                for section in discovery["sections"]
                for item in section["items"]
                for criterion in item["criteria"]
            }
            self.assertIn("method_state_active_goal_tension", criteria)
            self.assertIn("method_state_practice_loop", criteria)

        asyncio.run(run())

    def test_generate_discovery_surfaces_longitudinal_clarification_and_witness_items(self) -> None:
        async def run() -> None:
            repository, service, _ = self._service()
            material = await service.store_material(
                {
                    "userId": "user_1",
                    "materialType": "reflection",
                    "text": "The authority scene still presses on my chest.",
                    "materialDate": "2026-04-18T08:00:00Z",
                }
            )
            goal = await service.upsert_goal(
                {
                    "userId": "user_1",
                    "label": "Speak directly",
                    "status": "active",
                    "linkedMaterialIds": [material["id"]],
                }
            )
            await service.store_body_state(
                {
                    "userId": "user_1",
                    "sensation": "tightness",
                    "observedAt": "2026-04-18T09:00:00Z",
                    "bodyRegion": "chest",
                    "activation": "high",
                    "linkedGoalIds": [goal["id"]],
                    "noteText": "My chest tightened when the email came in.",
                }
            )
            await service.capture_reality_anchors(
                {
                    "userId": "user_1",
                    "summary": "Ordinary life contact is still thin.",
                    "anchorSummary": "Pacing matters because support feels limited.",
                    "relationshipContact": "thin",
                    "groundingRecommendation": "pace_gently",
                }
            )
            await repository.create_typology_lens(
                {
                    "id": "typology_1",
                    "userId": "user_1",
                    "role": "inferior",
                    "function": "sensation",
                    "claim": "Concrete facts can blur when conflict spikes.",
                    "confidence": "low",
                    "status": "user_refined",
                    "evidenceIds": [],
                    "counterevidenceIds": [],
                    "userTestPrompt": "When conflict spikes, do concrete facts go fuzzy first?",
                    "linkedMaterialIds": [material["id"]],
                    "createdAt": "2026-04-18T09:30:00Z",
                    "updatedAt": "2026-04-18T09:30:00Z",
                }
            )
            routed_prompt = await repository.create_clarification_prompt(
                {
                    "id": "prompt_routed",
                    "userId": "user_1",
                    "materialId": material["id"],
                    "questionText": "Where do you feel that pressure?",
                    "questionKey": "body_pressure",
                    "intent": "body_signal",
                    "captureTarget": "body_state",
                    "expectedAnswerKind": "free_text",
                    "status": "pending",
                    "privacyClass": "session_only",
                    "createdAt": "2026-04-18T10:00:00Z",
                    "updatedAt": "2026-04-18T10:00:00Z",
                }
            )
            await service.answer_clarification(
                {
                    "userId": "user_1",
                    "promptId": routed_prompt["id"],
                    "answerText": "My jaw and chest clench.",
                    "answerPayload": {
                        "sensation": "tightness",
                        "bodyRegion": "jaw",
                        "activation": "high",
                    },
                }
            )
            unrouted_prompt = await repository.create_clarification_prompt(
                {
                    "id": "prompt_unrouted",
                    "userId": "user_1",
                    "materialId": material["id"],
                    "questionText": "What should we call this for now?",
                    "questionKey": "naming_pressure",
                    "intent": "other",
                    "captureTarget": "answer_only",
                    "expectedAnswerKind": "free_text",
                    "status": "pending",
                    "privacyClass": "session_only",
                    "createdAt": "2026-04-18T10:10:00Z",
                    "updatedAt": "2026-04-18T10:10:00Z",
                }
            )
            await service.answer_clarification(
                {
                    "userId": "user_1",
                    "promptId": unrouted_prompt["id"],
                    "answerText": "Not sure yet.",
                }
            )
            discovery = await service.generate_discovery(
                {
                    "userId": "user_1",
                    "windowStart": "2026-04-12T00:00:00Z",
                    "windowEnd": "2026-04-22T23:59:59Z",
                    "maxItems": 20,
                }
            )
            criteria = {
                criterion
                for section in discovery["sections"]
                for item in section["items"]
                for criterion in item["criteria"]
            }
            self.assertIn("method_context_longitudinal_signal", criteria)
            self.assertIn("method_state_relational_field", criteria)
            self.assertIn("method_state_typology_method_state", criteria)
            self.assertIn("method_context_witness_state", criteria)
            self.assertNotIn("clarification_state_recently_unrouted", criteria)
            self.assertIn("clarification_state_avoid_repeat", criteria)

        asyncio.run(run())

    def test_threshold_review_practice_respects_grounding_first_method_state(self) -> None:
        async def run() -> None:
            _, service, _ = self._service()
            await service.capture_reality_anchors(
                {
                    "userId": "user_1",
                    "summary": "Outer life is too thin for threshold depth right now.",
                    "anchorSummary": "Containment is strained and sleep is unsettled.",
                    "workDailyLifeContinuity": "strained",
                    "sleepBodyRegulation": "strained",
                    "relationshipContact": "thin",
                    "reflectiveCapacity": "fragile",
                    "groundingRecommendation": "grounding_first",
                }
            )
            workflow = await service.generate_threshold_review(
                {
                    "userId": "user_1",
                    "windowStart": "2026-04-12T00:00:00Z",
                    "windowEnd": "2026-04-19T23:59:59Z",
                    "persist": False,
                }
            )
            practice = workflow["result"]["practiceRecommendation"]
            self.assertEqual(practice["type"], "grounding")
            self.assertIn("method_state_grounding_first_fallback", practice["adaptationNotes"])

        asyncio.run(run())

    def test_generate_discovery_adds_typology_function_dynamics_section_when_requested(
        self,
    ) -> None:
        async def run() -> None:
            repository, service, _ = self._service()
            material = await service.store_material(
                {
                    "userId": "user_1",
                    "materialType": "reflection",
                    "text": "I kept overexplaining while missing what my body was doing.",
                    "materialDate": "2026-04-18T08:00:00Z",
                }
            )
            await repository.create_typology_lens(
                {
                    "id": "typology_lens_1",
                    "userId": "user_1",
                    "role": "dominant",
                    "function": "thinking",
                    "claim": "Reflection organizes the field first.",
                    "confidence": "medium",
                    "status": "candidate",
                    "evidenceIds": ["evidence_1"],
                    "counterevidenceIds": [],
                    "userTestPrompt": "Does thought lead before the body is noticed?",
                    "linkedMaterialIds": [material["id"]],
                    "createdAt": "2026-04-18T09:00:00Z",
                    "updatedAt": "2026-04-18T09:00:00Z",
                }
            )
            await repository.create_typology_lens(
                {
                    "id": "typology_lens_2",
                    "userId": "user_1",
                    "role": "inferior",
                    "function": "sensation",
                    "claim": "Body contact drops out under strain.",
                    "confidence": "low",
                    "status": "user_refined",
                    "evidenceIds": ["evidence_2"],
                    "counterevidenceIds": [],
                    "userTestPrompt": "Does sensation fall away under pressure?",
                    "linkedMaterialIds": [material["id"]],
                    "createdAt": "2026-04-18T09:10:00Z",
                    "updatedAt": "2026-04-18T09:10:00Z",
                }
            )
            discovery = await service.generate_discovery(
                {
                    "userId": "user_1",
                    "windowStart": "2026-04-12T00:00:00Z",
                    "windowEnd": "2026-04-22T23:59:59Z",
                    "analyticLens": "typology_function_dynamics",
                    "maxItems": 20,
                }
            )
            function_section = next(
                section
                for section in discovery["sections"]
                if section["key"] == "function_dynamics"
            )
            self.assertIn("Foreground", {item["label"] for item in function_section["items"]})
            criteria = {
                criterion for item in function_section["items"] for criterion in item["criteria"]
            }
            self.assertIn("typology_function_dynamics", criteria)
            self.assertIn("method_state_typology_method_state", criteria)

        asyncio.run(run())

    def test_generate_discovery_omits_typology_function_dynamics_when_grounding_first(self) -> None:
        async def run() -> None:
            repository, service, _ = self._service()
            await service.capture_reality_anchors(
                {
                    "userId": "user_1",
                    "summary": "Outer life is too thin for depth.",
                    "anchorSummary": "Ground first before typology framing.",
                    "workDailyLifeContinuity": "strained",
                    "sleepBodyRegulation": "strained",
                    "relationshipContact": "thin",
                    "reflectiveCapacity": "fragile",
                    "groundingRecommendation": "grounding_first",
                }
            )
            await repository.create_typology_lens(
                {
                    "id": "typology_grounding_1",
                    "userId": "user_1",
                    "role": "dominant",
                    "function": "intuition",
                    "claim": "Images keep leading.",
                    "confidence": "medium",
                    "status": "candidate",
                    "evidenceIds": ["evidence_1"],
                    "counterevidenceIds": [],
                    "userTestPrompt": "Do images lead before interpretation?",
                    "linkedMaterialIds": [],
                    "createdAt": "2026-04-18T09:00:00Z",
                    "updatedAt": "2026-04-18T09:00:00Z",
                }
            )
            discovery = await service.generate_discovery(
                {
                    "userId": "user_1",
                    "windowStart": "2026-04-12T00:00:00Z",
                    "windowEnd": "2026-04-22T23:59:59Z",
                    "analyticLens": "typology_function_dynamics",
                    "maxItems": 20,
                }
            )
            self.assertFalse(
                any(section["key"] == "function_dynamics" for section in discovery["sections"])
            )

        asyncio.run(run())

    def test_living_myth_review_practice_respects_grounding_first_method_state(self) -> None:
        async def run() -> None:
            _, service, _ = self._service()
            await service.capture_reality_anchors(
                {
                    "userId": "user_1",
                    "summary": "Outer life is too thin for symbolic synthesis right now.",
                    "anchorSummary": "Daily life needs grounding before chapter-scale meaning work.",
                    "workDailyLifeContinuity": "strained",
                    "sleepBodyRegulation": "strained",
                    "relationshipContact": "thin",
                    "reflectiveCapacity": "fragile",
                    "groundingRecommendation": "grounding_first",
                }
            )
            workflow = await service.generate_living_myth_review(
                {
                    "userId": "user_1",
                    "windowStart": "2026-04-12T00:00:00Z",
                    "windowEnd": "2026-04-19T23:59:59Z",
                    "persist": False,
                }
            )
            practice = workflow["result"]["practiceRecommendation"]
            self.assertEqual(practice["type"], "grounding")
            self.assertIn("method_state_grounding_first_fallback", practice["adaptationNotes"])

        asyncio.run(run())

    def test_review_and_packet_inputs_lift_longitudinal_method_state_fields(self) -> None:
        async def run() -> None:
            repository, service, llm = self._service()
            material = await service.store_material(
                {
                    "userId": "user_1",
                    "materialType": "dream",
                    "text": "A threshold and a returning guide stayed with me.",
                    "materialDate": "2026-04-18T08:00:00Z",
                }
            )
            first_goal = await service.upsert_goal(
                {
                    "userId": "user_1",
                    "label": "Speak directly",
                    "status": "active",
                    "linkedMaterialIds": [material["id"]],
                }
            )
            second_goal = await service.upsert_goal(
                {
                    "userId": "user_1",
                    "label": "Stay safe",
                    "status": "active",
                    "linkedMaterialIds": [material["id"]],
                }
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
            await repository.create_practice_session(
                {
                    "id": "practice_review_input",
                    "userId": "user_1",
                    "practiceType": "journaling",
                    "reason": "Track what shifts without forcing it.",
                    "instructions": ["Write what changed."],
                    "durationMinutes": 8,
                    "contraindicationsChecked": ["none"],
                    "requiresConsent": False,
                    "status": "completed",
                    "activationBefore": "high",
                    "activationAfter": "moderate",
                    "createdAt": "2026-04-18T09:00:00Z",
                    "updatedAt": "2026-04-18T09:05:00Z",
                    "completedAt": "2026-04-18T09:05:00Z",
                }
            )
            journey = await service.create_journey(
                {
                    "userId": "user_1",
                    "label": "Threshold thread",
                    "currentQuestion": "What is trying to come through carefully?",
                    "relatedMaterialIds": [material["id"]],
                }
            )
            await service.capture_reality_anchors(
                {
                    "userId": "user_1",
                    "summary": "Outer life can hold paced symbolic contact.",
                    "anchorSummary": "Containment is present if the pace stays gentle.",
                    "relationshipContact": "available",
                    "groundingRecommendation": "pace_gently",
                }
            )
            await repository.create_living_myth_record(
                {
                    "id": "wellbeing_1",
                    "userId": "user_1",
                    "recordType": "symbolic_wellbeing_snapshot",
                    "status": "active",
                    "source": "user_reported",
                    "label": "Symbolic wellbeing",
                    "summary": "Symbolic wellbeing snapshot.",
                    "confidence": "medium",
                    "evidenceIds": [],
                    "relatedMaterialIds": [material["id"]],
                    "relatedSymbolIds": [],
                    "relatedGoalIds": [first_goal["id"]],
                    "relatedDreamSeriesIds": [],
                    "relatedIndividuationRecordIds": [],
                    "privacyClass": "approved_summary",
                    "details": {
                        "capacitySummary": "Symbolic contact is present without much strain.",
                        "groundingCapacity": "steady",
                        "symbolicLiveliness": "steady",
                        "somaticContact": "available",
                        "relationalSpaciousness": "growing",
                        "agencyTone": "measured",
                    },
                    "createdAt": "2026-04-18T10:00:00Z",
                    "updatedAt": "2026-04-18T10:00:00Z",
                }
            )
            await repository.create_typology_lens(
                {
                    "id": "typology_packet_1",
                    "userId": "user_1",
                    "role": "dominant",
                    "function": "intuition",
                    "claim": "Images and emerging patterning lead the field.",
                    "confidence": "medium",
                    "status": "candidate",
                    "evidenceIds": ["evidence_1"],
                    "counterevidenceIds": [],
                    "userTestPrompt": "Do images lead before analysis settles?",
                    "linkedMaterialIds": [material["id"]],
                    "createdAt": "2026-04-18T10:05:00Z",
                    "updatedAt": "2026-04-18T10:05:00Z",
                }
            )

            review_workflow = await service.generate_living_myth_review(
                {
                    "userId": "user_1",
                    "windowStart": "2026-04-12T00:00:00Z",
                    "windowEnd": "2026-04-19T23:59:59Z",
                    "persist": False,
                }
            )
            review_input = llm.living_myth_review_calls[0]
            self.assertEqual(
                review_input["activeGoalTension"]["goalTensionId"],
                review_input["methodContextSnapshot"]["methodState"]["activeGoalTension"][
                    "goalTensionId"
                ],
            )
            self.assertEqual(
                review_input["practiceLoop"]["recentOutcomeTrend"],
                review_input["methodContextSnapshot"]["methodState"]["practiceLoop"][
                    "recentOutcomeTrend"
                ],
            )
            self.assertEqual(
                review_input["latestSymbolicWellbeing"]["id"],
                review_input["methodContextSnapshot"]["livingMythContext"][
                    "latestSymbolicWellbeing"
                ]["id"],
            )
            self.assertEqual(review_input["activeJourneys"][0]["id"], journey["id"])
            self.assertEqual(
                review_input["witnessState"]["stance"],
                review_input["methodContextSnapshot"]["witnessState"]["stance"],
            )
            self.assertTrue(review_input["threadDigests"])
            self.assertTrue(
                any(journey["id"] in item["journeyIds"] for item in review_input["threadDigests"])
            )

            packet_workflow = await service.generate_analysis_packet(
                {
                    "userId": "user_1",
                    "windowStart": "2026-04-12T00:00:00Z",
                    "windowEnd": "2026-04-19T23:59:59Z",
                    "analyticLens": "typology_function_dynamics",
                    "persist": False,
                }
            )
            packet_input = llm.analysis_packet_calls[0]
            self.assertEqual(
                packet_input["activeGoalTension"]["goalTensionId"],
                review_input["activeGoalTension"]["goalTensionId"],
            )
            self.assertEqual(
                packet_input["practiceLoop"]["recentOutcomeTrend"],
                review_input["practiceLoop"]["recentOutcomeTrend"],
            )
            self.assertEqual(
                packet_input["latestSymbolicWellbeing"]["id"],
                review_input["latestSymbolicWellbeing"]["id"],
            )
            self.assertEqual(packet_input["activeJourneys"][0]["id"], journey["id"])
            self.assertEqual(packet_input["analyticLens"], "typology_function_dynamics")
            self.assertIn("typologyEvidenceDigest", packet_input)
            self.assertEqual(
                packet_input["typologyEvidenceDigest"]["status"],
                "hypotheses_available",
            )
            self.assertEqual(
                packet_input["witnessState"]["stance"],
                packet_input["methodContextSnapshot"]["witnessState"]["stance"],
            )
            self.assertTrue(packet_input["threadDigests"])
            self.assertEqual(
                review_workflow["continuity"]["methodContextSnapshot"]["witnessState"]["stance"],
                review_input["witnessState"]["stance"],
            )
            self.assertTrue(review_workflow["continuity"]["threadDigests"])
            self.assertEqual(
                packet_workflow["continuity"]["methodContextSnapshot"]["witnessState"]["stance"],
                packet_input["witnessState"]["stance"],
            )

        asyncio.run(run())

    def test_threshold_review_lifts_longitudinal_fields_from_canonical_bundle(self) -> None:
        async def run() -> None:
            repository, service, llm = self._service()
            material = await service.store_material(
                {
                    "userId": "user_1",
                    "materialType": "dream",
                    "text": "A threshold and a returning guide stayed with me.",
                    "materialDate": "2026-04-18T08:00:00Z",
                }
            )
            first_goal = await service.upsert_goal(
                {
                    "userId": "user_1",
                    "label": "Speak directly",
                    "status": "active",
                    "linkedMaterialIds": [material["id"]],
                }
            )
            second_goal = await service.upsert_goal(
                {
                    "userId": "user_1",
                    "label": "Stay safe",
                    "status": "active",
                    "linkedMaterialIds": [material["id"]],
                }
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
            await repository.create_practice_session(
                {
                    "id": "practice_threshold_input",
                    "userId": "user_1",
                    "practiceType": "journaling",
                    "reason": "Track what shifts without forcing it.",
                    "instructions": ["Write what changed."],
                    "durationMinutes": 8,
                    "contraindicationsChecked": ["none"],
                    "requiresConsent": False,
                    "status": "completed",
                    "activationBefore": "high",
                    "activationAfter": "moderate",
                    "createdAt": "2026-04-18T09:00:00Z",
                    "updatedAt": "2026-04-18T09:05:00Z",
                    "completedAt": "2026-04-18T09:05:00Z",
                }
            )
            await service.create_journey(
                {
                    "userId": "user_1",
                    "label": "Threshold thread",
                    "currentQuestion": "What is trying to come through carefully?",
                    "relatedMaterialIds": [material["id"]],
                }
            )
            await service.capture_reality_anchors(
                {
                    "userId": "user_1",
                    "summary": "Outer life can hold paced symbolic contact.",
                    "anchorSummary": "Containment is present if the pace stays gentle.",
                    "relationshipContact": "available",
                    "groundingRecommendation": "pace_gently",
                }
            )
            await repository.create_living_myth_record(
                {
                    "id": "threshold_wellbeing_1",
                    "userId": "user_1",
                    "recordType": "symbolic_wellbeing_snapshot",
                    "status": "active",
                    "source": "user_reported",
                    "label": "Symbolic wellbeing",
                    "summary": "Symbolic wellbeing snapshot.",
                    "confidence": "medium",
                    "evidenceIds": [],
                    "relatedMaterialIds": [material["id"]],
                    "relatedSymbolIds": [],
                    "relatedGoalIds": [first_goal["id"]],
                    "relatedDreamSeriesIds": [],
                    "relatedIndividuationRecordIds": [],
                    "privacyClass": "approved_summary",
                    "details": {
                        "capacitySummary": "Symbolic contact is present without much strain.",
                        "groundingCapacity": "steady",
                        "symbolicLiveliness": "steady",
                        "somaticContact": "available",
                        "relationalSpaciousness": "growing",
                        "agencyTone": "measured",
                    },
                    "createdAt": "2026-04-18T10:00:00Z",
                    "updatedAt": "2026-04-18T10:00:00Z",
                }
            )

            workflow = await service.generate_threshold_review(
                {
                    "userId": "user_1",
                    "windowStart": "2026-04-12T00:00:00Z",
                    "windowEnd": "2026-04-19T23:59:59Z",
                    "persist": False,
                }
            )

            review_input = llm.threshold_review_calls[0]
            self.assertEqual(
                review_input["activeGoalTension"]["goalTensionId"],
                review_input["methodContextSnapshot"]["methodState"]["activeGoalTension"][
                    "goalTensionId"
                ],
            )
            self.assertEqual(
                review_input["practiceLoop"]["recentOutcomeTrend"],
                review_input["methodContextSnapshot"]["methodState"]["practiceLoop"][
                    "recentOutcomeTrend"
                ],
            )
            self.assertEqual(
                review_input["latestSymbolicWellbeing"]["id"],
                review_input["methodContextSnapshot"]["livingMythContext"][
                    "latestSymbolicWellbeing"
                ]["id"],
            )
            self.assertEqual(
                review_input["witnessState"]["stance"],
                review_input["methodContextSnapshot"]["witnessState"]["stance"],
            )
            self.assertTrue(review_input["threadDigests"])
            self.assertEqual(
                workflow["continuity"]["methodContextSnapshot"]["witnessState"]["stance"],
                review_input["witnessState"]["stance"],
            )

        asyncio.run(run())

    def test_life_os_context_flows_into_llm_input_when_native_context_is_empty(self) -> None:
        async def run() -> None:
            _, service, llm = self._service()
            await service.create_and_interpret_material(
                {
                    "userId": "user_1",
                    "materialType": "reflection",
                    "text": "A snake under the stairs stayed with me all day.",
                    "lifeOsWindow": {
                        "start": "2026-04-12T00:00:00Z",
                        "end": "2026-04-19T00:00:00Z",
                    },
                }
            )
            self.assertEqual(len(llm.interpret_calls), 1)
            self.assertIn("lifeContextSnapshot", llm.interpret_calls[0])
            snapshot = llm.interpret_calls[0]["lifeContextSnapshot"]
            self.assertEqual(snapshot["source"], "hermes-life-os")
            self.assertTrue(snapshot["lifeEventRefs"])

        asyncio.run(run())

    def test_service_prefers_native_context_over_life_os_context(self) -> None:
        async def run() -> None:
            _, service, llm = self._service()
            await service.create_and_interpret_material(
                {
                    "userId": "user_1",
                    "materialType": "reflection",
                    "text": "The snake image came back after the conflict.",
                    "materialDate": "2026-04-13T08:00:00Z",
                }
            )
            await service.create_and_interpret_material(
                {
                    "userId": "user_1",
                    "materialType": "reflection",
                    "text": "Another snake moved through the house.",
                    "materialDate": "2026-04-16T08:00:00Z",
                    "lifeOsWindow": {
                        "start": "2026-04-12T00:00:00Z",
                        "end": "2026-04-19T00:00:00Z",
                    },
                }
            )
            self.assertEqual(len(llm.interpret_calls), 2)
            self.assertEqual(
                llm.interpret_calls[-1]["lifeContextSnapshot"]["source"], "circulatio-backend"
            )

        asyncio.run(run())

    def test_service_builds_native_context_without_life_os_window(self) -> None:
        async def run() -> None:
            _, service, llm = self._service()
            await service.create_and_interpret_material(
                {
                    "userId": "user_1",
                    "materialType": "reflection",
                    "text": "The snake image came back after the conflict.",
                    "materialDate": "2026-04-13T08:00:00Z",
                }
            )
            await service.create_and_interpret_material(
                {
                    "userId": "user_1",
                    "materialType": "reflection",
                    "text": "Another snake moved through the house.",
                    "materialDate": "2026-04-16T08:00:00Z",
                }
            )
            self.assertEqual(len(llm.interpret_calls), 2)
            self.assertEqual(
                llm.interpret_calls[-1]["lifeContextSnapshot"]["source"], "circulatio-backend"
            )

        asyncio.run(run())

    def test_journey_page_is_read_mostly_and_uses_alive_today_context(self) -> None:
        async def run() -> None:
            repository, service, llm = self._service()
            await service.store_material(
                {
                    "userId": "user_1",
                    "materialType": "reflection",
                    "text": "The snake image stayed with me after the meeting.",
                    "materialDate": "2026-04-16T08:00:00Z",
                }
            )
            await service.store_body_state(
                {
                    "userId": "user_1",
                    "sensation": "tightness",
                    "observedAt": "2026-04-16T09:00:00Z",
                    "bodyRegion": "chest",
                    "activation": "high",
                }
            )
            await repository.create_goal(
                {
                    "id": create_id("goal"),
                    "userId": "user_1",
                    "label": "Speak more directly",
                    "status": "active",
                    "valueTags": ["truth"],
                    "linkedMaterialIds": [],
                    "linkedSymbolIds": [],
                    "createdAt": "2026-04-15T08:00:00Z",
                    "updatedAt": "2026-04-15T08:00:00Z",
                }
            )

            page = await service.generate_journey_page(
                {
                    "userId": "user_1",
                    "windowStart": "2026-04-12T00:00:00Z",
                    "windowEnd": "2026-04-19T23:59:59Z",
                }
            )

            self.assertEqual(
                [card["section"] for card in page["cards"]],
                [
                    "alive_today",
                    "weekly_reflection",
                    "rhythmic_invitations",
                    "tending_now",
                    "practice_container",
                    "analysis_packet",
                ],
            )
            self.assertEqual(await repository.list_weekly_reviews("user_1"), [])
            self.assertEqual(await repository.list_proactive_briefs("user_1"), [])
            self.assertEqual(await repository.list_practice_sessions("user_1"), [])
            self.assertEqual(await repository.list_journey_experiments("user_1"), [])
            self.assertIsNone(await repository.get_adaptation_profile("user_1"))
            self.assertEqual(len(llm.alive_today_calls), 1)
            self.assertIn("methodContextSnapshot", llm.alive_today_calls[0])
            self.assertTrue(llm.alive_today_calls[0]["methodContextSnapshot"]["recentBodyStates"])
            self.assertTrue(llm.alive_today_calls[0]["methodContextSnapshot"]["activeGoals"])
            self.assertTrue(page["continuity"]["threadDigests"])
            self.assertEqual(
                page["continuity"]["methodContextSnapshot"]["recentBodyStates"][0]["bodyRegion"],
                "chest",
            )

        asyncio.run(run())

    def test_journey_page_uses_latest_weekly_review_without_creating_new_review(self) -> None:
        async def run() -> None:
            repository, service, _ = self._service()
            await service.store_material(
                {
                    "userId": "user_1",
                    "materialType": "reflection",
                    "text": "A snake moved through the house this week.",
                    "materialDate": "2026-04-16T08:00:00Z",
                }
            )
            review = await service.generate_weekly_review(
                user_id="user_1",
                window_start="2026-04-12T00:00:00Z",
                window_end="2026-04-19T23:59:59Z",
            )
            page = await service.generate_journey_page(
                {
                    "userId": "user_1",
                    "windowStart": "2026-04-12T00:00:00Z",
                    "windowEnd": "2026-04-19T23:59:59Z",
                }
            )
            reviews = await repository.list_weekly_reviews("user_1")
            self.assertEqual(len(reviews), 1)
            self.assertEqual(page["weeklySurface"]["kind"], "latest_review")
            self.assertEqual(page["weeklySurface"]["reviewId"], review["id"])

        asyncio.run(run())

    def test_journey_page_exposes_review_available_surface_without_persisting(self) -> None:
        async def run() -> None:
            repository, service, _ = self._service()
            page = await service.generate_journey_page(
                {
                    "userId": "user_1",
                    "windowStart": "2026-04-12T00:00:00Z",
                    "windowEnd": "2026-04-19T23:59:59Z",
                }
            )
            self.assertEqual(page["weeklySurface"]["kind"], "review_due")
            self.assertEqual(await repository.list_weekly_reviews("user_1"), [])

        asyncio.run(run())

    def test_journey_page_prefers_existing_due_practice_followup(self) -> None:
        async def run() -> None:
            repository, service, _ = self._service()
            await repository.create_practice_session(
                {
                    "id": "practice_due",
                    "userId": "user_1",
                    "practiceType": "journaling",
                    "reason": "Hold the image lightly.",
                    "instructions": ["Write what changed."],
                    "durationMinutes": 10,
                    "contraindicationsChecked": ["none"],
                    "requiresConsent": False,
                    "status": "accepted",
                    "followUpPrompt": "What changed after staying with it?",
                    "nextFollowUpDueAt": "2026-04-18T00:00:00Z",
                    "source": "manual",
                    "followUpCount": 1,
                    "createdAt": "2026-04-17T00:00:00Z",
                    "updatedAt": "2026-04-17T00:00:00Z",
                }
            )
            page = await service.generate_journey_page(
                {
                    "userId": "user_1",
                    "windowStart": "2026-04-12T00:00:00Z",
                    "windowEnd": "2026-04-19T23:59:59Z",
                }
            )
            practices = await repository.list_practice_sessions("user_1")
            self.assertEqual(len(practices), 1)
            self.assertEqual(page["practiceContainer"]["kind"], "practice_follow_up")
            self.assertEqual(page["practiceContainer"]["practiceSessionId"], "practice_due")

        asyncio.run(run())

    def test_journey_page_analysis_packet_is_bounded_preview(self) -> None:
        async def run() -> None:
            repository, service, _ = self._service()
            for index in range(6):
                await repository.create_symbol(
                    {
                        "id": f"symbol_{index}",
                        "userId": "user_1",
                        "canonicalName": f"symbol-{index}",
                        "aliases": [],
                        "category": "object",
                        "recurrenceCount": index + 1,
                        "firstSeen": "2026-04-12T00:00:00Z",
                        "lastSeen": "2026-04-19T00:00:00Z",
                        "valenceHistory": [],
                        "personalAssociations": [],
                        "linkedMaterialIds": [],
                        "linkedLifeEventRefs": [],
                        "status": "active",
                        "createdAt": "2026-04-12T00:00:00Z",
                        "updatedAt": "2026-04-19T00:00:00Z",
                    }
                )
                await repository.create_journey(
                    {
                        "id": f"journey_{index}",
                        "userId": "user_1",
                        "label": f"Journey {index}",
                        "status": "active",
                        "relatedMaterialIds": [],
                        "relatedSymbolIds": [],
                        "relatedPatternIds": [],
                        "relatedDreamSeriesIds": [],
                        "relatedGoalIds": [],
                        "currentQuestion": f"What is shifting in thread {index}?",
                        "createdAt": "2026-04-12T00:00:00Z",
                        "updatedAt": "2026-04-19T00:00:00Z",
                    }
                )
                await repository.create_practice_session(
                    {
                        "id": f"practice_{index}",
                        "userId": "user_1",
                        "practiceType": "journaling",
                        "reason": f"Practice {index}",
                        "instructions": ["Write briefly."],
                        "durationMinutes": 5,
                        "contraindicationsChecked": ["none"],
                        "requiresConsent": False,
                        "status": "completed",
                        "outcome": f"Outcome {index}",
                        "source": "manual",
                        "followUpCount": 0,
                        "createdAt": "2026-04-12T00:00:00Z",
                        "updatedAt": "2026-04-19T00:00:00Z",
                        "completedAt": "2026-04-19T00:00:00Z",
                    }
                )
            page = await service.generate_journey_page(
                {
                    "userId": "user_1",
                    "windowStart": "2026-04-12T00:00:00Z",
                    "windowEnd": "2026-04-19T23:59:59Z",
                }
            )
            preview = page["analysisPacket"]
            self.assertLessEqual(len(preview["sections"]), 5)
            self.assertTrue(all(len(section["items"]) <= 5 for section in preview["sections"]))
            self.assertNotIn("futureSeams", preview)
            self.assertTrue(
                all(
                    "count" not in item and "score" not in item
                    for section in preview["sections"]
                    for item in section["items"]
                )
            )

        asyncio.run(run())

    def test_create_journey_stores_low_risk_container_without_interpretation(self) -> None:
        async def run() -> None:
            repository, service, _ = self._service()
            material = await service.store_material(
                {
                    "userId": "user_1",
                    "materialType": "reflection",
                    "text": "I keep thinking about her when I do my wash.",
                }
            )
            goal = await repository.create_goal(
                {
                    "id": create_id("goal"),
                    "userId": "user_1",
                    "label": "Stay present in contact",
                    "status": "active",
                    "valueTags": [],
                    "linkedMaterialIds": [],
                    "linkedSymbolIds": [],
                    "createdAt": "2026-04-18T00:00:00Z",
                    "updatedAt": "2026-04-18T00:00:00Z",
                }
            )
            symbol = await repository.create_symbol(
                {
                    "id": "symbol_washing",
                    "userId": "user_1",
                    "canonicalName": "washing",
                    "aliases": [],
                    "category": "activity",
                    "recurrenceCount": 1,
                    "firstSeen": "2026-04-18T00:00:00Z",
                    "lastSeen": "2026-04-18T00:00:00Z",
                    "valenceHistory": [],
                    "personalAssociations": [],
                    "linkedMaterialIds": [],
                    "linkedLifeEventRefs": [],
                    "status": "active",
                    "createdAt": "2026-04-18T00:00:00Z",
                    "updatedAt": "2026-04-18T00:00:00Z",
                }
            )

            journey = await service.create_journey(
                {
                    "userId": "user_1",
                    "label": "Laundry return",
                    "currentQuestion": "Why does this thought return in this ordinary ritual?",
                    "relatedMaterialIds": [material["id"]],
                    "relatedGoalIds": [goal["id"]],
                    "relatedSymbolIds": [symbol["id"]],
                }
            )

            self.assertEqual(journey["status"], "active")
            self.assertEqual(journey["relatedMaterialIds"], [material["id"]])
            self.assertEqual(journey["relatedGoalIds"], [goal["id"]])
            self.assertEqual(journey["relatedSymbolIds"], [symbol["id"]])
            self.assertEqual(await repository.list_interpretation_runs("user_1"), [])

        asyncio.run(run())

    def test_update_journey_merges_and_unlinks_related_ids(self) -> None:
        async def run() -> None:
            repository, service, _ = self._service()
            material_one = await service.store_material(
                {
                    "userId": "user_1",
                    "materialType": "reflection",
                    "text": "The thread begins with direct contact.",
                }
            )
            material_two = await service.store_material(
                {
                    "userId": "user_1",
                    "materialType": "reflection",
                    "text": "The same thread returns after the message.",
                }
            )
            goal_one = await repository.create_goal(
                {
                    "id": "goal_one",
                    "userId": "user_1",
                    "label": "Protect the nervous system",
                    "status": "active",
                    "valueTags": [],
                    "linkedMaterialIds": [],
                    "linkedSymbolIds": [],
                    "createdAt": "2026-04-18T00:00:00Z",
                    "updatedAt": "2026-04-18T00:00:00Z",
                }
            )
            goal_two = await repository.create_goal(
                {
                    "id": "goal_two",
                    "userId": "user_1",
                    "label": "Stay in contact without collapse",
                    "status": "active",
                    "valueTags": [],
                    "linkedMaterialIds": [],
                    "linkedSymbolIds": [],
                    "createdAt": "2026-04-18T00:00:00Z",
                    "updatedAt": "2026-04-18T00:00:00Z",
                }
            )
            symbol_one = await repository.create_symbol(
                {
                    "id": "symbol_pressure",
                    "userId": "user_1",
                    "canonicalName": "pressure",
                    "aliases": [],
                    "category": "feeling",
                    "recurrenceCount": 1,
                    "firstSeen": "2026-04-18T00:00:00Z",
                    "lastSeen": "2026-04-18T00:00:00Z",
                    "valenceHistory": [],
                    "personalAssociations": [],
                    "linkedMaterialIds": [],
                    "linkedLifeEventRefs": [],
                    "status": "active",
                    "createdAt": "2026-04-18T00:00:00Z",
                    "updatedAt": "2026-04-18T00:00:00Z",
                }
            )
            symbol_two = await repository.create_symbol(
                {
                    "id": "symbol_contact",
                    "userId": "user_1",
                    "canonicalName": "contact",
                    "aliases": [],
                    "category": "relation",
                    "recurrenceCount": 1,
                    "firstSeen": "2026-04-18T00:00:00Z",
                    "lastSeen": "2026-04-18T00:00:00Z",
                    "valenceHistory": [],
                    "personalAssociations": [],
                    "linkedMaterialIds": [],
                    "linkedLifeEventRefs": [],
                    "status": "active",
                    "createdAt": "2026-04-18T00:00:00Z",
                    "updatedAt": "2026-04-18T00:00:00Z",
                }
            )
            journey = await service.create_journey(
                {
                    "userId": "user_1",
                    "label": "Contact pressure",
                    "currentQuestion": "What collapses here?",
                    "relatedMaterialIds": [material_one["id"]],
                    "relatedGoalIds": [goal_one["id"]],
                    "relatedSymbolIds": [symbol_one["id"]],
                }
            )

            updated = await service.update_journey(
                {
                    "userId": "user_1",
                    "journeyId": journey["id"],
                    "currentQuestion": "What repeats when direct contact appears?",
                    "addRelatedMaterialIds": [material_two["id"]],
                    "addRelatedGoalIds": [goal_two["id"]],
                    "removeRelatedGoalIds": [goal_one["id"]],
                    "addRelatedSymbolIds": [symbol_two["id"]],
                    "removeRelatedSymbolIds": [symbol_one["id"]],
                }
            )

            self.assertEqual(
                updated["currentQuestion"],
                "What repeats when direct contact appears?",
            )
            self.assertEqual(
                updated["relatedMaterialIds"],
                [material_one["id"], material_two["id"]],
            )
            self.assertEqual(updated["relatedGoalIds"], [goal_two["id"]])
            self.assertEqual(updated["relatedSymbolIds"], [symbol_two["id"]])

        asyncio.run(run())

    def test_set_journey_status_and_list_filter_work(self) -> None:
        async def run() -> None:
            _, service, _ = self._service()
            journey = await service.create_journey(
                {
                    "userId": "user_1",
                    "label": "Returning contact thread",
                }
            )

            paused = await service.set_journey_status(
                {
                    "userId": "user_1",
                    "journeyId": journey["id"],
                    "status": "paused",
                }
            )
            active = await service.set_journey_status(
                {
                    "userId": "user_1",
                    "journeyId": journey["id"],
                    "status": "active",
                }
            )
            active_list = await service.list_journeys({"userId": "user_1", "statuses": ["active"]})

            self.assertEqual(paused["status"], "paused")
            self.assertEqual(active["status"], "active")
            self.assertEqual([item["id"] for item in active_list], [journey["id"]])

        asyncio.run(run())

    def test_start_journey_experiment_from_brief_is_idempotent_and_links_brief(self) -> None:
        async def run() -> None:
            repository, service, _ = self._service()
            journey = await service.create_journey(
                {
                    "userId": "user_1",
                    "label": "Returning contact thread",
                }
            )
            brief = await repository.create_proactive_brief(
                {
                    "id": create_id("proactive_brief"),
                    "userId": "user_1",
                    "briefType": "journey_checkin",
                    "status": "candidate",
                    "title": "Current tending",
                    "summary": "Stay with this thread lightly.",
                    "relatedJourneyIds": [journey["id"]],
                    "relatedMaterialIds": [],
                    "relatedSymbolIds": [],
                    "relatedPracticeSessionIds": [],
                    "relatedExperimentIds": [],
                    "evidenceIds": [],
                    "createdAt": "2026-04-19T00:00:00Z",
                    "updatedAt": "2026-04-19T00:00:00Z",
                }
            )

            first = await service.start_journey_experiment(
                {"userId": "user_1", "briefId": brief["id"]}
            )
            second = await service.start_journey_experiment(
                {"userId": "user_1", "briefId": brief["id"]}
            )
            experiments = await repository.list_journey_experiments("user_1")
            updated_brief = await repository.get_proactive_brief("user_1", brief["id"])

            self.assertEqual(first["id"], second["id"])
            self.assertEqual(len(experiments), 1)
            self.assertEqual(updated_brief["status"], "acted_on")
            self.assertEqual(updated_brief["relatedExperimentIds"], [first["id"]])

        asyncio.run(run())

    def test_dismissing_experiment_linked_brief_quiets_the_experiment(self) -> None:
        async def run() -> None:
            repository, service, _ = self._service()
            journey = await service.create_journey(
                {
                    "userId": "user_1",
                    "label": "Returning contact thread",
                }
            )
            experiment = await service.start_journey_experiment(
                {
                    "userId": "user_1",
                    "journeyId": journey["id"],
                    "title": "Current tending",
                    "summary": "Stay with this thread lightly.",
                }
            )
            brief = await repository.create_proactive_brief(
                {
                    "id": create_id("proactive_brief"),
                    "userId": "user_1",
                    "briefType": "journey_checkin",
                    "status": "candidate",
                    "title": "Journey check-in",
                    "summary": "A light check-in remains available.",
                    "relatedJourneyIds": [journey["id"]],
                    "relatedMaterialIds": [],
                    "relatedSymbolIds": [],
                    "relatedPracticeSessionIds": [],
                    "relatedExperimentIds": [experiment["id"]],
                    "evidenceIds": [],
                    "createdAt": "2026-04-19T00:00:00Z",
                    "updatedAt": "2026-04-19T00:00:00Z",
                }
            )

            dismissed = await service.respond_rhythmic_brief(
                {"userId": "user_1", "briefId": brief["id"], "action": "dismissed"}
            )
            updated_experiment = await repository.get_journey_experiment("user_1", experiment["id"])

            self.assertEqual(dismissed["status"], "dismissed")
            self.assertEqual(updated_experiment["status"], "quiet")
            self.assertEqual(updated_experiment["cooldownUntil"], dismissed["cooldownUntil"])

        asyncio.run(run())

    def test_pausing_journey_quiets_current_experiment(self) -> None:
        async def run() -> None:
            repository, service, _ = self._service()
            journey = await service.create_journey(
                {
                    "userId": "user_1",
                    "label": "Returning contact thread",
                }
            )
            experiment = await service.start_journey_experiment(
                {
                    "userId": "user_1",
                    "journeyId": journey["id"],
                    "title": "Current tending",
                    "summary": "Stay with this thread lightly.",
                }
            )

            await service.set_journey_status(
                {
                    "userId": "user_1",
                    "journeyId": journey["id"],
                    "status": "paused",
                }
            )
            updated_experiment = await repository.get_journey_experiment("user_1", experiment["id"])

            self.assertEqual(updated_experiment["status"], "quiet")

        asyncio.run(run())

    def test_quieting_journey_experiment_clears_due_date_and_resume_stays_neutral(self) -> None:
        async def run() -> None:
            repository, service, _ = self._service()
            journey = await service.create_journey(
                {
                    "userId": "user_1",
                    "label": "Returning contact thread",
                }
            )
            experiment = await repository.create_journey_experiment(
                {
                    "id": create_id("journey_experiment"),
                    "userId": "user_1",
                    "journeyId": journey["id"],
                    "title": "Current tending",
                    "summary": "Stay with this thread lightly.",
                    "status": "active",
                    "source": "manual",
                    "bodyFirst": False,
                    "relatedPracticeSessionIds": [],
                    "relatedBriefIds": [],
                    "relatedSymbolIds": [],
                    "relatedGoalTensionIds": [],
                    "relatedBodyStateIds": [],
                    "relatedResourceIds": [],
                    "nextCheckInDueAt": "2026-04-21T00:00:00Z",
                    "createdAt": "2026-04-20T08:00:00Z",
                    "updatedAt": "2026-04-20T08:00:00Z",
                }
            )

            quiet = await service.respond_journey_experiment(
                {"userId": "user_1", "experimentId": experiment["id"], "action": "quiet"}
            )
            resumed = await service.respond_journey_experiment(
                {"userId": "user_1", "experimentId": experiment["id"], "action": "resume"}
            )

            self.assertEqual(quiet["status"], "quiet")
            self.assertEqual(quiet.get("nextCheckInDueAt", ""), "")
            self.assertTrue(str(quiet.get("cooldownUntil") or ""))
            self.assertEqual(resumed["status"], "active")
            self.assertEqual(resumed.get("nextCheckInDueAt", ""), "")

        asyncio.run(run())

    def test_practice_responses_resolve_linked_experiments(self) -> None:
        async def run() -> None:
            repository, service, _ = self._service()
            journey = await service.create_journey(
                {
                    "userId": "user_1",
                    "label": "Returning contact thread",
                }
            )
            accepted_experiment = await repository.create_journey_experiment(
                {
                    "id": create_id("journey_experiment"),
                    "userId": "user_1",
                    "journeyId": journey["id"],
                    "title": "Current tending",
                    "summary": "Stay with this thread lightly.",
                    "status": "active",
                    "source": "manual",
                    "bodyFirst": False,
                    "relatedPracticeSessionIds": [],
                    "relatedBriefIds": [],
                    "relatedSymbolIds": [],
                    "relatedGoalTensionIds": [],
                    "relatedBodyStateIds": [],
                    "relatedResourceIds": [],
                    "nextCheckInDueAt": "2026-04-21T00:00:00Z",
                    "createdAt": "2026-04-20T08:00:00Z",
                    "updatedAt": "2026-04-20T08:00:00Z",
                }
            )
            skipped_experiment = await repository.create_journey_experiment(
                {
                    "id": create_id("journey_experiment"),
                    "userId": "user_1",
                    "journeyId": journey["id"],
                    "title": "Current tending",
                    "summary": "Stay with this thread lightly.",
                    "status": "active",
                    "source": "manual",
                    "bodyFirst": False,
                    "relatedPracticeSessionIds": [],
                    "relatedBriefIds": [],
                    "relatedSymbolIds": [],
                    "relatedGoalTensionIds": [],
                    "relatedBodyStateIds": [],
                    "relatedResourceIds": [],
                    "nextCheckInDueAt": "2026-04-21T00:00:00Z",
                    "createdAt": "2026-04-20T08:00:00Z",
                    "updatedAt": "2026-04-20T08:00:00Z",
                }
            )
            accepted_practice = await repository.create_practice_session(
                {
                    "id": create_id("practice_session"),
                    "userId": "user_1",
                    "practiceType": "journaling",
                    "target": "thread contact",
                    "reason": "stay with the thread",
                    "instructions": [],
                    "durationMinutes": 5,
                    "contraindicationsChecked": [],
                    "requiresConsent": False,
                    "status": "recommended",
                    "source": "manual",
                    "followUpCount": 0,
                    "relatedJourneyIds": [journey["id"]],
                    "relatedExperimentIds": [accepted_experiment["id"]],
                    "createdAt": "2026-04-20T08:00:00Z",
                    "updatedAt": "2026-04-20T08:00:00Z",
                }
            )
            skipped_practice = await repository.create_practice_session(
                {
                    "id": create_id("practice_session"),
                    "userId": "user_1",
                    "practiceType": "grounding",
                    "target": "settle body",
                    "reason": "stay with the thread",
                    "instructions": [],
                    "durationMinutes": 5,
                    "contraindicationsChecked": [],
                    "requiresConsent": False,
                    "status": "recommended",
                    "source": "manual",
                    "followUpCount": 0,
                    "relatedJourneyIds": [journey["id"]],
                    "relatedExperimentIds": [skipped_experiment["id"]],
                    "createdAt": "2026-04-20T08:00:00Z",
                    "updatedAt": "2026-04-20T08:00:00Z",
                }
            )

            await service.respond_practice_recommendation(
                {
                    "userId": "user_1",
                    "practiceSessionId": accepted_practice["id"],
                    "action": "accepted",
                }
            )
            await service.respond_practice_recommendation(
                {
                    "userId": "user_1",
                    "practiceSessionId": skipped_practice["id"],
                    "action": "skipped",
                    "note": "Not today.",
                }
            )
            accepted_updated = await repository.get_journey_experiment(
                "user_1", accepted_experiment["id"]
            )
            skipped_updated = await repository.get_journey_experiment(
                "user_1", skipped_experiment["id"]
            )

            self.assertEqual(accepted_updated["status"], "quiet")
            self.assertEqual(
                accepted_updated["relatedPracticeSessionIds"], [accepted_practice["id"]]
            )
            self.assertEqual(accepted_updated.get("nextCheckInDueAt", ""), "")
            self.assertTrue(str(accepted_updated.get("cooldownUntil") or ""))
            self.assertEqual(skipped_updated["status"], "quiet")
            self.assertEqual(skipped_updated["relatedPracticeSessionIds"], [skipped_practice["id"]])
            self.assertEqual(skipped_updated.get("nextCheckInDueAt", ""), "")
            self.assertTrue(str(skipped_updated.get("cooldownUntil") or ""))

        asyncio.run(run())

    def test_practice_outcome_completes_linked_experiment(self) -> None:
        async def run() -> None:
            repository, service, _ = self._service()
            journey = await service.create_journey(
                {
                    "userId": "user_1",
                    "label": "Returning contact thread",
                }
            )
            experiment = await repository.create_journey_experiment(
                {
                    "id": create_id("journey_experiment"),
                    "userId": "user_1",
                    "journeyId": journey["id"],
                    "title": "Current tending",
                    "summary": "Stay with this thread lightly.",
                    "status": "active",
                    "source": "manual",
                    "bodyFirst": False,
                    "relatedPracticeSessionIds": [],
                    "relatedBriefIds": [],
                    "relatedSymbolIds": [],
                    "relatedGoalTensionIds": [],
                    "relatedBodyStateIds": [],
                    "relatedResourceIds": [],
                    "nextCheckInDueAt": "2026-04-21T00:00:00Z",
                    "createdAt": "2026-04-20T08:00:00Z",
                    "updatedAt": "2026-04-20T08:00:00Z",
                }
            )
            practice = await repository.create_practice_session(
                {
                    "id": create_id("practice_session"),
                    "userId": "user_1",
                    "practiceType": "grounding",
                    "target": "settle body",
                    "reason": "stay with the thread",
                    "instructions": [],
                    "durationMinutes": 5,
                    "contraindicationsChecked": [],
                    "requiresConsent": False,
                    "status": "recommended",
                    "source": "manual",
                    "followUpCount": 0,
                    "relatedJourneyIds": [journey["id"]],
                    "relatedExperimentIds": [experiment["id"]],
                    "createdAt": "2026-04-20T08:00:00Z",
                    "updatedAt": "2026-04-20T08:00:00Z",
                }
            )

            result = await service.record_practice_outcome(
                user_id="user_1",
                practice_session_id=practice["id"],
                material_id=None,
                outcome={
                    "practiceType": "grounding",
                    "outcome": "Felt more settled after grounding.",
                },
            )
            updated_experiment = await repository.get_journey_experiment("user_1", experiment["id"])

            self.assertEqual(result["practiceSession"]["status"], "completed")
            self.assertEqual(updated_experiment["status"], "completed")
            self.assertEqual(updated_experiment["relatedPracticeSessionIds"], [practice["id"]])
            self.assertEqual(updated_experiment.get("nextCheckInDueAt", ""), "")
            self.assertTrue(str(updated_experiment.get("completedAt") or ""))

        asyncio.run(run())

    def test_journey_reference_resolution_supports_exact_and_normalized_labels(self) -> None:
        async def run() -> None:
            _, service, _ = self._service()
            journey = await service.create_journey(
                {
                    "userId": "user_1",
                    "label": "Laundry Return",
                }
            )

            exact = await service.get_journey(
                {"userId": "user_1", "journeyLabel": "Laundry Return"}
            )
            normalized = await service.get_journey(
                {"userId": "user_1", "journeyLabel": "  laundry-return  "}
            )
            updated = await service.update_journey(
                {
                    "userId": "user_1",
                    "journeyLabel": "laundry return",
                    "currentQuestion": "What keeps looping back here?",
                }
            )
            paused = await service.set_journey_status(
                {
                    "userId": "user_1",
                    "journeyLabel": "laundry_return",
                    "status": "paused",
                }
            )

            self.assertEqual(exact["id"], journey["id"])
            self.assertEqual(normalized["id"], journey["id"])
            self.assertEqual(updated["id"], journey["id"])
            self.assertEqual(updated["currentQuestion"], "What keeps looping back here?")
            self.assertEqual(paused["id"], journey["id"])
            self.assertEqual(paused["status"], "paused")

        asyncio.run(run())

    def test_journey_label_resolution_raises_conflict_for_ambiguous_normalized_matches(
        self,
    ) -> None:
        async def run() -> None:
            _, service, _ = self._service()
            await service.create_journey(
                {
                    "userId": "user_1",
                    "label": "Contact Pressure",
                }
            )
            await service.create_journey(
                {
                    "userId": "user_1",
                    "label": "contact-pressure",
                }
            )

            with self.assertRaises(ConflictError):
                await service.get_journey({"userId": "user_1", "journeyLabel": "contact pressure"})

        asyncio.run(run())

    def test_create_journey_rejects_unknown_symbol_links(self) -> None:
        async def run() -> None:
            _, service, _ = self._service()
            with self.assertRaises(ValidationError):
                await service.create_journey(
                    {
                        "userId": "user_1",
                        "label": "Unknown symbol thread",
                        "relatedSymbolIds": ["missing_symbol"],
                    }
                )

        asyncio.run(run())

    def test_interpretation_input_includes_trusted_amplification_sources_and_keeps_culture_separate(
        self,
    ) -> None:
        async def run() -> None:
            _, service, llm = self._service()
            await service.set_cultural_frame(
                {
                    "userId": "user_1",
                    "label": "Jungian amplification",
                    "type": "mythic",
                    "allowedUses": ["collective_amplification"],
                }
            )
            await service.create_and_interpret_material(
                {
                    "userId": "user_1",
                    "materialType": "dream",
                    "text": "A serpent circled a tree.",
                    "options": {"allowCulturalAmplification": True},
                }
            )
            interpret_input = llm.interpret_calls[-1]
            self.assertEqual(
                interpret_input["trustedAmplificationSources"][0]["label"],
                "Symbolonline",
            )
            self.assertEqual(
                interpret_input["trustedAmplificationSources"][1]["url"],
                "https://aras.org/",
            )
            self.assertEqual(
                interpret_input["methodContextSnapshot"]["activeCulturalFrames"][0]["label"],
                "Jungian amplification",
            )

        asyncio.run(run())

    def test_answer_clarification_rejects_empty_answer_when_not_skipping(self) -> None:
        async def run() -> None:
            _, service, _ = self._service()
            with self.assertRaises(ValidationError) as ctx:
                await service.answer_clarification(
                    {"userId": "user_1", "answerText": "", "skip": False}
                )
            self.assertIn("answerText is required", str(ctx.exception))

        asyncio.run(run())

    def test_answer_clarification_skip_without_prompt_creates_skipped_record(self) -> None:
        async def run() -> None:
            _, service, _ = self._service()
            result = await service.answer_clarification(
                {"userId": "user_1", "answerText": "", "skip": True}
            )
            self.assertEqual(result["routingStatus"], "skipped")
            self.assertEqual(result["answer"]["routingStatus"], "skipped")
            self.assertEqual(result["createdRecordRefs"], [])

        asyncio.run(run())

    def test_answer_clarification_answer_only_is_unrouted_without_payload(self) -> None:
        async def run() -> None:
            _, service, _ = self._service()
            result = await service.answer_clarification(
                {
                    "userId": "user_1",
                    "answerText": "Just thinking out loud.",
                    "captureTargetOverride": "answer_only",
                }
            )
            self.assertEqual(result["routingStatus"], "unrouted")
            self.assertEqual(result["createdRecordRefs"], [])
            self.assertFalse(result["answer"].get("validationErrors"))

        asyncio.run(run())

    def test_answer_clarification_body_state_needs_review_when_payload_missing(
        self,
    ) -> None:
        async def run() -> None:
            _, service, _ = self._service()
            result = await service.answer_clarification(
                {
                    "userId": "user_1",
                    "answerText": "My chest feels tight.",
                    "captureTargetOverride": "body_state",
                }
            )
            self.assertEqual(result["routingStatus"], "needs_review")
            errors = result["answer"].get("validationErrors", [])
            self.assertTrue(any("Structured answerPayload is required" in e for e in errors))

        asyncio.run(run())

    def test_answer_clarification_body_state_reroutes_free_text_when_prompt_has_anchor_metadata(
        self,
    ) -> None:
        async def run() -> None:
            repository, service, llm = self._service()
            material = await service.store_material(
                {
                    "userId": "user_1",
                    "materialType": "reflection",
                    "text": "The room felt charged before I answered.",
                    "materialDate": "2026-04-18T08:00:00Z",
                }
            )
            prompt = await repository.create_clarification_prompt(
                {
                    "id": "clarification_prompt_body_anchor",
                    "userId": "user_1",
                    "materialId": material["id"],
                    "questionText": "Where did you feel it in your body?",
                    "questionKey": "body_location",
                    "intent": "body_signal",
                    "captureTarget": "body_state",
                    "expectedAnswerKind": "free_text",
                    "routingHints": {"anchorRefs": {"materialId": material["id"]}},
                    "status": "pending",
                    "privacyClass": "session_only",
                    "createdAt": "2026-04-21T10:00:00Z",
                    "updatedAt": "2026-04-21T10:00:00Z",
                }
            )
            result = await service.answer_clarification(
                {
                    "userId": "user_1",
                    "promptId": prompt["id"],
                    "answerText": "My chest tightened before I answered her.",
                }
            )
            body_states = await repository.list_body_states("user_1")
            self.assertEqual(result["routingStatus"], "routed")
            self.assertEqual(result["createdRecordRefs"][0]["recordType"], "BodyState")
            self.assertEqual(result["prompt"]["status"], "answered")
            self.assertEqual(len(body_states), 1)
            self.assertEqual(body_states[0]["bodyRegion"], "chest")
            self.assertEqual(len(llm.method_state_route_calls), 1)
            self.assertEqual(llm.method_state_route_calls[0]["source"], "clarifying_answer")

        asyncio.run(run())

    def test_answer_clarification_body_state_needs_review_on_invalid_payload(
        self,
    ) -> None:
        async def run() -> None:
            _, service, _ = self._service()
            result = await service.answer_clarification(
                {
                    "userId": "user_1",
                    "answerText": "Tightness",
                    "captureTargetOverride": "body_state",
                    "answerPayload": {"bodyRegion": "chest"},
                }
            )
            self.assertEqual(result["routingStatus"], "needs_review")
            errors = result["answer"].get("validationErrors", [])
            self.assertTrue(any("payload.sensation" in e for e in errors))

        asyncio.run(run())

    def test_answer_clarification_happy_path_body_state(self) -> None:
        async def run() -> None:
            repository, service, _ = self._service()
            result = await service.answer_clarification(
                {
                    "userId": "user_1",
                    "answerText": "Tight chest",
                    "captureTargetOverride": "body_state",
                    "answerPayload": {
                        "sensation": "tightness",
                        "bodyRegion": "chest",
                        "activation": "high",
                    },
                }
            )
            self.assertEqual(result["routingStatus"], "routed")
            self.assertEqual(len(result["createdRecordRefs"]), 1)
            self.assertEqual(result["createdRecordRefs"][0]["recordType"], "BodyState")
            body_states = await repository.list_body_states("user_1")
            self.assertEqual(len(body_states), 1)
            self.assertEqual(body_states[0]["sensation"], "tightness")

        asyncio.run(run())

    def test_answer_clarification_happy_path_goal(self) -> None:
        async def run() -> None:
            repository, service, _ = self._service()
            result = await service.answer_clarification(
                {
                    "userId": "user_1",
                    "answerText": "I want to speak more directly",
                    "captureTargetOverride": "goal",
                    "answerPayload": {
                        "label": "Speak more directly",
                        "valueTags": ["truth"],
                    },
                }
            )
            self.assertEqual(result["routingStatus"], "routed")
            self.assertEqual(result["createdRecordRefs"][0]["recordType"], "Goal")
            goals = await repository.list_goals("user_1")
            self.assertEqual(len(goals), 1)
            self.assertEqual(goals[0]["label"], "Speak more directly")

        asyncio.run(run())

    def test_answer_clarification_happy_path_threshold_process(self) -> None:
        async def run() -> None:
            repository, service, _ = self._service()
            result = await service.answer_clarification(
                {
                    "userId": "user_1",
                    "answerText": "Work identity ending",
                    "captureTargetOverride": "threshold_process",
                    "answerPayload": {
                        "summary": "An older work identity is ending.",
                        "thresholdName": "Vocational threshold",
                        "normalizedThresholdKey": "vocational-threshold",
                        "phase": "liminal",
                    },
                }
            )
            self.assertEqual(result["routingStatus"], "routed")
            self.assertEqual(result["createdRecordRefs"][0]["recordType"], "ThresholdProcess")
            records = await repository.list_individuation_records(
                "user_1", record_types=["threshold_process"], limit=20
            )
            self.assertEqual(len(records), 1)
            self.assertEqual(records[0]["details"]["thresholdName"], "Vocational threshold")

        asyncio.run(run())

    def test_answer_clarification_happy_path_interpretation_preference(self) -> None:
        async def run() -> None:
            repository, service, _ = self._service()
            result = await service.answer_clarification(
                {
                    "userId": "user_1",
                    "answerText": "Keep it body-first and light.",
                    "captureTargetOverride": "interpretation_preference",
                    "answerPayload": {
                        "depthPreference": "brief_pattern_notes",
                        "modalityBias": "body",
                    },
                }
            )
            self.assertEqual(result["routingStatus"], "routed")
            self.assertEqual(result["createdRecordRefs"][0]["recordType"], "AdaptationProfile")
            profile = await repository.get_adaptation_profile("user_1")
            self.assertEqual(
                profile["explicitPreferences"]["interpretation"]["depthPreference"],
                "brief_pattern_notes",
            )
            self.assertEqual(
                profile["explicitPreferences"]["interpretation"]["modalityBias"],
                "body",
            )

        asyncio.run(run())

    def test_answer_clarification_happy_path_typology_feedback(self) -> None:
        async def run() -> None:
            repository, service, _ = self._service()
            result = await service.answer_clarification(
                {
                    "userId": "user_1",
                    "answerText": "That framing fits, but only very lightly.",
                    "captureTargetOverride": "typology_feedback",
                    "answerPayload": {
                        "role": "inferior",
                        "function": "sensation",
                        "claim": "Concrete facts can drop out when conflict spikes.",
                        "confidence": "low",
                        "status": "user_refined",
                        "evidenceIds": ["evidence_1"],
                        "userTestPrompt": "When conflict spikes, do concrete facts get fuzzy first?",
                    },
                }
            )
            self.assertEqual(result["routingStatus"], "routed")
            self.assertEqual(result["createdRecordRefs"][0]["recordType"], "TypologyLens")
            lenses = await repository.list_typology_lenses("user_1")
            self.assertEqual(len(lenses), 1)
            self.assertEqual(lenses[0]["function"], "sensation")
            self.assertEqual(lenses[0]["status"], "user_refined")
            self.assertEqual(lenses[0]["evidenceIds"], ["evidence_1"])

        asyncio.run(run())

    def test_answer_clarification_typology_feedback_merges_evidence_ids(self) -> None:
        async def run() -> None:
            repository, service, _ = self._service()
            await service.answer_clarification(
                {
                    "userId": "user_1",
                    "answerText": "That still fits.",
                    "captureTargetOverride": "typology_feedback",
                    "answerPayload": {
                        "role": "inferior",
                        "function": "sensation",
                        "claim": "Concrete facts can drop out when conflict spikes.",
                        "confidence": "low",
                        "status": "user_refined",
                        "evidenceIds": ["evidence_1"],
                        "userTestPrompt": "When conflict spikes, do concrete facts get fuzzy first?",
                    },
                }
            )
            await service.answer_clarification(
                {
                    "userId": "user_1",
                    "answerText": "The same frame still fits.",
                    "captureTargetOverride": "typology_feedback",
                    "answerPayload": {
                        "claim": "Concrete facts can drop out when conflict spikes.",
                        "evidenceIds": ["evidence_2"],
                        "userTestPrompt": "When conflict spikes, do concrete facts get fuzzy first?",
                    },
                }
            )
            lenses = await repository.list_typology_lenses("user_1")
            self.assertEqual(lenses[0]["evidenceIds"], ["evidence_1", "evidence_2"])

        asyncio.run(run())

    def test_answer_clarification_uses_capture_target_override_over_prompt(
        self,
    ) -> None:
        async def run() -> None:
            repository, service, _ = self._service()
            prompt = await repository.create_clarification_prompt(
                {
                    "id": "prompt_1",
                    "userId": "user_1",
                    "questionText": "Where do you feel it?",
                    "intent": "body_signal",
                    "captureTarget": "body_state",
                    "expectedAnswerKind": "free_text",
                    "status": "pending",
                    "privacyClass": "session_only",
                    "createdAt": "2026-04-21T10:00:00Z",
                    "updatedAt": "2026-04-21T10:00:00Z",
                }
            )
            result = await service.answer_clarification(
                {
                    "userId": "user_1",
                    "promptId": prompt["id"],
                    "answerText": "Just a note.",
                    "captureTargetOverride": "answer_only",
                }
            )
            self.assertEqual(result["routingStatus"], "unrouted")
            self.assertEqual(result["answer"]["captureTarget"], "answer_only")
            self.assertEqual(result["prompt"]["status"], "answered_unrouted")

        asyncio.run(run())

    def test_answer_clarification_rejects_other_users_prompt(self) -> None:
        async def run() -> None:
            repository, service, _ = self._service()
            prompt = await repository.create_clarification_prompt(
                {
                    "id": "prompt_u2",
                    "userId": "user_2",
                    "questionText": "What is your goal?",
                    "intent": "goal_pressure",
                    "captureTarget": "goal",
                    "expectedAnswerKind": "free_text",
                    "status": "pending",
                    "privacyClass": "session_only",
                    "createdAt": "2026-04-21T10:00:00Z",
                    "updatedAt": "2026-04-21T10:00:00Z",
                }
            )
            with self.assertRaises(Exception) as ctx:
                await service.answer_clarification(
                    {
                        "userId": "user_1",
                        "promptId": prompt["id"],
                        "answerText": "hello",
                    }
                )
            self.assertIn("prompt_u2", str(ctx.exception))

        asyncio.run(run())

    def test_answer_clarification_emits_adaptation_signals_for_routed_and_skipped(
        self,
    ) -> None:
        async def run() -> None:
            repository, service, _ = self._service()
            await service.answer_clarification(
                {
                    "userId": "user_1",
                    "answerText": "",
                    "skip": True,
                    "captureTargetOverride": "body_state",
                }
            )
            await service.answer_clarification(
                {
                    "userId": "user_1",
                    "answerText": "Heat",
                    "captureTargetOverride": "body_state",
                    "answerPayload": {"sensation": "heat"},
                }
            )
            profile = await repository.get_adaptation_profile("user_1")
            self.assertEqual(profile["sampleCounts"].get("clarification_skipped", 0), 1)
            self.assertEqual(profile["sampleCounts"].get("clarification_answered", 0), 1)
            recent = profile.get("learnedSignals", {}).get("recentEvents", [])
            types = [e.get("type") for e in recent[-3:]]
            self.assertIn("clarification_skipped", types)
            self.assertIn("clarification_answered", types)

        asyncio.run(run())

    def test_ensure_clarification_prompt_for_run_skips_recent_repeated_question_key(
        self,
    ) -> None:
        async def run() -> None:
            repository, service, _ = self._service()
            material = await service.store_material(
                {
                    "userId": "user_1",
                    "materialType": "reflection",
                    "text": "The image still feels charged.",
                    "materialDate": "2026-04-18T08:00:00Z",
                }
            )
            await repository.create_clarification_prompt(
                {
                    "id": "prompt_existing",
                    "userId": "user_1",
                    "materialId": material["id"],
                    "questionText": "Where do you feel that pressure?",
                    "questionKey": "body_pressure",
                    "intent": "body_signal",
                    "captureTarget": "body_state",
                    "expectedAnswerKind": "free_text",
                    "status": "answered_unrouted",
                    "privacyClass": "session_only",
                    "createdAt": "2026-04-20T10:00:00Z",
                    "updatedAt": "2026-04-20T10:05:00Z",
                }
            )
            prompts = await service._ensure_clarification_prompt_for_run(
                user_id="user_1",
                material=material,
                run_id="run_new",
                interpretation={
                    "clarificationPlan": {
                        "questionText": "Where do you feel that pressure?",
                        "questionKey": "body_pressure",
                        "intent": "body_signal",
                        "captureTarget": "body_state",
                        "expectedAnswerKind": "free_text",
                    }
                },
            )
            stored_prompts = await repository.list_clarification_prompts("user_1", limit=20)
            self.assertEqual(prompts, [])
            self.assertEqual(len(stored_prompts), 1)

        asyncio.run(run())

    def test_store_practice_plan_persists_coach_metadata(self) -> None:
        async def run() -> None:
            repository, service, _ = self._service()
            practice = {
                "id": create_id("practice_plan"),
                "type": "journaling",
                "reason": "Track the shift without forcing meaning.",
                "instructions": ["Write what changed."],
                "durationMinutes": 5,
                "contraindicationsChecked": ["none"],
                "requiresConsent": False,
                "coachLoopKey": "coach:soma:body_1",
                "resourceInvitationId": "resource_invitation_1",
            }
            record = await service._store_practice_plan(
                user_id="user_1",
                practice=practice,
                trigger={"triggerType": "manual"},
            )
            persisted = await repository.get_practice_session("user_1", record["id"])
            self.assertEqual(persisted["coachLoopKey"], "coach:soma:body_1")
            self.assertEqual(persisted["resourceInvitationId"], "resource_invitation_1")

        asyncio.run(run())

    def test_practice_followup_reuses_persisted_resource_invitation(self) -> None:
        async def run() -> None:
            repository, service, _ = self._service()
            await repository.create_practice_session(
                {
                    "id": "practice_1",
                    "userId": "user_1",
                    "practiceType": "journaling",
                    "reason": "Track the authority pattern.",
                    "instructions": ["Write for five minutes."],
                    "durationMinutes": 6,
                    "contraindicationsChecked": ["none"],
                    "requiresConsent": False,
                    "status": "completed",
                    "activationBefore": "low",
                    "activationAfter": "high",
                    "coachLoopKey": "coach:practice_integration:practice_1",
                    "coachLoopKind": "practice_integration",
                    "coachMoveKind": "offer_resource",
                    "resourceInvitationId": "resource_invitation_1",
                    "resourceInvitation": {
                        "id": "resource_invitation_1",
                        "resource": {
                            "id": "resource_1",
                            "title": "Three breaths",
                            "provider": "Circulatio",
                            "url": "https://example.com/resource",
                            "resourceType": "micro_practice",
                            "modality": "breath",
                            "activationBand": "high",
                            "contraindications": [],
                            "tags": ["grounding"],
                            "curationSource": "catalog",
                            "reviewedAt": "2026-04-20T00:00:00Z",
                        },
                        "triggerLoopKey": "coach:practice_integration:practice_1",
                        "reason": "A gentler resource fits the current pacing.",
                        "activationRationale": "Recent practice signals suggest a gentler modality.",
                        "capture": {
                            "source": "practice_feedback",
                            "anchorRefs": {
                                "coachLoopKey": "coach:practice_integration:practice_1",
                                "practiceSessionId": "practice_1",
                                "resourceInvitationId": "resource_invitation_1",
                            },
                            "expectedTargets": [
                                "practice_outcome",
                                "practice_preference",
                                "body_state",
                            ],
                            "maxQuestions": 1,
                            "answerMode": "choice_then_free_text",
                            "skipBehavior": "cooldown",
                        },
                        "presentationPolicy": {
                            "allowNotNow": True,
                            "preserveHostChoice": True,
                            "renderAs": "resource_card",
                        },
                        "createdAt": "2026-04-20T10:05:00Z",
                    },
                    "relatedResourceIds": ["resource_1"],
                    "createdAt": "2026-04-20T10:00:00Z",
                    "updatedAt": "2026-04-20T10:05:00Z",
                }
            )
            snapshot = service._enrich_method_context_snapshot(
                {
                    "windowStart": "2026-04-20T00:00:00Z",
                    "windowEnd": "2026-04-21T00:00:00Z",
                    "methodState": {
                        "practiceLoop": {"recentOutcomeTrend": "activating"},
                    },
                },
                window_start="2026-04-20T00:00:00Z",
                window_end="2026-04-21T00:00:00Z",
                surface="practice_followup",
                existing_briefs=[],
                recent_practices=await repository.list_practice_sessions("user_1"),
                journeys=[],
            )
            coach_state = snapshot["coachState"]
            self.assertEqual(
                coach_state["selectedMove"]["resourceInvitation"]["id"],
                "resource_invitation_1",
            )
            self.assertEqual(
                coach_state["selectedMove"]["capture"]["anchorRefs"]["resourceInvitationId"],
                "resource_invitation_1",
            )

        asyncio.run(run())

    def test_store_rhythmic_brief_persists_coach_and_resource_metadata(self) -> None:
        async def run() -> None:
            repository, service, _ = self._service()
            brief = await service._store_rhythmic_brief(
                user_id="user_1",
                source="manual",
                seed={
                    "briefType": "resource_invitation",
                    "triggerKey": "coach:resource_support:current",
                    "priority": 96,
                    "relatedJourneyIds": [],
                    "relatedMaterialIds": [],
                    "relatedSymbolIds": [],
                    "relatedPracticeSessionIds": [],
                    "evidenceIds": ["evidence_1"],
                    "coachLoopKey": "coach:resource_support:current",
                    "coachLoopKind": "resource_support",
                    "coachMoveKind": "offer_resource",
                    "capture": {
                        "source": "body_note",
                        "expectedTargets": ["body_state"],
                        "answerMode": "choice_then_free_text",
                        "skipBehavior": "cooldown",
                        "anchorRefs": {"coachLoopKey": "coach:resource_support:current"},
                    },
                    "resourceInvitation": {
                        "id": "resource_invitation_1",
                        "resource": {"id": "resource_1"},
                        "triggerLoopKey": "coach:resource_support:current",
                        "reason": "Grounding first.",
                        "activationRationale": "Containment is thin.",
                        "capture": {
                            "source": "body_note",
                            "expectedTargets": ["body_state"],
                            "answerMode": "choice_then_free_text",
                            "skipBehavior": "cooldown",
                        },
                        "presentationPolicy": {"style": "grounding_first"},
                        "createdAt": "2026-04-21T10:00:00Z",
                    },
                },
                result={
                    "title": "Resource support",
                    "summary": "A gentler resource fits better here.",
                    "userFacingResponse": "A gentler resource may help before going deeper.",
                },
                created_at="2026-04-21T10:00:00Z",
            )
            persisted = await repository.get_proactive_brief("user_1", brief["id"])
            self.assertEqual(persisted["coachLoopKey"], "coach:resource_support:current")
            self.assertEqual(persisted["coachLoopKind"], "resource_support")
            self.assertEqual(persisted["coachMoveKind"], "offer_resource")
            self.assertEqual(persisted["resourceInvitation"]["id"], "resource_invitation_1")
            self.assertEqual(persisted["relatedResourceIds"], ["resource_1"])

        asyncio.run(run())

    def test_canonical_bundle_produces_consistent_thread_state_across_surfaces(self) -> None:
        async def run() -> None:
            repository, service, _ = self._service()
            await service.create_material(
                {
                    "userId": "user_1",
                    "materialType": "dream",
                    "text": "A river flows through a dark forest.",
                    "materialDate": "2026-04-20T08:00:00Z",
                }
            )
            await service.create_journey(
                {
                    "userId": "user_1",
                    "label": "Forest exploration",
                    "currentQuestion": "What does the forest represent?",
                }
            )
            store_result = await service.store_material_with_intake_context(
                {
                    "userId": "user_1",
                    "materialType": "reflection",
                    "text": "The forest feels familiar.",
                    "materialDate": "2026-04-21T10:00:00Z",
                }
            )
            continuity = store_result["continuity"]
            self.assertIn("threadDigests", continuity)
            self.assertIn("generatedAt", continuity)
            self.assertIn("windowStart", continuity)
            self.assertIn("windowEnd", continuity)
            store_digest_keys = {d["threadKey"] for d in continuity["threadDigests"]}
            alive_result = await service.generate_alive_today(
                user_id="user_1",
                window_start="2026-04-14T00:00:00Z",
                window_end="2026-04-21T23:59:59Z",
            )
            alive_digest_keys = {
                d["threadKey"] for d in alive_result["continuity"]["threadDigests"]
            }
            self.assertTrue(store_digest_keys.issubset(alive_digest_keys))

        asyncio.run(run())

    def test_dream_series_appears_in_thread_digests_with_evidence(self) -> None:
        async def run() -> None:
            repository, service, _ = self._service()
            material = await service.create_material(
                {
                    "userId": "user_1",
                    "materialType": "dream",
                    "text": "I was in a house with many rooms.",
                }
            )
            await repository.create_dream_series(
                {
                    "id": create_id("dream_series"),
                    "userId": "user_1",
                    "label": "House dreams",
                    "status": "active",
                    "confidence": "medium",
                    "materialIds": [material["id"]],
                    "symbolIds": [],
                    "motifKeys": ["house"],
                    "settingKeys": [],
                    "figureKeys": [],
                    "createdAt": "2026-04-20T08:00:00Z",
                    "updatedAt": "2026-04-20T08:00:00Z",
                }
            )
            result = await service.store_material_with_intake_context(
                {
                    "userId": "user_1",
                    "materialType": "reflection",
                    "text": "Thinking about the house dream.",
                    "materialDate": "2026-04-21T10:00:00Z",
                }
            )
            continuity = result["continuity"]
            dream_digests = [d for d in continuity["threadDigests"] if d["kind"] == "dream_series"]
            self.assertTrue(dream_digests)
            self.assertEqual(
                dream_digests[0]["evidenceIds"],
                [material["id"]],
            )

        asyncio.run(run())

    def test_post_write_continuity_refresh_from_practice_outcome(self) -> None:
        async def run() -> None:
            repository, service, _ = self._service()
            practice = await service._repository.create_practice_session(
                {
                    "id": create_id("practice_session"),
                    "userId": "user_1",
                    "practiceType": "grounding",
                    "target": "body awareness",
                    "reason": "grounding after dream",
                    "instructions": [],
                    "durationMinutes": 5,
                    "contraindicationsChecked": [],
                    "requiresConsent": False,
                    "status": "recommended",
                    "source": "manual",
                    "followUpCount": 0,
                    "createdAt": "2026-04-20T08:00:00Z",
                    "updatedAt": "2026-04-20T08:00:00Z",
                }
            )
            result = await service.record_practice_outcome(
                user_id="user_1",
                practice_session_id=practice["id"],
                material_id=None,
                outcome={
                    "practiceType": "grounding",
                    "outcome": "Felt more settled after grounding.",
                },
            )
            self.assertIn("continuity", result)
            continuity = result["continuity"]
            self.assertIn("threadDigests", continuity)
            self.assertIn("generatedAt", continuity)

        asyncio.run(run())

    def test_journey_page_uses_canonical_bundle(self) -> None:
        async def run() -> None:
            repository, service, _ = self._service()
            await service.create_material(
                {
                    "userId": "user_1",
                    "materialType": "dream",
                    "text": "A bridge over water.",
                    "materialDate": "2026-04-20T08:00:00Z",
                }
            )
            await service.create_journey(
                {
                    "userId": "user_1",
                    "label": "Water dreams",
                    "currentQuestion": "What does the water mean?",
                }
            )
            page = await service.generate_journey_page(
                {
                    "userId": "user_1",
                    "windowStart": "2026-04-14T00:00:00Z",
                    "windowEnd": "2026-04-21T23:59:59Z",
                }
            )
            self.assertIn("continuity", page)
            self.assertIn("threadDigests", page["continuity"])
            self.assertTrue(page["continuity"]["threadDigests"])
            self.assertIn("aliveToday", page)
            self.assertIn("weeklySurface", page)
            self.assertIn("practiceContainer", page)

        asyncio.run(run())

    def test_longitudinal_signal_surface_readiness(self) -> None:
        async def run() -> None:
            repository, service, _ = self._service()
            await service.create_material(
                {
                    "userId": "user_1",
                    "materialType": "dream",
                    "text": "A recurring snake image.",
                    "materialDate": "2026-04-15T08:00:00Z",
                }
            )
            await service.create_material(
                {
                    "userId": "user_1",
                    "materialType": "dream",
                    "text": "The snake returns again.",
                    "materialDate": "2026-04-20T08:00:00Z",
                }
            )
            result = await service.store_material_with_intake_context(
                {
                    "userId": "user_1",
                    "materialType": "reflection",
                    "text": "Noticing the snake pattern.",
                    "materialDate": "2026-04-21T10:00:00Z",
                }
            )
            continuity = result["continuity"]
            self.assertIn("threadDigests", continuity)
            for digest in continuity["threadDigests"]:
                self.assertIn("surfaceReadiness", digest)
                self.assertIn("threadKey", digest)
                self.assertIn("kind", digest)
                self.assertIn("evidenceIds", digest)

        asyncio.run(run())


if __name__ == "__main__":
    unittest.main()
