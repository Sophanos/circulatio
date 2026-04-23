from __future__ import annotations

import os
import sys
import unittest

sys.path.insert(0, os.path.abspath("src"))

from circulatio.core.practice_engine import PracticeEngine


class PracticeEngineTests(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = PracticeEngine()

    def test_consent_fallback(self) -> None:
        result = self.engine.reconcile_llm_practice(
            practice={
                "id": "practice_1",
                "type": "active_imagination",
                "reason": "Stay with the image.",
                "instructions": ["Return to the image."],
                "durationMinutes": 12,
                "contraindicationsChecked": ["none"],
                "requiresConsent": True,
            },
            safety={"status": "clear", "flags": ["none"], "depthWorkAllowed": True},
            method_gate=None,
            depth_readiness=None,
            consent_preferences=[{"scope": "active_imagination", "status": "revoked"}],
        )
        self.assertEqual(result["type"], "journaling")
        self.assertIn(
            "active_imagination_blocked_by_consent_fallback_to_journaling",
            result["adaptationNotes"],
        )

    def test_method_gate_fallback(self) -> None:
        result = self.engine.reconcile_llm_practice(
            practice={
                "id": "practice_1",
                "type": "active_imagination",
                "reason": "Stay with the image.",
                "instructions": ["Return to the image."],
                "durationMinutes": 12,
                "contraindicationsChecked": ["none"],
                "requiresConsent": True,
                "relatedExperimentIds": ["experiment_1"],
            },
            safety={"status": "clear", "flags": ["none"], "depthWorkAllowed": True},
            method_gate={"blockedMoves": ["active_imagination"]},
            depth_readiness={"allowedMoves": {"active_imagination": "withhold"}},
            consent_preferences=[],
        )
        self.assertEqual(result["type"], "journaling")
        self.assertEqual(result["relatedExperimentIds"], ["experiment_1"])

    def test_consent_fallback_precedes_method_block_for_active_imagination(self) -> None:
        result = self.engine.reconcile_llm_practice(
            practice={
                "id": "practice_1",
                "type": "active_imagination",
                "reason": "Stay with the image.",
                "instructions": ["Return to the image."],
                "durationMinutes": 12,
                "contraindicationsChecked": ["none"],
                "requiresConsent": True,
                "relatedExperimentIds": ["experiment_1"],
            },
            safety={"status": "clear", "flags": ["none"], "depthWorkAllowed": True},
            method_gate={"blockedMoves": ["active_imagination"]},
            depth_readiness={"allowedMoves": {"active_imagination": "withhold"}},
            consent_preferences=[{"scope": "active_imagination", "status": "revoked"}],
        )
        self.assertEqual(result["type"], "journaling")
        self.assertIn(
            "active_imagination_blocked_by_consent_fallback_to_journaling",
            result["adaptationNotes"],
        )
        self.assertNotIn(
            "active_imagination_blocked_by_method_fallback_to_journaling",
            result["adaptationNotes"],
        )
        self.assertEqual(result["relatedExperimentIds"], ["experiment_1"])

    def test_explicit_duration_cap(self) -> None:
        result = self.engine.reconcile_llm_practice(
            practice={
                "id": "practice_1",
                "type": "journaling",
                "reason": "Write it down.",
                "instructions": ["Write what is present."],
                "durationMinutes": 15,
                "contraindicationsChecked": ["none"],
                "requiresConsent": False,
            },
            safety={"status": "clear", "flags": ["none"], "depthWorkAllowed": True},
            method_gate=None,
            depth_readiness=None,
            consent_preferences=[],
            adaptation_hints={"maturity": "learning", "maxDurationMinutes": 8},
        )
        self.assertEqual(result["durationMinutes"], 8)

    def test_practice_hints_override_legacy_adaptation_hints(self) -> None:
        result = self.engine.reconcile_llm_practice(
            practice={
                "id": "practice_1",
                "type": "journaling",
                "reason": "Write it down.",
                "instructions": ["Write what is present."],
                "durationMinutes": 15,
                "contraindicationsChecked": ["none"],
                "requiresConsent": False,
            },
            safety={"status": "clear", "flags": ["none"], "depthWorkAllowed": True},
            method_gate=None,
            depth_readiness=None,
            consent_preferences=[],
            practice_hints={"maturity": "learning", "maxDurationMinutes": 6},
            adaptation_hints={"maturity": "learning", "maxDurationMinutes": 12},
        )
        self.assertEqual(result["durationMinutes"], 6)

    def test_practice_engine_annotates_targeted_tension(self) -> None:
        result = self.engine.reconcile_llm_practice(
            practice={
                "id": "practice_1",
                "type": "journaling",
                "reason": "Write what is active.",
                "instructions": ["Write what is active."],
                "durationMinutes": 10,
                "contraindicationsChecked": ["none"],
                "requiresConsent": False,
            },
            safety={"status": "clear", "flags": ["none"], "depthWorkAllowed": True},
            method_gate=None,
            depth_readiness=None,
            consent_preferences=[],
            goal_tensions=[
                {
                    "id": "tension_1",
                    "tensionSummary": "Directness and safety pull against each other.",
                }
            ],
            body_states=[{"id": "body_1", "sensation": "tightness"}],
        )
        self.assertEqual(result["targetedTensionId"], "tension_1")
        self.assertEqual(result["targetedBodyStateId"], "body_1")

    def test_learned_preferences_remain_soft_before_threshold(self) -> None:
        result = self.engine.build_adaptation_hints(
            profile={
                "id": "adaptation_1",
                "userId": "user_1",
                "explicitPreferences": {},
                "learnedSignals": {
                    "practiceStats": {"byModality": {"imaginal": {"recommended": 4}}}
                },
                "sampleCounts": {"total": 10},
                "createdAt": "2026-04-12T00:00:00Z",
                "updatedAt": "2026-04-12T00:00:00Z",
                "status": "active",
            }
        )
        self.assertEqual(result["maturity"], "learning")
        self.assertNotIn("maxDurationMinutes", result)

    def test_activation_delta_classification(self) -> None:
        event = self.engine.summarize_outcome_signal(
            practice={
                "id": "practice_1",
                "userId": "user_1",
                "practiceType": "journaling",
                "reason": "Write it down.",
                "instructions": ["Write what is present."],
                "durationMinutes": 5,
                "contraindicationsChecked": ["none"],
                "requiresConsent": False,
                "status": "completed",
            },
            previous_status="accepted",
            outcome={
                "practiceType": "journaling",
                "outcome": "The image softened.",
                "activationBefore": "high",
                "activationAfter": "moderate",
            },
            action="completed",
        )
        self.assertTrue(event["signals"]["activationImproved"])
        self.assertFalse(event["signals"]["activationWorsened"])

    def test_review_and_packet_triggers_keep_non_manual_source(self) -> None:
        for trigger_type in ("threshold_review", "living_myth_review", "analysis_packet"):
            defaults = self.engine.derive_lifecycle_defaults(
                practice={
                    "id": "practice_1",
                    "type": "journaling",
                    "reason": "Write what is present.",
                    "instructions": ["Write what is present."],
                    "durationMinutes": 5,
                    "contraindicationsChecked": ["none"],
                    "requiresConsent": False,
                },
                created_at="2026-04-18T08:00:00Z",
                trigger={"triggerType": trigger_type},
            )
            self.assertEqual(defaults["source"], trigger_type)

    def test_method_state_frame_copies_related_experiment_ids_from_selected_move(self) -> None:
        result = self.engine.reconcile_llm_practice(
            practice={
                "id": "practice_1",
                "type": "journaling",
                "reason": "Write what is present.",
                "instructions": ["Write what is present."],
                "durationMinutes": 10,
                "contraindicationsChecked": ["none"],
                "requiresConsent": False,
            },
            safety={"status": "clear", "flags": ["none"], "depthWorkAllowed": True},
            method_gate=None,
            depth_readiness=None,
            consent_preferences=[],
            method_context={
                "coachState": {
                    "selectedMove": {
                        "relatedExperimentIds": ["experiment_1"],
                    }
                }
            },
            runtime_policy={},
        )
        self.assertEqual(result["relatedExperimentIds"], ["experiment_1"])


if __name__ == "__main__":
    unittest.main()
