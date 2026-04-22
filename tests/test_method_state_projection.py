from __future__ import annotations

import asyncio
import os
import sys
import unittest

sys.path.insert(0, os.path.abspath("src"))

from circulatio.core.circulatio_core import CirculatioCore
from circulatio.core.method_state_policy import derive_runtime_method_state_policy
from circulatio.repositories.in_memory_circulatio_repository import InMemoryCirculatioRepository


class MethodStateProjectionTests(unittest.TestCase):
    WINDOW_START = "2026-04-12T00:00:00Z"
    WINDOW_END = "2026-04-19T23:59:59Z"

    async def _build_snapshot(self, repository: InMemoryCirculatioRepository) -> dict[str, object]:
        snapshot = await repository.build_method_context_snapshot_from_records(
            "user_1",
            window_start=self.WINDOW_START,
            window_end=self.WINDOW_END,
        )
        self.assertIsNotNone(snapshot)
        assert snapshot is not None
        return snapshot

    def _reality_anchor_record(
        self,
        *,
        record_id: str,
        created_at: str,
        grounding: str,
        work: str = "stable",
        sleep: str = "stable",
        relationship: str = "available",
        reflective: str = "steady",
        summary: str = "Reality anchors remain visible.",
    ) -> dict[str, object]:
        return {
            "id": record_id,
            "userId": "user_1",
            "recordType": "reality_anchor_summary",
            "status": "user_confirmed",
            "source": "user_reported",
            "label": "Reality anchors",
            "summary": summary,
            "confidence": "high",
            "evidenceIds": [],
            "relatedMaterialIds": [],
            "relatedSymbolIds": [],
            "relatedGoalIds": [],
            "relatedDreamSeriesIds": [],
            "relatedJourneyIds": [],
            "relatedPracticeSessionIds": [],
            "privacyClass": "approved_summary",
            "createdAt": created_at,
            "updatedAt": created_at,
            "details": {
                "anchorSummary": summary,
                "workDailyLifeContinuity": work,
                "sleepBodyRegulation": sleep,
                "relationshipContact": relationship,
                "reflectiveCapacity": reflective,
                "groundingRecommendation": grounding,
                "reasons": ["Recent outer-life signals support this read."],
            },
        }

    def _body_state_record(
        self,
        *,
        record_id: str,
        created_at: str,
        activation: str,
    ) -> dict[str, object]:
        return {
            "id": record_id,
            "userId": "user_1",
            "source": "manual_body_note",
            "observedAt": created_at,
            "bodyRegion": "chest",
            "sensation": "tightness",
            "activation": activation,
            "tone": "charged",
            "linkedMaterialIds": [],
            "linkedSymbolIds": [],
            "linkedGoalIds": [],
            "evidenceIds": [],
            "privacyClass": "approved_summary",
            "status": "active",
            "createdAt": created_at,
            "updatedAt": created_at,
        }

    def _practice_session_record(
        self,
        *,
        record_id: str,
        created_at: str,
        status: str,
        modality: str,
        activation_before: str | None = None,
        activation_after: str | None = None,
        outcome_evidence_ids: list[str] | None = None,
    ) -> dict[str, object]:
        record: dict[str, object] = {
            "id": record_id,
            "userId": "user_1",
            "practiceType": "journaling",
            "reason": "Track what happens without forcing meaning.",
            "instructions": ["Write what is present."],
            "durationMinutes": 10,
            "contraindicationsChecked": ["none"],
            "requiresConsent": False,
            "status": status,
            "source": "manual",
            "modality": modality,
            "createdAt": created_at,
            "updatedAt": created_at,
        }
        if status == "completed":
            record["completedAt"] = created_at
        if activation_before is not None:
            record["activationBefore"] = activation_before
        if activation_after is not None:
            record["activationAfter"] = activation_after
        if outcome_evidence_ids is not None:
            record["outcomeEvidenceIds"] = list(outcome_evidence_ids)
        return record

    def _goal_tension_record(
        self,
        *,
        record_id: str,
        created_at: str,
        status: str,
        summary: str,
    ) -> dict[str, object]:
        return {
            "id": record_id,
            "userId": "user_1",
            "goalIds": ["goal_a", "goal_b"],
            "tensionSummary": summary,
            "polarityLabels": ["truth", "stability"],
            "evidenceIds": [],
            "status": status,
            "createdAt": created_at,
            "updatedAt": created_at,
        }

    def _relational_scene_record(
        self,
        *,
        record_id: str,
        created_at: str,
        affect: list[str],
    ) -> dict[str, object]:
        return {
            "id": record_id,
            "userId": "user_1",
            "recordType": "relational_scene",
            "status": "user_confirmed",
            "source": "user_reported",
            "label": "Relational scene",
            "summary": "A recurring relational scene is active.",
            "confidence": "medium",
            "evidenceIds": [],
            "relatedMaterialIds": [],
            "relatedSymbolIds": [],
            "relatedGoalIds": [],
            "relatedDreamSeriesIds": [],
            "relatedJourneyIds": [],
            "relatedPracticeSessionIds": [],
            "privacyClass": "approved_summary",
            "createdAt": created_at,
            "updatedAt": created_at,
            "details": {
                "sceneSummary": "Authority pressure returns whenever the user feels exposed.",
                "chargedRoles": [{"roleLabel": "authority", "affectTone": "pressure"}],
                "recurringAffect": affect,
                "recurrenceContexts": ["work"],
                "normalizedSceneKey": "authority-scene",
            },
        }

    def _wellbeing_record(
        self,
        *,
        record_id: str,
        created_at: str,
        grounding_capacity: str,
        relational_spaciousness: str,
        support_needed: str | None = None,
    ) -> dict[str, object]:
        details: dict[str, object] = {
            "capacitySummary": "Recent symbolic wellbeing gives a bounded signal.",
            "groundingCapacity": grounding_capacity,
            "symbolicLiveliness": "present",
            "somaticContact": "available",
            "relationalSpaciousness": relational_spaciousness,
            "agencyTone": "strained",
        }
        if support_needed:
            details["supportNeeded"] = support_needed
        return {
            "id": record_id,
            "userId": "user_1",
            "recordType": "symbolic_wellbeing_snapshot",
            "status": "active",
            "source": "user_reported",
            "label": "Symbolic wellbeing",
            "summary": "Symbolic wellbeing snapshot.",
            "confidence": "medium",
            "evidenceIds": [],
            "relatedMaterialIds": [],
            "relatedSymbolIds": [],
            "relatedGoalIds": [],
            "relatedDreamSeriesIds": [],
            "relatedIndividuationRecordIds": [],
            "privacyClass": "approved_summary",
            "createdAt": created_at,
            "updatedAt": created_at,
            "details": details,
        }

    def test_projection_splits_grounding_and_containment(self) -> None:
        async def run() -> None:
            repository = InMemoryCirculatioRepository()
            await repository.create_individuation_record(
                self._reality_anchor_record(
                    record_id="anchor_grounding",
                    created_at="2026-04-18T09:00:00Z",
                    grounding="grounding_first",
                    work="strained",
                    sleep="strained",
                    relationship="thin",
                    reflective="fragile",
                    summary="Outer life is too strained for symbolic depth right now.",
                )
            )
            await repository.create_body_state(
                self._body_state_record(
                    record_id="body_overwhelmed",
                    created_at="2026-04-18T09:10:00Z",
                    activation="overwhelming",
                )
            )
            await repository.create_living_myth_record(
                self._wellbeing_record(
                    record_id="wellbeing_strained",
                    created_at="2026-04-18T09:20:00Z",
                    grounding_capacity="strained",
                    relational_spaciousness="constricted",
                    support_needed="ordinary contact needs to lead",
                )
            )

            snapshot = await self._build_snapshot(repository)
            method_state = snapshot["methodState"]
            assert isinstance(method_state, dict)
            self.assertEqual(method_state["grounding"]["recommendation"], "grounding_first")
            self.assertEqual(method_state["containment"]["status"], "thin")
            self.assertNotIn("groundingNeed", method_state["containment"])

        asyncio.run(run())

    def test_ego_capacity_uses_derived_grounding_before_method_state_exists(self) -> None:
        async def run() -> None:
            repository = InMemoryCirculatioRepository()
            await repository.create_individuation_record(
                self._reality_anchor_record(
                    record_id="anchor_fragile",
                    created_at="2026-04-18T08:00:00Z",
                    grounding="grounding_first",
                    relationship="thin",
                    reflective="fragile",
                    summary="Grounding needs to lead before deeper symbolic work.",
                )
            )

            snapshot = await self._build_snapshot(repository)
            method_state = snapshot["methodState"]
            assert isinstance(method_state, dict)
            ego_capacity = method_state["egoCapacity"]
            self.assertEqual(ego_capacity["reflectiveCapacity"], "fragile")

        asyncio.run(run())

    def test_active_goal_tension_ranks_active_before_candidate(self) -> None:
        async def run() -> None:
            repository = InMemoryCirculatioRepository()
            await repository.create_goal_tension(
                self._goal_tension_record(
                    record_id="tension_candidate",
                    created_at="2026-04-19T10:00:00Z",
                    status="candidate",
                    summary="A candidate tension is visible but not yet primary.",
                )
            )
            await repository.create_goal_tension(
                self._goal_tension_record(
                    record_id="tension_active",
                    created_at="2026-04-18T10:00:00Z",
                    status="active",
                    summary="A live tension is shaping the present moment.",
                )
            )
            await repository.create_goal_tension(
                self._goal_tension_record(
                    record_id="tension_integrating",
                    created_at="2026-04-17T10:00:00Z",
                    status="integrating",
                    summary="A tension is already moving toward integration.",
                )
            )

            snapshot = await self._build_snapshot(repository)
            method_state = snapshot["methodState"]
            assert isinstance(method_state, dict)
            self.assertEqual(method_state["activeGoalTension"]["goalTensionId"], "tension_active")

        asyncio.run(run())

    def test_practice_loop_reconciles_explicit_learned_and_recent_signals(self) -> None:
        async def run() -> None:
            repository = InMemoryCirculatioRepository()
            await repository.upsert_adaptation_profile(
                "user_1",
                {
                    "id": "adaptation_1",
                    "userId": "user_1",
                    "explicitPreferences": {"practice": {"maxDurationMinutes": 6}},
                    "learnedSignals": {
                        "practicePolicy": {
                            "preferredModalities": ["movement"],
                            "avoidedModalities": ["breath"],
                        },
                        "practiceStats": {
                            "byModality": {
                                "imaginal": {"recommended": 4, "accepted": 2, "completed": 2},
                                "chanting": {"skipped": 3},
                            }
                        },
                    },
                    "sampleCounts": {"total": 22},
                    "createdAt": "2026-04-18T07:00:00Z",
                    "updatedAt": "2026-04-18T07:00:00Z",
                    "status": "active",
                },
            )
            await repository.create_practice_session(
                self._practice_session_record(
                    record_id="practice_completed",
                    created_at="2026-04-18T09:00:00Z",
                    status="completed",
                    modality="movement",
                    activation_before="moderate",
                    activation_after="high",
                )
            )
            await repository.create_practice_session(
                self._practice_session_record(
                    record_id="practice_skipped",
                    created_at="2026-04-18T10:00:00Z",
                    status="skipped",
                    modality="imaginal",
                )
            )

            snapshot = await self._build_snapshot(repository)
            method_state = snapshot["methodState"]
            assert isinstance(method_state, dict)
            practice_loop = method_state["practiceLoop"]
            self.assertEqual(practice_loop["maxDurationMinutes"], 6)
            self.assertIn("movement", practice_loop["preferredModalities"])
            self.assertIn("imaginal", practice_loop["preferredModalities"])
            self.assertIn("breath", practice_loop["avoidedModalities"])
            self.assertIn("chanting", practice_loop["avoidedModalities"])
            self.assertEqual(practice_loop["recentOutcomeTrend"], "activating")
            self.assertEqual(practice_loop["recommendedIntensity"], "low")

        asyncio.run(run())

    def test_practice_outcome_evidence_flows_into_grounding_summary(self) -> None:
        async def run() -> None:
            repository = InMemoryCirculatioRepository()
            await repository.create_practice_session(
                self._practice_session_record(
                    record_id="practice_evidence",
                    created_at="2026-04-18T09:00:00Z",
                    status="completed",
                    modality="movement",
                    activation_before="moderate",
                    activation_after="high",
                    outcome_evidence_ids=["evidence_practice_1"],
                )
            )

            snapshot = await self._build_snapshot(repository)
            method_state = snapshot["methodState"]
            assert isinstance(method_state, dict)
            grounding = method_state["grounding"]
            self.assertIn(
                "Recent practice outcomes increased activation.", grounding["strainSignals"]
            )
            self.assertIn("evidence_practice_1", grounding["evidenceIds"])

        asyncio.run(run())

    def test_relational_field_derives_isolation_from_existing_sources(self) -> None:
        async def run() -> None:
            repository = InMemoryCirculatioRepository()
            await repository.create_individuation_record(
                self._reality_anchor_record(
                    record_id="anchor_relational",
                    created_at="2026-04-18T08:00:00Z",
                    grounding="pace_gently",
                    relationship="thin",
                    summary="Relational contact is thin and space feels constricted.",
                )
            )
            await repository.create_individuation_record(
                self._relational_scene_record(
                    record_id="scene_authority",
                    created_at="2026-04-18T08:30:00Z",
                    affect=["pressure"],
                )
            )
            await repository.create_living_myth_record(
                self._wellbeing_record(
                    record_id="wellbeing_relational",
                    created_at="2026-04-18T08:45:00Z",
                    grounding_capacity="strained",
                    relational_spaciousness="constricted",
                    support_needed="ordinary contact needs more room",
                )
            )

            snapshot = await self._build_snapshot(repository)
            method_state = snapshot["methodState"]
            assert isinstance(method_state, dict)
            relational_field = method_state["relationalField"]
            self.assertEqual(relational_field["relationshipContact"], "thin")
            self.assertEqual(relational_field["isolationRisk"], "high")
            self.assertEqual(relational_field["supportDirection"], "increase_contact")
            self.assertIn("scene_authority", relational_field["activeSceneIds"])

        asyncio.run(run())

    def test_runtime_policy_fragile_capacity_only_softens_pacing(self) -> None:
        policy = derive_runtime_method_state_policy(
            {
                "windowStart": self.WINDOW_START,
                "windowEnd": self.WINDOW_END,
                "source": "circulatio-backend",
                "methodState": {
                    "grounding": {"recommendation": "clear_for_depth"},
                    "containment": {"status": "steady"},
                    "egoCapacity": {"reflectiveCapacity": "fragile"},
                },
            }
        )
        self.assertEqual(policy["depthLevel"], "gentle")
        self.assertEqual(policy["maxClarifyingQuestions"], 1)
        self.assertNotEqual(policy["depthLevel"], "grounding_only")
        self.assertNotIn("requireGroundingCompatible", policy["practiceConstraints"])

    def test_generate_practice_uses_canonical_goal_tension_and_practice_loop(self) -> None:
        async def run() -> None:
            repository = InMemoryCirculatioRepository()
            core = CirculatioCore(repository, llm=None)
            result = await core.generate_practice(
                {
                    "userId": "user_1",
                    "windowStart": self.WINDOW_START,
                    "windowEnd": self.WINDOW_END,
                    "trigger": {"triggerType": "manual"},
                    "methodContextSnapshot": {
                        "windowStart": self.WINDOW_START,
                        "windowEnd": self.WINDOW_END,
                        "source": "circulatio-backend",
                        "goalTensions": [
                            {
                                "id": "raw_tension",
                                "goalIds": ["goal_a", "goal_b"],
                                "tensionSummary": "A raw fallback tension should not be selected.",
                                "polarityLabels": ["truth", "safety"],
                                "evidenceIds": [],
                                "status": "active",
                                "createdAt": "2026-04-18T06:00:00Z",
                                "updatedAt": "2026-04-18T06:00:00Z",
                            }
                        ],
                        "adaptationProfile": {
                            "id": "adaptation_conflict",
                            "explicitPreferences": {
                                "practice": {
                                    "maxDurationMinutes": 12,
                                    "preferredModalities": ["imaginal"],
                                }
                            },
                            "learnedSignals": {},
                            "sampleCounts": {"total": 1},
                        },
                        "methodState": {
                            "grounding": {"recommendation": "clear_for_depth"},
                            "containment": {"status": "steady"},
                            "activeGoalTension": {
                                "goalTensionId": "canonical_tension",
                                "linkedGoalIds": ["goal_a", "goal_b"],
                                "summary": "A canonical active tension remains in play.",
                                "polarityLabels": ["truth", "stability"],
                                "balancingDirection": (
                                    "Hold truth and stability together before choosing a side."
                                ),
                                "evidenceIds": [],
                                "updatedAt": "2026-04-18T09:00:00Z",
                            },
                            "practiceLoop": {
                                "preferredModalities": ["writing"],
                                "avoidedModalities": ["imaginal"],
                                "recentCompletedTypes": [],
                                "recentSkippedTypes": [],
                                "recentOutcomeTrend": "unknown",
                                "recommendedIntensity": "moderate",
                                "maxDurationMinutes": 5,
                                "reasons": ["Canonical practice-loop constraints are available."],
                                "source": "mixed",
                                "updatedAt": "2026-04-18T09:00:00Z",
                            },
                        },
                    },
                }
            )
            practice = result["practiceRecommendation"]
            self.assertEqual(practice["targetedTensionId"], "canonical_tension")
            self.assertEqual(practice["durationMinutes"], 5)

        asyncio.run(run())

    def test_answer_only_unrouted_clarification_does_not_count_as_friction(self) -> None:
        async def run() -> None:
            repository = InMemoryCirculatioRepository()
            await repository.create_clarification_prompt(
                {
                    "id": "clarification_prompt_fallback",
                    "userId": "user_1",
                    "materialId": "material_1",
                    "runId": "run_1",
                    "questionText": "What image feels most alive right now?",
                    "questionKey": "fallback_image",
                    "intent": "personal_association",
                    "captureTarget": "answer_only",
                    "expectedAnswerKind": "free_text",
                    "status": "answered_unrouted",
                    "privacyClass": "session_only",
                    "createdAt": "2026-04-18T08:00:00Z",
                    "updatedAt": "2026-04-18T08:05:00Z",
                    "answeredAt": "2026-04-18T08:05:00Z",
                    "answerRecordId": "clarification_answer_fallback",
                }
            )
            await repository.create_clarification_answer(
                {
                    "id": "clarification_answer_fallback",
                    "userId": "user_1",
                    "promptId": "clarification_prompt_fallback",
                    "materialId": "material_1",
                    "runId": "run_1",
                    "answerText": "The door frame keeps carrying the charge.",
                    "captureTarget": "answer_only",
                    "routingStatus": "unrouted",
                    "createdRecordRefs": [],
                    "privacyClass": "session_only",
                    "createdAt": "2026-04-18T08:05:00Z",
                    "updatedAt": "2026-04-18T08:05:00Z",
                }
            )
            snapshot = await self._build_snapshot(repository)
            clarification_state = snapshot.get("clarificationState")
            self.assertIsNotNone(clarification_state)
            assert clarification_state is not None
            self.assertEqual(clarification_state["recentlyUnrouted"], [])
            self.assertIn("fallback_image", clarification_state["avoidRepeatQuestionKeys"])

        asyncio.run(run())


if __name__ == "__main__":
    unittest.main()
