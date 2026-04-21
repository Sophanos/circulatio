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
        core = CirculatioCore(repository, llm=llm)
        builder = CirculatioLifeContextBuilder(repository)
        context_adapter = ContextAdapter(
            repository,
            life_os=FakeLifeOs(),
            life_context_builder=builder,
            method_context_builder=CirculatioMethodContextBuilder(repository),
        )
        service = CirculatioService(repository, core, context_adapter=context_adapter)
        return repository, service, llm

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
            self.assertEqual(accepted["status"], "accepted")
            self.assertEqual(skipped["status"], "skipped")
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
            self.assertEqual(completed["status"], "completed")
            self.assertEqual(completed["id"], again["id"])
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
                }
            )
            records = await repository.list_individuation_records("user_1", limit=20)
            self.assertEqual(len(records), 3)
            self.assertEqual(anchors["recordType"], "reality_anchor_summary")
            self.assertEqual(anchors["status"], "user_confirmed")
            self.assertEqual(numinous["recordType"], "numinous_encounter")
            self.assertEqual(aesthetic["recordType"], "aesthetic_resonance")

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
            self.assertEqual(len(llm.review_calls), 1)
            self.assertTrue(llm.review_calls[0]["hermesMemoryContext"]["recentMaterialSummaries"])
            self.assertEqual(
                llm.review_calls[0]["methodContextSnapshot"]["recentBodyStates"][0]["bodyRegion"],
                "chest",
            )
            self.assertEqual(
                llm.review_calls[0]["methodContextSnapshot"]["activeGoals"][0]["id"], "goal_1"
            )
            self.assertTrue(
                summary["summary"]["userFacingResponse"].startswith("LLM weekly review:")
            )

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
                    "practice_container",
                    "analysis_packet",
                ],
            )
            self.assertEqual(await repository.list_weekly_reviews("user_1"), [])
            self.assertEqual(await repository.list_proactive_briefs("user_1"), [])
            self.assertEqual(await repository.list_practice_sessions("user_1"), [])
            self.assertIsNone(await repository.get_adaptation_profile("user_1"))
            self.assertEqual(len(llm.review_calls), 1)
            self.assertIn("methodContextSnapshot", llm.review_calls[0])
            self.assertTrue(llm.review_calls[0]["methodContextSnapshot"]["recentBodyStates"])
            self.assertTrue(llm.review_calls[0]["methodContextSnapshot"]["activeGoals"])

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


if __name__ == "__main__":
    unittest.main()
