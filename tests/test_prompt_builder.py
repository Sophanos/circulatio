from __future__ import annotations

import json
import os
import sys
import unittest

sys.path.insert(0, os.path.abspath("src"))

from circulatio.llm.prompt_builder import (
    build_alive_today_messages,
    build_analysis_packet_messages,
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
                    ],
                },
                "trustedAmplificationSources": [
                    {
                        "label": "Symbolonline",
                        "url": "https://symbolonline.eu/index.php?title=Hauptseite",
                        "kind": "symbol_reference",
                        "language": "de",
                    },
                    {
                        "label": "ARAS",
                        "url": "https://aras.org/",
                        "kind": "scholarly_reference",
                        "language": "en",
                    },
                ],
            }
        )
        payload = json.loads(messages[1]["content"])
        self.assertEqual(payload["trustedAmplificationSources"][0]["label"], "Symbolonline")
        self.assertEqual(
            payload["trustedAmplificationSources"][1]["url"],
            "https://aras.org/",
        )
        self.assertEqual(
            payload["methodContextSnapshot"]["activeCulturalFrames"][0]["label"],
            "Jungian amplification",
        )
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

    def test_analysis_packet_prompt_includes_typology_digest_only_for_typology_lens(self) -> None:
        messages = build_analysis_packet_messages(
            {
                "userId": "user_1",
                "windowStart": "2026-04-20T00:00:00Z",
                "windowEnd": "2026-04-21T00:00:00Z",
                "analyticLens": "typology_function_dynamics",
                "hermesMemoryContext": {
                    **_MEMORY_CONTEXT,
                    "typologyLensSummaries": [
                        {
                            "id": "typology_1",
                            "role": "dominant",
                            "function": "thinking",
                            "claim": "Reflection leads.",
                            "confidence": "medium",
                            "status": "candidate",
                            "evidenceIds": ["evidence_1"],
                            "counterevidenceIds": [],
                            "linkedMaterialIds": ["material_1"],
                            "userTestPrompt": "Does reflection lead first?",
                            "lastUpdated": "2026-04-20T09:00:00Z",
                        }
                    ],
                },
                "typologyEvidenceDigest": {
                    "status": "hypotheses_available",
                    "lensSummaries": [],
                    "foreground": {
                        "functions": ["thinking"],
                        "lensIds": ["typology_1"],
                        "evidenceIds": ["evidence_1"],
                        "linkedMaterialIds": ["material_1"],
                    },
                    "compensation": {
                        "functions": ["feeling"],
                        "lensIds": [],
                        "evidenceIds": [],
                        "linkedMaterialIds": [],
                    },
                    "background": {
                        "functions": [],
                        "lensIds": [],
                        "evidenceIds": [],
                        "linkedMaterialIds": [],
                    },
                    "supportingRefs": ["typology_1", "material_1"],
                    "counterevidenceIds": [],
                    "bodyStateIds": [],
                    "relationalSceneIds": [],
                    "practiceOutcomeIds": [],
                    "ambiguityNotes": [],
                    "evidencedLensCount": 1,
                    "feedbackSignalCount": 0,
                    "updatedAt": "2026-04-20T09:00:00Z",
                },
            }
        )
        payload = json.loads(messages[1]["content"])
        self.assertEqual(payload["analyticLens"], "typology_function_dynamics")
        self.assertIn("typologyEvidenceDigest", payload)
        self.assertIn("typologyLensSummaries", payload["symbolicMemory"])
        self.assertIn("typologyPolicy", payload["instructions"])
        self.assertIn("typologyRestraintPolicy", payload["instructions"])

        generic_payload = json.loads(
            build_analysis_packet_messages(
                {
                    "userId": "user_1",
                    "windowStart": "2026-04-20T00:00:00Z",
                    "windowEnd": "2026-04-21T00:00:00Z",
                    "hermesMemoryContext": _MEMORY_CONTEXT,
                }
            )[1]["content"]
        )
        self.assertEqual(generic_payload["analyticLens"], "generic")
        self.assertNotIn("typologyEvidenceDigest", generic_payload)
        self.assertNotIn("typologyLensSummaries", generic_payload["symbolicMemory"])

    def test_interpretation_schema_mentions_typology_assessment(self) -> None:
        messages = build_interpretation_messages(
            {
                "userId": "user_1",
                "materialType": "reflection",
                "materialText": "A charged image stayed after the meeting.",
                "hermesMemoryContext": _MEMORY_CONTEXT,
            }
        )
        self.assertIn("typologyAssessment", messages[0]["content"])


if __name__ == "__main__":
    unittest.main()
