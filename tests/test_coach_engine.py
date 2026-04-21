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


if __name__ == "__main__":
    unittest.main()
