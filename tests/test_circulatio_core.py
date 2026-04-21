from __future__ import annotations

import asyncio
import os
import sys
import unittest

sys.path.insert(0, os.path.abspath("src"))

from circulatio.adapters.context_adapter import ContextAdapter
from circulatio.core.circulatio_core import CirculatioCore
from circulatio.domain.ids import normalize_claim_key
from circulatio.repositories.in_memory_graph_memory_repository import InMemoryGraphMemoryRepository
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
            "focusSummary": "Focus lower than usual this week",
            "notableChanges": ["more evening restlessness"],
            "source": "hermes-life-os",
            "rawMoodLog": ["bad"],
            "sleepEntries": [1, 2, 3],
        }


class NarrativeOnlyLlm:
    async def interpret_material(self, input_data: dict[str, object]) -> dict[str, object]:
        del input_data
        return {
            "symbolMentions": [],
            "figureMentions": [],
            "motifMentions": [],
            "lifeContextLinks": [],
            "observations": [],
            "hypotheses": [],
            "practiceRecommendation": {},
            "proposalCandidates": [],
            "userFacingResponse": "A fluent but unstructured symbolic reading.",
            "clarifyingQuestion": "",
        }

    async def generate_practice(self, input_data: dict[str, object]) -> dict[str, object]:
        del input_data
        return {"practiceRecommendation": {}, "userFacingResponse": ""}

    async def generate_rhythmic_brief(self, input_data: dict[str, object]) -> dict[str, object]:
        del input_data
        return {"title": "", "summary": "", "userFacingResponse": ""}


