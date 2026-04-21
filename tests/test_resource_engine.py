from __future__ import annotations

import os
import sys
import unittest

sys.path.insert(0, os.path.abspath("src"))

from circulatio.core.resource_catalog import CATALOG
from circulatio.core.resource_engine import ResourceEngine


class ResourceEngineTests(unittest.TestCase):
    def test_select_resource_for_grounding_loop_returns_curated_invitation(self) -> None:
        engine = ResourceEngine()
        loop = {
            "loopKey": "coach:soma:body_1",
            "kind": "soma",
            "moveKind": "offer_resource",
            "summaryHint": "Containment suggests a gentler grounding resource.",
            "capture": {
                "source": "body_note",
                "anchorRefs": {"coachLoopKey": "coach:soma:body_1"},
                "expectedTargets": ["body_state"],
                "maxQuestions": 1,
                "answerMode": "choice_then_free_text",
                "skipBehavior": "track_only",
            },
            "blockedMoves": [],
        }
        coach_state = {
            "globalConstraints": {"depthLevel": "grounding_only"},
            "witness": {},
        }

        invitation = engine.select_resource_for_loop(
            loop=loop,
            coach_state=coach_state,
            runtime_policy={"depthLevel": "grounding_only"},
            safety_context=None,
            now="2026-04-21T00:00:00Z",
        )

        self.assertIsNotNone(invitation)
        self.assertEqual(invitation["triggerLoopKey"], "coach:soma:body_1")
        self.assertIn(
            invitation["resource"]["modality"],
            {"grounding", "breath", "body_scan", "somatic_tracking"},
        )

    def test_resource_allowed_blocks_non_grounding_modalities_in_grounding_only(self) -> None:
        engine = ResourceEngine()
        journaling = next(item for item in CATALOG if item["modality"] == "journaling")
        allowed = engine.resource_allowed(
            resource=journaling,
            loop={"blockedMoves": []},
            runtime_policy={"depthLevel": "grounding_only"},
            consent_preferences=[],
        )
        self.assertFalse(allowed)


if __name__ == "__main__":
    unittest.main()
