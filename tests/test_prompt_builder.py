from __future__ import annotations

import json
import os
import sys
import unittest

sys.path.insert(0, os.path.abspath("src"))

from circulatio.llm.prompt_builder import (
    build_alive_today_messages,
    build_interpretation_messages,
    build_practice_messages,
)

_MEMORY_CONTEXT = {
    "recurringSymbols": [],
    "activeComplexCandidates": [],
    "recentMaterialSummaries": [],
    "recentInterpretationFeedback": [
        {
            "hypothesisId": "hyp_1",
            "runId": "run_1",
            "feedback": "rejected",
            "note": "Zu viel auf einmal.",
            "timestamp": "2026-04-21T08:00:00Z",
        }
    ],
    "practiceOutcomes": [],
    "culturalOriginPreferences": [],
    "suppressedHypotheses": [],
    "typologyLensSummaries": [],
    "recentTypologySignals": [],
}


class PromptBuilderTests(unittest.TestCase):
    def test_interpretation_prompt_uses_typed_hints_and_excludes_raw_feedback_notes(self) -> None:
        messages = build_interpretation_messages(
            {
                "userId": "user_1",
                "materialType": "reflection",
                "materialText": "A strong image stayed after the meeting.",
                "hermesMemoryContext": _MEMORY_CONTEXT,
                "communicationHints": {
                    "tone": "gentle",
                    "questioningStyle": "soma_first",
                    "symbolicDensity": "sparse",
                    "source": "explicit",
                },
                "interpretationHints": {
                    "depthPreference": "brief_pattern_notes",
                    "modalityBias": "body",
                    "source": "learned",
                },
                "practiceHints": {
                    "maxDurationMinutes": 5,
                    "preferredModalities": ["writing"],
                    "source": "mixed",
                    "maturity": "learning",
                },
            }
        )
        payload = json.loads(messages[1]["content"])
        self.assertEqual(payload["communicationHints"]["tone"], "gentle")
        self.assertEqual(payload["interpretationHints"]["depthPreference"], "brief_pattern_notes")
        self.assertEqual(payload["practiceHints"]["maxDurationMinutes"], 5)
        self.assertNotIn("recentInterpretationFeedback", payload["symbolicMemory"])
        self.assertNotIn("Zu viel auf einmal.", messages[1]["content"])

    def test_interpretation_prompt_surfaces_trusted_amplification_sources(self) -> None:
        messages = build_interpretation_messages(
            {
                "userId": "user_1",
                "materialType": "dream",
                "materialText": "A snake rose around a tree.",
                "hermesMemoryContext": _MEMORY_CONTEXT,
                "methodContextSnapshot": {
                    "windowStart": "2026-04-01T00:00:00Z",
                    "windowEnd": "2026-04-21T00:00:00Z",
                    "activeCulturalFrames": [
                        {
                            "id": "cultural_frame_1",
                            "label": "Jungian amplification",
                            "status": "enabled",
                        }
                    ]
                },
                "trustedAmplificationSources": [
                    {
                        "label": "Symbolonline",
                        "url": "https://symbolonline.eu/index.php?title=Hauptseite",
                        "kind": "symbol_reference",
                        "language": "de",
                    },
                    {
                        "label": "Carl Jung Depth Psychology",
                        "url": "https://carljungdepthpsychologysite.blog/",
                        "kind": "depth_psychology_archive",
                        "language": "en",
                    },
                ],
            }
        )
        payload = json.loads(messages[1]["content"])
        self.assertEqual(payload["trustedAmplificationSources"][0]["label"], "Symbolonline")
        self.assertEqual(
            payload["trustedAmplificationSources"][1]["url"],
            "https://carljungdepthpsychologysite.blog/",
        )
        self.assertEqual(payload["methodContextSnapshot"]["activeCulturalFrames"][0]["label"], "Jungian amplification")
        self.assertIn("Some amplification will resonate", payload["instructions"]["sourcePolicy"])

    def test_practice_prompt_changes_when_practice_hints_change(self) -> None:
        base = {
            "userId": "user_1",
            "windowStart": "2026-04-20T00:00:00Z",
            "windowEnd": "2026-04-21T00:00:00Z",
            "trigger": {"triggerType": "manual"},
            "hermesMemoryContext": _MEMORY_CONTEXT,
        }
        first = build_practice_messages(
            {
                **base,
                "practiceHints": {
                    "maxDurationMinutes": 5,
                    "source": "explicit",
                    "maturity": "learning",
                },
            }
        )[1]["content"]
        second = build_practice_messages(
            {
                **base,
                "practiceHints": {
                    "maxDurationMinutes": 12,
                    "preferredModalities": ["imaginal"],
                    "source": "learned",
                    "maturity": "mature",
                },
            }
        )[1]["content"]
        self.assertNotEqual(first, second)
        self.assertIn('"practiceHints"', first)
        self.assertNotIn('"adaptationHints"', first)

    def test_alive_today_prompt_includes_coach_state(self) -> None:
        messages = build_alive_today_messages(
            {
                "userId": "user_1",
                "windowStart": "2026-04-20T00:00:00Z",
                "windowEnd": "2026-04-21T00:00:00Z",
                "explicitQuestion": "What is alive today?",
                "hermesMemoryContext": _MEMORY_CONTEXT,
                "methodContextSnapshot": {
                    "windowStart": "2026-04-20T00:00:00Z",
                    "windowEnd": "2026-04-21T00:00:00Z",
                    "coachState": {
                        "surface": "alive_today",
                        "selectedMove": {
                            "kind": "ask_body_checkin",
                            "loopKey": "coach:soma:body_1",
                        },
                    },
                },
            }
        )
        payload = json.loads(messages[1]["content"])
        self.assertEqual(payload["methodContextSnapshot"]["coachState"]["surface"], "alive_today")
        self.assertEqual(
            payload["methodContextSnapshot"]["coachState"]["selectedMove"]["kind"],
            "ask_body_checkin",
        )


if __name__ == "__main__":
    unittest.main()