class CirculatioCoreTests(unittest.TestCase):
    def test_llm_interpretation_is_side_effect_free_until_record_integration(self) -> None:
        async def run() -> None:
            repo = InMemoryGraphMemoryRepository()
            llm = FakeCirculatioLlm()
            core = CirculatioCore(repo, llm=llm)
            before = await repo.get_hermes_memory_context("user_1")
            result = await core.interpret_dream(
                {
                    "userId": "user_1",
                    "materialText": "I was in a house and found a snake under the stairs.",
                    "lifeContextSnapshot": {
                        "windowStart": "2026-04-12T00:00:00Z",
                        "windowEnd": "2026-04-19T00:00:00Z",
                        "lifeEventRefs": [
                            {
                                "id": "life_event_1",
                                "summary": "Repeated conflict with manager",
                                "symbolicAnnotation": "authority conflict",
                            }
                        ],
                        "focusSummary": "Focus lower than usual this week",
                        "source": "hermes-life-os",
                    },
                }
            )
            after = await repo.get_hermes_memory_context("user_1")
            self.assertTrue(result["symbolMentions"])
            self.assertTrue(result["memoryWritePlan"]["proposals"])
            self.assertTrue(result["userFacingResponse"].startswith("LLM interpretation:"))
            self.assertEqual(result["llmInterpretationHealth"]["status"], "structured")
            self.assertEqual(before, after)
            self.assertEqual(len(llm.interpret_calls), 1)

        asyncio.run(run())

    def test_suppressed_hypothesis_filters_llm_output(self) -> None:
        async def run() -> None:
            repo = InMemoryGraphMemoryRepository()
            llm = FakeCirculatioLlm()
            core = CirculatioCore(repo, llm=llm)
            claim = "One possible pattern is that the snake image carries a recurring tension rather than a one-off detail."
            normalized = normalize_claim_key("theme", claim)
            await repo.suppress_hypothesis(
                {
                    "userId": "user_1",
                    "hypothesisId": "hyp_1",
                    "normalizedClaimKey": normalized,
                    "reason": "user_rejected",
                }
            )
            result = await core.interpret_material(
                {
                    "userId": "user_1",
                    "materialType": "dream",
                    "materialText": "A snake moved through the house.",
                }
            )
            self.assertFalse(
                any(item["normalizedClaimKey"] == normalized for item in result["hypotheses"])
            )

        asyncio.run(run())

    def test_narrative_only_llm_output_falls_back_cleanly(self) -> None:
        async def run() -> None:
            repo = InMemoryGraphMemoryRepository()
            core = CirculatioCore(repo, llm=NarrativeOnlyLlm())
            result = await core.interpret_material(
                {
                    "userId": "user_1",
                    "materialType": "dream",
                    "materialText": "A snake moved through the house.",
                }
            )
            self.assertEqual(result["symbolMentions"], [])
            self.assertEqual(result["memoryWritePlan"]["proposals"], [])
            self.assertEqual(result["llmInterpretationHealth"]["status"], "fallback")
            self.assertIn("did not return usable structured output", result["userFacingResponse"])

        asyncio.run(run())

    def test_weekly_review_uses_llm_path(self) -> None:
        async def run() -> None:
            repo = InMemoryGraphMemoryRepository()
            llm = FakeCirculatioLlm()
            core = CirculatioCore(repo, llm=llm)
            result = await core.generate_circulation_summary(
                {
                    "userId": "user_1",
                    "windowStart": "2026-04-12T00:00:00Z",
                    "windowEnd": "2026-04-19T00:00:00Z",
                    "hermesMemoryContext": {
                        "recurringSymbols": [],
                        "activeComplexCandidates": [],
                        "recentMaterialSummaries": [],
                        "recentInterpretationFeedback": [],
                        "practiceOutcomes": [],
                        "culturalOriginPreferences": [],
                        "suppressedHypotheses": [],
                        "typologyLensSummaries": [],
                        "recentTypologySignals": [],
                    },
                }
            )
            self.assertTrue(result["userFacingResponse"].startswith("LLM weekly review:"))
            self.assertEqual(result["activeThemes"], ["llm-theme"])
            self.assertEqual(len(llm.review_calls), 1)

        asyncio.run(run())

    def test_llm_drives_method_gate_series_and_practice_metadata(self) -> None:
        async def run() -> None:
            repo = InMemoryGraphMemoryRepository()
            llm = FakeCirculatioLlm()
            core = CirculatioCore(repo, llm=llm)
            result = await core.interpret_material(
                {
                    "userId": "user_1",
                    "materialType": "dream",
                    "materialText": "A snake moved through the house.",
                    "methodContextSnapshot": {
                        "windowStart": "2026-04-12T00:00:00Z",
                        "windowEnd": "2026-04-19T00:00:00Z",
                        "consciousAttitude": {
                            "id": "attitude_1",
                            "stanceSummary": "Trying to stay composed while feeling cornered.",
                            "activeValues": ["composure"],
                            "activeConflicts": ["authority vs autonomy"],
                            "avoidedThemes": ["confrontation"],
                            "confidence": "medium",
                            "status": "user_confirmed",
                            "evidenceIds": [],
                        },
                        "activeDreamSeries": [
                            {
                                "id": "series_house_snake",
                                "label": "House / snake sequence",
                                "status": "active",
                                "confidence": "medium",
                                "materialIds": ["material_old"],
                            }
                        ],
                        "source": "circulatio-backend",
                    },
                }
            )
            self.assertEqual(result["depthReadiness"]["status"], "ready")
            self.assertEqual(result["methodGate"]["depthLevel"], "depth_interpretation_allowed")
            self.assertTrue(result["dreamSeriesSuggestions"])
            self.assertEqual(result["practiceRecommendation"]["templateId"], "llm-guided-practice")
            self.assertTrue(result["practiceRecommendation"]["script"])
            self.assertEqual(result["depthEngineHealth"]["status"], "structured")

        asyncio.run(run())

    def test_individuation_candidates_map_to_assessment_and_pending_proposals(self) -> None:
        async def run() -> None:
            repo = InMemoryGraphMemoryRepository()
            llm = FakeCirculatioLlm()
            original = llm.interpret_material

            async def with_individuation(input_data: dict[str, object]) -> dict[str, object]:
                result = await original(input_data)
                result["proposalCandidates"] = []
                result["individuation"] = {
                    "realityAnchors": [
                        {
                            "label": "Reality anchors",
                            "summary": "Outer life appears stable enough for careful reflection.",
                            "anchorSummary": "Daily life is holding together well enough for depth work.",
                            "workDailyLifeContinuity": "stable",
                            "sleepBodyRegulation": "stable",
                            "relationshipContact": "available",
                            "reflectiveCapacity": "steady",
                            "groundingRecommendation": "clear_for_depth",
                            "reasons": ["Stable routines remain available."],
                            "confidence": "high",
                            "supportingRefs": ["sym_snake"],
                            "reason": "Hold this grounding context only if the user wants it remembered.",
                        }
                    ],
                    "thresholdProcesses": [
                        {
                            "label": "Vocational threshold",
                            "summary": "A threshold is active around work identity.",
                            "thresholdName": "Vocational threshold",
                            "phase": "liminal",
                            "whatIsEnding": "An older work identity is loosening.",
                            "notYetBegun": "The next form is not yet stable.",
                            "groundingStatus": "steady",
                            "invitationReadiness": "ask",
                            "normalizedThresholdKey": "vocational-threshold",
                            "confidence": "medium",
                            "supportingRefs": ["sym_snake"],
                            "reason": "Hold this threshold only if the user wants it remembered.",
                        }
                    ],
                    "projectionHypotheses": [
                        {
                            "label": "Projection hypothesis",
                            "summary": "A provisional projection hypothesis is available.",
                            "hypothesisSummary": "Authority may be carrying disowned pressure here.",
                            "projectionPattern": "Authority becomes especially charged when the user feels seen.",
                            "userTestPrompt": "What part of this charge may also belong to the inner situation?",
                            "normalizedHypothesisKey": "authority-pressure",
                            "confidence": "high",
                            "supportingRefs": ["fig_authority"],
                            "counterRefs": ["motif_containment"],
                            "reason": "Hold this hypothesis only with explicit projection-language consent.",
                        }
                    ],
                    "innerOuterCorrespondences": [
                        {
                            "label": "Inner-outer correspondence",
                            "summary": "A tentative correspondence is visible across inner and outer scenes.",
                            "correspondenceSummary": "The same image appears in dream material and waking conflict.",
                            "innerRefs": ["material_older"],
                            "outerRefs": ["life_event_1"],
                            "symbolIds": ["symbol_snake"],
                            "userCharge": "explicitly_charged",
                            "caveat": "Hold lightly without causal certainty.",
                            "normalizedCorrespondenceKey": "snake-crossing",
                            "confidence": "medium",
                            "supportingRefs": ["sym_snake"],
                            "reason": "Hold this correspondence only with explicit correspondence consent.",
                        }
                    ],
                    "archetypalPatterns": [
                        {
                            "label": "Archetypal pattern",
                            "summary": "A very tentative threshold pattern is available.",
                            "patternFamily": "threshold",
                            "resonanceSummary": "The image field may resonate with a threshold pattern.",
                            "caveat": "Keep this as a tentative lens rather than a verdict.",
                            "phrasingPolicy": "very_tentative",
                            "confidence": "high",
                            "supportingRefs": ["sym_snake"],
                            "counterRefs": ["motif_containment"],
                            "reason": "Hold this pattern only with explicit archetypal-patterning consent.",
                        }
                    ],
                }
                return result

            llm.interpret_material = with_individuation
            core = CirculatioCore(repo, llm=llm)
            result = await core.interpret_material(
                {
                    "userId": "user_1",
                    "materialType": "dream",
                    "materialText": "A snake and a uniformed authority appeared in the locked house.",
                    "methodContextSnapshot": {
                        "windowStart": "2026-04-12T00:00:00Z",
                        "windowEnd": "2026-04-19T00:00:00Z",
                        "consentPreferences": [
                            {"scope": "projection_language", "status": "allow"},
                            {"scope": "inner_outer_correspondence", "status": "allow"},
                            {"scope": "archetypal_patterning", "status": "allow"},
                        ],
                        "source": "circulatio-backend",
                    },
                }
            )
            assessment = result["individuationAssessment"]
            self.assertEqual(
                assessment["realityAnchors"]["groundingRecommendation"], "clear_for_depth"
            )
            self.assertEqual(len(assessment["thresholdProcesses"]), 1)
            self.assertEqual(len(assessment["projectionHypotheses"]), 1)
            self.assertEqual(len(assessment["innerOuterCorrespondences"]), 1)
            self.assertEqual(len(assessment["archetypalPatterns"]), 1)
            self.assertEqual(assessment["projectionHypotheses"][0]["confidence"], "medium")
            self.assertEqual(assessment["withheldReasons"], [])
            actions = {proposal["action"] for proposal in result["memoryWritePlan"]["proposals"]}
            self.assertIn("create_reality_anchor_summary", actions)
            self.assertIn("upsert_threshold_process", actions)
            self.assertIn("upsert_projection_hypothesis", actions)
            self.assertIn("upsert_inner_outer_correspondence", actions)
            self.assertIn("upsert_archetypal_pattern", actions)
            self.assertEqual(result["llmInterpretationHealth"]["status"], "structured")

        asyncio.run(run())

    def test_individuation_scoped_candidates_are_withheld_without_consent(self) -> None:
        async def run() -> None:
            repo = InMemoryGraphMemoryRepository()
            llm = FakeCirculatioLlm()
            original = llm.interpret_material

            async def with_scoped_individuation(input_data: dict[str, object]) -> dict[str, object]:
                result = await original(input_data)
                result["proposalCandidates"] = []
                result["individuation"] = {
                    "projectionHypotheses": [
                        {
                            "label": "Projection hypothesis",
                            "summary": "A projection hypothesis is available.",
                            "hypothesisSummary": "Authority may be carrying disowned pressure here.",
                            "projectionPattern": "Authority becomes especially charged when the user feels seen.",
                            "userTestPrompt": "What part of this charge may also belong to the inner situation?",
                            "normalizedHypothesisKey": "authority-pressure",
                            "confidence": "medium",
                            "supportingRefs": ["fig_authority"],
                            "reason": "Hold this hypothesis only with explicit projection-language consent.",
                        }
                    ],
                    "innerOuterCorrespondences": [
                        {
                            "label": "Inner-outer correspondence",
                            "summary": "A tentative correspondence is visible across inner and outer scenes.",
                            "correspondenceSummary": "The same image appears in dream material and waking conflict.",
                            "innerRefs": ["material_older"],
                            "outerRefs": ["life_event_1"],
                            "symbolIds": ["symbol_snake"],
                            "userCharge": "explicitly_charged",
                            "caveat": "Hold lightly without causal certainty.",
                            "normalizedCorrespondenceKey": "snake-crossing",
                            "confidence": "medium",
                            "supportingRefs": ["sym_snake"],
                            "reason": "Hold this correspondence only with explicit correspondence consent.",
                        }
                    ],
                    "archetypalPatterns": [
                        {
                            "label": "Archetypal pattern",
                            "summary": "A very tentative threshold pattern is available.",
                            "patternFamily": "threshold",
                            "resonanceSummary": "The image field may resonate with a threshold pattern.",
                            "caveat": "Keep this as a tentative lens rather than a verdict.",
                            "phrasingPolicy": "very_tentative",
                            "confidence": "medium",
                            "supportingRefs": ["sym_snake"],
                            "reason": "Hold this pattern only with explicit archetypal-patterning consent.",
                        }
                    ],
                }
                return result

            llm.interpret_material = with_scoped_individuation
            core = CirculatioCore(repo, llm=llm)
            result = await core.interpret_material(
                {
                    "userId": "user_1",
                    "materialType": "dream",
                    "materialText": "A snake and a uniformed authority appeared in the locked house.",
                    "methodContextSnapshot": {
                        "windowStart": "2026-04-12T00:00:00Z",
                        "windowEnd": "2026-04-19T00:00:00Z",
                        "consentPreferences": [
                            {"scope": "projection_language", "status": "revoked"},
                            {"scope": "inner_outer_correspondence", "status": "ask_each_time"},
                            {"scope": "archetypal_patterning", "status": "declined"},
                        ],
                        "source": "circulatio-backend",
                    },
                }
            )
            assessment = result["individuationAssessment"]
            self.assertEqual(assessment["projectionHypotheses"], [])
            self.assertEqual(assessment["innerOuterCorrespondences"], [])
            self.assertEqual(assessment["archetypalPatterns"], [])
            self.assertIn("projection_language_withheld_by_consent", assessment["withheldReasons"])
            self.assertIn(
                "inner_outer_correspondence_withheld_by_consent",
                assessment["withheldReasons"],
            )
            self.assertIn(
                "archetypal_patterning_withheld_by_consent", assessment["withheldReasons"]
            )
            actions = {proposal["action"] for proposal in result["memoryWritePlan"]["proposals"]}
            self.assertNotIn("upsert_projection_hypothesis", actions)
            self.assertNotIn("upsert_inner_outer_correspondence", actions)
            self.assertNotIn("upsert_archetypal_pattern", actions)
            self.assertEqual(result["llmInterpretationHealth"]["status"], "structured")

        asyncio.run(run())

    def test_context_adapter_uses_life_os_snapshot_and_compacts_fields(self) -> None:
        async def run() -> None:
            repo = InMemoryGraphMemoryRepository()
            adapter = ContextAdapter(repo, life_os=FakeLifeOs())
            result = await adapter.build_material_input(
                {
                    "userId": "user_1",
                    "materialType": "dream",
                    "materialText": "A snake under the stairs.",
                    "lifeOsWindow": {
                        "start": "2026-04-12T00:00:00Z",
                        "end": "2026-04-19T00:00:00Z",
                    },
                }
            )
            snapshot = result["lifeContextSnapshot"]
            self.assertIn("focusSummary", snapshot)
            self.assertNotIn("rawMoodLog", snapshot)
            self.assertNotIn("sleepEntries", snapshot)

        asyncio.run(run())

    def test_generate_practice_uses_llm_output(self) -> None:
        async def run() -> None:
            repo = InMemoryGraphMemoryRepository()
            llm = FakeCirculatioLlm()
            core = CirculatioCore(repo, llm=llm)
            result = await core.generate_practice(
                {
                    "userId": "user_1",
                    "windowStart": "2026-04-12T00:00:00Z",
                    "windowEnd": "2026-04-19T00:00:00Z",
                    "trigger": {"triggerType": "manual"},
                    "hermesMemoryContext": {
                        "recurringSymbols": [],
                        "activeComplexCandidates": [],
                        "recentMaterialSummaries": [],
                        "recentInterpretationFeedback": [],
                        "practiceOutcomes": [],
                        "culturalOriginPreferences": [],
                        "suppressedHypotheses": [],
                        "typologyLensSummaries": [],
                        "recentTypologySignals": [],
                    },
                    "methodContextSnapshot": {
                        "windowStart": "2026-04-12T00:00:00Z",
                        "windowEnd": "2026-04-19T00:00:00Z",
                        "consciousAttitude": {"id": "att_1", "stanceSummary": "Stay with it."},
                        "consentPreferences": [{"scope": "active_imagination", "status": "allow"}],
                        "source": "circulatio-backend",
                    },
                }
            )
            self.assertEqual(result["practiceRecommendation"]["type"], "active_imagination")
            self.assertEqual(result["llmHealth"]["source"], "llm")
            self.assertEqual(len(llm.practice_calls), 1)

        asyncio.run(run())

    def test_threshold_review_builds_memory_write_plan_from_llm_proposals(self) -> None:
        async def run() -> None:
            repo = InMemoryGraphMemoryRepository()
            llm = FakeCirculatioLlm()
            core = CirculatioCore(repo, llm=llm)
            result = await core.generate_threshold_review(
                {
                    "userId": "user_1",
                    "windowStart": "2026-04-12T00:00:00Z",
                    "windowEnd": "2026-04-19T00:00:00Z",
                    "hermesMemoryContext": {
                        "recentMaterialSummaries": [
                            {
                                "id": "material_1",
                                "materialType": "dream",
                                "date": "2026-04-18T08:00:00Z",
                                "summary": "A work threshold and authority scene returned.",
                                "symbolNames": [],
                                "themeLabels": [],
                            }
                        ]
                    },
                    "evidence": [
                        {
                            "id": "evidence_1",
                            "type": "dream_text_span",
                            "sourceId": "material_1",
                            "quoteOrSummary": "A work threshold and authority scene returned.",
                            "timestamp": "2026-04-18T08:00:00Z",
                            "privacyClass": "approved_summary",
                            "reliability": "high",
                        }
                    ],
                }
            )
            self.assertIn("memoryWritePlan", result)
            proposals = result["memoryWritePlan"]["proposals"]
            self.assertEqual(len(proposals), 1)
            self.assertEqual(proposals[0]["action"], "upsert_relational_scene")
            self.assertEqual(proposals[0]["evidenceIds"], ["evidence_1"])

        asyncio.run(run())

    def test_living_myth_review_builds_memory_write_plan_from_llm_proposals(self) -> None:
        async def run() -> None:
            repo = InMemoryGraphMemoryRepository()
            llm = FakeCirculatioLlm()
            core = CirculatioCore(repo, llm=llm)
            result = await core.generate_living_myth_review(
                {
                    "userId": "user_1",
                    "windowStart": "2026-04-12T00:00:00Z",
                    "windowEnd": "2026-04-19T00:00:00Z",
                    "hermesMemoryContext": {
                        "recentMaterialSummaries": [
                            {
                                "id": "material_1",
                                "materialType": "dream",
                                "date": "2026-04-18T08:00:00Z",
                                "summary": "A work threshold and authority scene returned.",
                                "symbolNames": [],
                                "themeLabels": [],
                            }
                        ]
                    },
                    "recentMaterialSummaries": [
                        {
                            "id": "material_1",
                            "materialType": "dream",
                            "date": "2026-04-18T08:00:00Z",
                            "summary": "A work threshold and authority scene returned.",
                            "symbolNames": [],
                            "themeLabels": [],
                        }
                    ],
                    "evidence": [
                        {
                            "id": "evidence_1",
                            "type": "dream_text_span",
                            "sourceId": "material_1",
                            "quoteOrSummary": "A work threshold and authority scene returned.",
                            "timestamp": "2026-04-18T08:00:00Z",
                            "privacyClass": "approved_summary",
                            "reliability": "high",
                        }
                    ],
                }
            )
            self.assertIn("memoryWritePlan", result)
            actions = {item["action"] for item in result["memoryWritePlan"]["proposals"]}
            self.assertEqual(
                actions,
                {"upsert_threshold_process", "create_symbolic_wellbeing_snapshot"},
            )
            for proposal in result["memoryWritePlan"]["proposals"]:
                self.assertEqual(proposal["evidenceIds"], ["evidence_1"])

        asyncio.run(run())

    def test_analysis_packet_preserves_top_level_provenance(self) -> None:
        async def run() -> None:
            repo = InMemoryGraphMemoryRepository()
            llm = FakeCirculatioLlm()
            core = CirculatioCore(repo, llm=llm)
            result = await core.generate_analysis_packet(
                {
                    "userId": "user_1",
                    "windowStart": "2026-04-12T00:00:00Z",
                    "windowEnd": "2026-04-19T00:00:00Z",
                    "hermesMemoryContext": {},
                    "activeThresholdProcesses": [
                        {
                            "id": "threshold_1",
                            "label": "Threshold process",
                            "summary": "A liminal process is active.",
                            "confidence": "medium",
                            "evidenceIds": ["evidence_1"],
                            "thresholdName": "Threshold process",
                            "phase": "liminal",
                            "whatIsEnding": "An older arrangement is loosening.",
                            "notYetBegun": "The next form is not yet clear.",
                            "groundingStatus": "unknown",
                            "invitationReadiness": "ask",
                            "normalizedThresholdKey": "threshold-process",
                            "status": "active",
                            "updatedAt": "2026-04-18T08:00:00Z",
                        }
                    ],
                    "evidence": [
                        {
                            "id": "evidence_1",
                            "type": "dream_text_span",
                            "sourceId": "material_1",
                            "quoteOrSummary": "A threshold process remained active.",
                            "timestamp": "2026-04-18T08:00:00Z",
                            "privacyClass": "approved_summary",
                            "reliability": "high",
                        }
                    ],
                }
            )
            self.assertEqual(result["includedMaterialIds"], ["material_1"])
            self.assertEqual(
                result["includedRecordRefs"],
                [{"recordType": "ThresholdProcess", "recordId": "threshold_1"}],
            )
            self.assertEqual(result["evidenceIds"], ["evidence_1"])

        asyncio.run(run())

    def test_generate_practice_falls_back_when_llm_unavailable(self) -> None:
        async def run() -> None:
            repo = InMemoryGraphMemoryRepository()
            core = CirculatioCore(repo, llm=None)
            result = await core.generate_practice(
                {
                    "userId": "user_1",
                    "windowStart": "2026-04-12T00:00:00Z",
                    "windowEnd": "2026-04-19T00:00:00Z",
                    "trigger": {"triggerType": "manual"},
                    "hermesMemoryContext": {
                        "recurringSymbols": [],
                        "activeComplexCandidates": [],
                        "recentMaterialSummaries": [],
                        "recentInterpretationFeedback": [],
                        "practiceOutcomes": [],
                        "culturalOriginPreferences": [],
                        "suppressedHypotheses": [],
                        "typologyLensSummaries": [],
                        "recentTypologySignals": [],
                    },
                }
            )
            self.assertEqual(result["practiceRecommendation"]["type"], "journaling")
            self.assertEqual(result["llmHealth"]["source"], "fallback")

        asyncio.run(run())

    def test_generate_rhythmic_brief_skips_symbolic_candidate_when_llm_unavailable(self) -> None:
        async def run() -> None:
            repo = InMemoryGraphMemoryRepository()
            core = CirculatioCore(repo, llm=None)
            result = await core.generate_rhythmic_brief(
                {
                    "userId": "user_1",
                    "windowStart": "2026-04-12T00:00:00Z",
                    "windowEnd": "2026-04-19T00:00:00Z",
                    "source": "manual",
                    "seed": {
                        "briefType": "daily",
                        "triggerKey": "daily:signal:sig_1:2026-04-19",
                        "titleHint": "Longitudinal signal",
                        "summaryHint": "A signal may be ready for a check-in.",
                        "priority": 60,
                        "relatedJourneyIds": [],
                        "relatedMaterialIds": [],
                        "relatedSymbolIds": [],
                        "relatedPracticeSessionIds": [],
                        "evidenceIds": [],
                        "reason": "longitudinal_signal_active",
                    },
                    "hermesMemoryContext": {
                        "recurringSymbols": [],
                        "activeComplexCandidates": [],
                        "recentMaterialSummaries": [],
                        "recentInterpretationFeedback": [],
                        "practiceOutcomes": [],
                        "culturalOriginPreferences": [],
                        "suppressedHypotheses": [],
                        "typologyLensSummaries": [],
                        "recentTypologySignals": [],
                    },
                }
            )
            self.assertTrue(result["withheld"])
            self.assertEqual(result["withheldReason"], "llm_missing_for_symbolic_brief")

        asyncio.run(run())

    def test_generate_rhythmic_brief_allows_neutral_practice_followup_fallback(self) -> None:
        async def run() -> None:
            repo = InMemoryGraphMemoryRepository()
            core = CirculatioCore(repo, llm=None)
            result = await core.generate_rhythmic_brief(
                {
                    "userId": "user_1",
                    "windowStart": "2026-04-12T00:00:00Z",
                    "windowEnd": "2026-04-19T00:00:00Z",
                    "source": "manual",
                    "seed": {
                        "briefType": "practice_followup",
                        "triggerKey": "practice_followup:practice_session:practice_1:2026-04-19",
                        "titleHint": "Practice follow-up",
                        "summaryHint": "A previously suggested practice may be ready for a light check-in.",
                        "suggestedActionHint": "You can note what happened, or simply leave it for later.",
                        "priority": 100,
                        "relatedJourneyIds": [],
                        "relatedMaterialIds": [],
                        "relatedSymbolIds": [],
                        "relatedPracticeSessionIds": ["practice_1"],
                        "evidenceIds": [],
                        "reason": "practice_session_due",
                    },
                    "hermesMemoryContext": {
                        "recurringSymbols": [],
                        "activeComplexCandidates": [],
                        "recentMaterialSummaries": [],
                        "recentInterpretationFeedback": [],
                        "practiceOutcomes": [],
                        "culturalOriginPreferences": [],
                        "suppressedHypotheses": [],
                        "typologyLensSummaries": [],
                        "recentTypologySignals": [],
                    },
                }
            )
            self.assertEqual(result["title"], "Practice follow-up")
            self.assertEqual(result["llmHealth"]["source"], "fallback")

        asyncio.run(run())


if __name__ == "__main__":
    unittest.main()
