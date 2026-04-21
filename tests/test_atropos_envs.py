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
from circulatio.domain.ids import create_id
from circulatio.hermes.atropos_envs import (
    build_circulatio_communication_env,
    build_circulatio_practice_env,
    score_circulatio_communication_reward,
    score_circulatio_practice_reward,
)
from circulatio.repositories.in_memory_circulatio_repository import InMemoryCirculatioRepository
from tests._helpers import FakeCirculatioLlm


class AtroposEnvTests(unittest.TestCase):
    def _service(self) -> tuple[InMemoryCirculatioRepository, CirculatioService]:
        repository = InMemoryCirculatioRepository()
        llm = FakeCirculatioLlm()
        core = CirculatioCore(repository, llm=llm)
        context_adapter = ContextAdapter(
            repository,
            life_context_builder=CirculatioLifeContextBuilder(repository),
            method_context_builder=CirculatioMethodContextBuilder(repository),
        )
        service = CirculatioService(
            repository,
            core,
            context_adapter=context_adapter,
            method_state_llm=llm,
        )
        return repository, service

    def test_communication_env_state_is_bounded(self) -> None:
        async def run() -> None:
            repository, service = self._service()
            await service.set_adaptation_preferences(
                user_id="user_1",
                scope="communication",
                preferences={"tone": "gentle"},
            )
            await service.set_adaptation_preferences(
                user_id="user_1",
                scope="interpretation",
                preferences={"depthPreference": "brief_pattern_notes"},
            )
            await service.apply_learned_policy_update(
                user_id="user_1",
                scope="communication",
                policy={"questioningStyle": "soma_first"},
            )

            target_run_id = ""
            target_material_id = ""
            target_hypothesis_id = ""
            for index in range(12):
                workflow = await service.create_and_interpret_material(
                    {
                        "userId": "user_1",
                        "materialType": "reflection",
                        "text": (
                            "I walked through a house and found a snake image returning "
                            f"after the conflict {index}."
                        ),
                    }
                )
                if index == 11:
                    target_run_id = workflow["run"]["id"]
                    target_material_id = workflow["material"]["id"]
                    target_hypothesis_id = workflow["interpretation"]["hypotheses"][0]["id"]
                    await service.approve_proposals(
                        user_id="user_1",
                        run_id=target_run_id,
                        proposal_ids=[workflow["pendingProposals"][0]["id"]],
                    )
                    await repository.create_material(
                        {
                            "id": create_id("material"),
                            "userId": "user_1",
                            "materialType": "reflection",
                            "text": "Follow-up response.",
                            "title": "Follow-up",
                            "summary": "Follow-up",
                            "privacyClass": "user_private",
                            "tags": [],
                            "status": "active",
                            "createdAt": "2026-04-21T09:00:00Z",
                            "updatedAt": "2026-04-21T09:00:00Z",
                        }
                    )
                    await repository.create_method_state_capture_run(
                        {
                            "id": create_id("method_state_capture"),
                            "userId": "user_1",
                            "idempotencyKey": "capture_1",
                            "source": "clarifying_answer",
                            "status": "completed",
                            "anchorRefs": {
                                "runId": target_run_id,
                                "materialId": target_material_id,
                            },
                            "responseMaterialId": target_material_id,
                            "evidenceIds": [],
                            "expectedTargets": ["body_state"],
                            "extractionResult": {},
                            "appliedEntityRefs": [],
                            "memoryWritePlan": {
                                "runId": target_run_id,
                                "proposals": [],
                                "evidenceItems": [],
                            },
                            "proposalDecisions": [],
                            "createdAt": "2026-04-21T09:05:00Z",
                            "updatedAt": "2026-04-21T09:05:00Z",
                        }
                    )
                    await service.reject_hypotheses(
                        user_id="user_1",
                        run_id=target_run_id,
                        feedback_by_hypothesis_id={
                            target_hypothesis_id: {
                                "feedback": "partially_refined",
                                "note": "Closer, but still too abstract.",
                            }
                        },
                    )
                    await service.record_interpretation_feedback(
                        "user_1",
                        target_run_id,
                        "too_abstract",
                        note="Zu abstrakt.",
                        locale="de-DE",
                    )

            env = await build_circulatio_communication_env(repository, user_id="user_1")
            outcomes = env["state"]["recentInterpretationOutcomes"]
            self.assertEqual(len(outcomes), 10)
            self.assertTrue(any(item["followUpAnswered"] for item in outcomes))
            self.assertTrue(any(item["hypothesisRefinedCount"] > 0 for item in outcomes))
            self.assertEqual(
                env["state"]["explicitCommunicationPreferences"]["tone"],
                "gentle",
            )
            self.assertEqual(
                env["state"]["learnedCommunicationPolicy"]["questioningStyle"],
                "soma_first",
            )

        asyncio.run(run())

    def test_practice_env_state_is_bounded(self) -> None:
        async def run() -> None:
            repository, service = self._service()
            await service.set_adaptation_preferences(
                user_id="user_1",
                scope="practice",
                preferences={"maxDurationMinutes": 6, "preferredModalities": ["writing"]},
            )
            await service.apply_learned_policy_update(
                user_id="user_1",
                scope="practice",
                policy={"avoidedModalities": ["imaginal"]},
            )
            first_practice_id = ""
            for index in range(12):
                workflow = await service.generate_practice_recommendation({"userId": "user_1"})
                if index == 0:
                    first_practice_id = workflow["practiceSession"]["id"]
                    await service.record_practice_feedback(
                        "user_1",
                        first_practice_id,
                        "good_fit",
                        note="Buen ritmo.",
                        locale="es-ES",
                    )
            env = await build_circulatio_practice_env(repository, user_id="user_1")
            self.assertEqual(len(env["state"]["recentPracticeOutcomes"]), 10)
            self.assertEqual(
                env["state"]["explicitPracticePreferences"]["maxDurationMinutes"],
                6,
            )
            self.assertEqual(
                env["state"]["learnedPracticePolicy"]["avoidedModalities"],
                ["imaginal"],
            )
            self.assertEqual(
                env["state"]["recentExplicitPracticeFeedback"][0]["locale"],
                "es-ES",
            )

        asyncio.run(run())

    def test_reward_scoring_uses_explicit_and_implicit_signals(self) -> None:
        communication = score_circulatio_communication_reward(
            explicit_feedback_events=[{"feedback": "helpful"}],
            implicit_signals={"proposalApprovedCount": 2, "clarifyingFollowUpAnswered": True},
        )
        practice = score_circulatio_practice_reward(
            explicit_feedback_events=[{"feedback": "good_fit"}],
            implicit_signals={"practiceCompletedCount": 1, "activationImprovedCount": 1},
        )
        self.assertGreater(communication["reward"], 0)
        self.assertGreater(practice["reward"], 0)

    def test_reward_scoring_applies_hard_penalties(self) -> None:
        communication = score_circulatio_communication_reward(
            explicit_feedback_events=[{"feedback": "helpful"}],
            hard_negative_flags=["projection_stated_as_fact", "safety_violation"],
        )
        practice = score_circulatio_practice_reward(
            explicit_feedback_events=[{"feedback": "good_fit"}],
            hard_negative_flags=["consent_blocked_practice"],
        )
        self.assertTrue(communication["hardNegative"])
        self.assertLess(communication["reward"], 0)
        self.assertTrue(practice["hardNegative"])
        self.assertLess(practice["reward"], 0)


if __name__ == "__main__":
    unittest.main()
