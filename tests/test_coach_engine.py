from __future__ import annotations

import os
import sys
import unittest

sys.path.insert(0, os.path.abspath("src"))

from circulatio.core.coach_engine import CoachEngine


class CoachEngineTests(unittest.TestCase):
    def test_alive_today_prefers_soma_resource_when_grounding_is_thin(self) -> None:
        engine = CoachEngine()
        method_context = {
            "windowStart": "2026-04-20T00:00:00Z",
            "windowEnd": "2026-04-21T00:00:00Z",
            "recentBodyStates": [
                {
                    "id": "body_1",
                    "sensation": "tightness",
                    "bodyRegion": "chest",
                    "linkedGoalIds": ["goal_1"],
                }
            ],
            "activeJourneys": [],
            "recentPracticeSessions": [],
            "methodState": {
                "generatedAt": "2026-04-21T00:00:00Z",
                "containment": {"groundingNeed": "grounding_first"},
                "activeGoalTension": {
                    "goalTensionId": "tension_1",
                    "linkedGoalIds": ["goal_1"],
                },
                "practiceLoop": {"recentOutcomeTrend": "activating"},
            },
        }
        runtime_policy = {
            "depthLevel": "grounding_only",
            "blockedMoves": ["projection_language"],
            "preferredMoves": ["grounding"],
            "preferredClarificationTargets": ["body_state"],
            "questionStyle": "body_first",
            "witnessTone": "grounded",
            "maxClarifyingQuestions": 1,
            "practiceConstraints": {"preferLowIntensity": True},
            "reasons": ["Containment currently requires grounding first."],
        }

        coach_state = engine.build_coach_state(
            method_context=method_context,
            runtime_policy=runtime_policy,
            surface="alive_today",
            existing_briefs=[],
            recent_practices=[],
            journeys=[],
            now="2026-04-21T00:00:00Z",
        )

        self.assertEqual(coach_state["surface"], "alive_today")
        self.assertTrue(coach_state["activeLoops"])
        self.assertEqual(coach_state["selectedMove"]["kind"], "offer_resource")
        self.assertEqual(
            coach_state["selectedMove"]["capture"]["expectedTargets"][0],
            "body_state",
        )

    def test_generic_surface_prefers_practice_integration_before_resource_support(self) -> None:
        engine = CoachEngine()
        coach_state = engine.build_coach_state(
            method_context={
                "windowStart": "2026-04-20T00:00:00Z",
                "windowEnd": "2026-04-21T00:00:00Z",
                "recentBodyStates": [],
                "activeJourneys": [],
                "recentPracticeSessions": [],
                "methodState": {
                    "grounding": {"recommendation": "grounding_first"},
                    "containment": {"status": "strained"},
                    "practiceLoop": {"recentOutcomeTrend": "activating"},
                },
            },
            runtime_policy={
                "depthLevel": "grounding_only",
                "blockedMoves": [],
                "preferredMoves": [],
                "preferredClarificationTargets": ["practice_outcome"],
                "questionStyle": "body_first",
                "witnessTone": "grounded",
                "maxClarifyingQuestions": 1,
                "practiceConstraints": {"preferLowIntensity": True},
                "reasons": ["Containment currently requires grounding first."],
            },
            surface="generic",
            existing_briefs=[],
            recent_practices=[
                {
                    "id": "practice_1",
                    "userId": "user_1",
                    "practiceType": "journaling",
                    "reason": "Track the pattern.",
                    "instructions": ["Write for five minutes."],
                    "durationMinutes": 8,
                    "contraindicationsChecked": ["none"],
                    "requiresConsent": False,
                    "status": "completed",
                    "activationBefore": "low",
                    "activationAfter": "high",
                    "createdAt": "2026-04-20T10:00:00Z",
                    "updatedAt": "2026-04-20T10:05:00Z",
                }
            ],
            journeys=[],
            now="2026-04-21T00:00:00Z",
        )

        self.assertEqual(
            coach_state["selectedMove"]["loopKey"],
            "coach:practice_integration:practice_1",
        )

    def test_followthrough_summary_can_make_soma_loop_dominant(self) -> None:
        engine = CoachEngine()
        coach_state = engine.build_coach_state(
            method_context={
                "windowStart": "2026-04-20T00:00:00Z",
                "windowEnd": "2026-04-21T00:00:00Z",
                "recentBodyStates": [
                    {
                        "id": "body_1",
                        "sensation": "tightness",
                        "bodyRegion": "chest",
                        "activation": "high",
                    }
                ],
                "activeJourneys": [
                    {
                        "id": "journey_1",
                        "label": "Embodied thread",
                        "status": "active",
                        "relatedGoalIds": [],
                        "relatedSymbolIds": [],
                        "relatedBodyStateIds": ["body_1"],
                    }
                ],
                "goalTensions": [],
                "recentPracticeSessions": [],
                "methodState": {},
            },
            runtime_policy={
                "depthLevel": "clear_for_depth",
                "blockedMoves": [],
                "preferredMoves": [],
                "preferredClarificationTargets": ["body_state"],
                "questionStyle": "body_first",
                "witnessTone": "grounded",
                "maxClarifyingQuestions": 1,
                "practiceConstraints": {"preferLowIntensity": True},
                "reasons": [],
            },
            surface="generic",
            existing_briefs=[],
            recent_practices=[],
            journeys=[
                {
                    "id": "journey_1",
                    "userId": "user_1",
                    "label": "Embodied thread",
                    "status": "active",
                    "relatedMaterialIds": [],
                    "relatedSymbolIds": [],
                    "relatedPatternIds": [],
                    "relatedDreamSeriesIds": [],
                    "relatedGoalIds": [],
                    "relatedBodyStateIds": ["body_1"],
                    "createdAt": "2026-04-20T00:00:00Z",
                    "updatedAt": "2026-04-20T00:00:00Z",
                }
            ],
            journey_followthrough=[
                {
                    "journeyId": "journey_1",
                    "family": "embodied_recurrence",
                    "readiness": "ready",
                    "recommendedSurface": "alive_today",
                    "recommendedMoveKind": "ask_body_checkin",
                    "bodyFirst": True,
                    "priority": 80,
                    "reasons": ["journey_embodied_recurrence_active"],
                    "blockedEscalations": ["diagnostic_or_causal_framing"],
                    "relatedPracticeSessionIds": [],
                    "relatedBodyStateIds": ["body_1"],
                    "relatedGoalTensionIds": [],
                    "lastTouchedAt": "2026-04-20T12:00:00Z",
                }
            ],
            now="2026-04-21T00:00:00Z",
        )

        self.assertEqual(coach_state["selectedMove"]["kind"], "ask_body_checkin")
        selected_loop = next(
            loop
            for loop in coach_state["activeLoops"]
            if loop["loopKey"] == coach_state["selectedMove"]["loopKey"]
        )
        self.assertEqual(selected_loop["kind"], "soma")
        self.assertIn("journey_1", selected_loop["relatedJourneyIds"])
        self.assertIn("journey_followthrough_dominant", selected_loop["reasons"])
        self.assertFalse(
            any(
                loop["loopKey"] == "coach:journey_reentry:journey_1"
                for loop in coach_state["activeLoops"]
            )
        )


if __name__ == "__main__":
    unittest.main()
