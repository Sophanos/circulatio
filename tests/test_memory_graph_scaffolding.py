from __future__ import annotations

import asyncio
import os
import sys
import unittest

sys.path.insert(0, os.path.abspath("src"))

from circulatio.domain.errors import ValidationError
from circulatio.repositories.in_memory_circulatio_repository import InMemoryCirculatioRepository


class MemoryGraphScaffoldingTests(unittest.TestCase):
    async def _seed_repository(self, repository: InMemoryCirculatioRepository) -> None:
        await repository.create_material(
            {
                "id": "material_1",
                "userId": "user_1",
                "materialType": "dream",
                "title": "Serpent dream",
                "summary": "A serpent moved through a house.",
                "materialDate": "2026-04-15T08:00:00Z",
                "createdAt": "2026-04-15T08:00:00Z",
                "updatedAt": "2026-04-15T08:00:00Z",
                "status": "active",
                "privacyClass": "approved_summary",
                "source": "hermes_command",
                "linkedContextSnapshotIds": [],
                "linkedPracticeSessionIds": [],
                "tags": ["snake", "house"],
            }
        )
        await repository.create_symbol(
            {
                "id": "symbol_snake",
                "userId": "user_1",
                "canonicalName": "snake",
                "aliases": ["serpent"],
                "category": "animal",
                "recurrenceCount": 2,
                "firstSeen": "2026-04-14T08:00:00Z",
                "lastSeen": "2026-04-15T08:00:00Z",
                "valenceHistory": [],
                "personalAssociations": [],
                "linkedMaterialIds": ["material_1"],
                "linkedLifeEventRefs": [],
                "status": "active",
                "createdAt": "2026-04-14T08:00:00Z",
                "updatedAt": "2026-04-15T08:00:00Z",
            }
        )
        await repository.create_pattern(
            {
                "id": "pattern_1",
                "userId": "user_1",
                "patternType": "complex_candidate",
                "label": "Authority / autonomy",
                "formulation": "A recurring tension between pressure and instinct.",
                "status": "active",
                "activationIntensity": 0.7,
                "confidence": "medium",
                "evidenceIds": ["evidence_1"],
                "counterevidenceIds": [],
                "linkedSymbols": ["snake"],
                "linkedSymbolIds": ["symbol_snake"],
                "linkedMaterialIds": ["material_1"],
                "linkedLifeEventRefs": [],
                "createdAt": "2026-04-15T08:00:00Z",
                "updatedAt": "2026-04-15T08:00:00Z",
                "lastSeen": "2026-04-15T08:00:00Z",
            }
        )
        await repository.create_practice_session(
            {
                "id": "practice_1",
                "userId": "user_1",
                "materialId": "material_1",
                "runId": "run_1",
                "practiceType": "journaling",
                "target": "snake",
                "reason": "Hold the image without forcing it.",
                "instructions": ["Write the image."],
                "durationMinutes": 10,
                "contraindicationsChecked": ["none"],
                "requiresConsent": False,
                "status": "completed",
                "outcome": "The image felt less charged after writing.",
                "activationBefore": "high",
                "activationAfter": "moderate",
                "createdAt": "2026-04-15T18:00:00Z",
                "updatedAt": "2026-04-15T18:15:00Z",
                "completedAt": "2026-04-15T18:15:00Z",
            }
        )
        await repository.store_evidence_items(
            "user_1",
            [
                {
                    "id": "evidence_1",
                    "type": "dream_text_span",
                    "sourceId": "material_1",
                    "quoteOrSummary": "snake in the house",
                    "timestamp": "2026-04-15T08:05:00Z",
                    "privacyClass": "approved_summary",
                    "reliability": "high",
                }
            ],
        )
        await repository.store_interpretation_run(
            {
                "id": "run_1",
                "userId": "user_1",
                "materialId": "material_1",
                "materialType": "dream",
                "createdAt": "2026-04-15T08:10:00Z",
                "status": "completed",
                "options": {
                    "maxHistoricalItems": 12,
                    "maxHypotheses": 2,
                    "allowCulturalAmplification": False,
                    "allowLifeContextLinks": True,
                    "proposeRawMaterialStorage": False,
                    "enableTypology": False,
                    "maxTypologyHypotheses": 1,
                },
                "safetyDisposition": {
                    "status": "clear",
                    "flags": [],
                    "depthWorkAllowed": True,
                    "message": "",
                },
                "result": {
                    "runId": "run_1",
                    "materialId": "material_1",
                    "safetyDisposition": {
                        "status": "clear",
                        "flags": [],
                        "depthWorkAllowed": True,
                        "message": "",
                    },
                    "observations": [],
                    "evidence": [],
                    "symbolMentions": [],
                    "figureMentions": [],
                    "motifMentions": [],
                    "personalSymbolUpdates": [],
                    "culturalAmplifications": [],
                    "hypotheses": [],
                    "complexCandidateUpdates": [],
                    "lifeContextLinks": [],
                    "practiceRecommendation": {
                        "id": "practice_plan_1",
                        "type": "journaling",
                        "reason": "Hold the image.",
                        "contraindicationsChecked": ["none"],
                        "durationMinutes": 10,
                        "requiresConsent": False,
                        "instructions": ["Write the image."],
                    },
                    "memoryWritePlan": {"runId": "run_1", "proposals": [], "evidenceItems": []},
                    "userFacingResponse": "A cautious symbolic reading is available.",
                },
                "evidenceIds": ["evidence_1"],
                "hypothesisIds": [],
                "proposalDecisions": [],
            }
        )
        await repository.create_individuation_record(
            {
                "id": "threshold_1",
                "userId": "user_1",
                "recordType": "threshold_process",
                "status": "active",
                "source": "threshold_review",
                "label": "House threshold",
                "summary": "A liminal process is active around the house image.",
                "confidence": "medium",
                "evidenceIds": ["evidence_1"],
                "relatedMaterialIds": ["material_1"],
                "relatedSymbolIds": ["symbol_snake"],
                "relatedGoalIds": [],
                "relatedDreamSeriesIds": [],
                "relatedJourneyIds": [],
                "relatedPracticeSessionIds": ["practice_1"],
                "privacyClass": "approved_summary",
                "details": {
                    "thresholdName": "House threshold",
                    "phase": "liminal",
                    "whatIsEnding": "An older stance is loosening.",
                    "notYetBegun": "The next form is not yet stable.",
                    "groundingStatus": "steady",
                    "invitationReadiness": "ask",
                    "normalizedThresholdKey": "house-threshold",
                },
                "createdAt": "2026-04-15T08:20:00Z",
                "updatedAt": "2026-04-15T08:20:00Z",
            }
        )
        await repository.create_living_myth_record(
            {
                "id": "chapter_1",
                "userId": "user_1",
                "recordType": "life_chapter_snapshot",
                "status": "active",
                "source": "living_myth_review",
                "label": "House chapter",
                "summary": "A life chapter is forming around guarded entry and instinct.",
                "confidence": "medium",
                "evidenceIds": ["evidence_1"],
                "relatedMaterialIds": ["material_1"],
                "relatedSymbolIds": ["symbol_snake"],
                "relatedGoalIds": [],
                "relatedDreamSeriesIds": [],
                "relatedIndividuationRecordIds": ["threshold_1"],
                "privacyClass": "approved_summary",
                "details": {
                    "chapterLabel": "House chapter",
                    "chapterSummary": "A life chapter is forming around guarded entry.",
                    "governingSymbolIds": ["symbol_snake"],
                    "governingQuestions": ["What is trying to cross the threshold?"],
                    "activeOppositionIds": [],
                    "thresholdProcessIds": ["threshold_1"],
                    "relationalSceneIds": [],
                    "correspondenceIds": [],
                },
                "createdAt": "2026-04-15T08:25:00Z",
                "updatedAt": "2026-04-15T08:25:00Z",
            }
        )
        await repository.create_living_myth_review(
            {
                "id": "review_1",
                "userId": "user_1",
                "reviewType": "threshold_review",
                "status": "generated",
                "windowStart": "2026-04-12T00:00:00Z",
                "windowEnd": "2026-04-19T23:59:59Z",
                "materialIds": ["material_1"],
                "contextSnapshotIds": [],
                "evidenceIds": ["evidence_1"],
                "result": {
                    "userFacingResponse": "A threshold review is available.",
                    "thresholdProcesses": [],
                    "realityAnchors": [],
                },
                "proposalDecisions": [],
                "createdAt": "2026-04-19T00:00:00Z",
                "updatedAt": "2026-04-19T00:00:00Z",
            }
        )
        await repository.create_analysis_packet(
            {
                "id": "packet_1",
                "userId": "user_1",
                "status": "generated",
                "windowStart": "2026-04-12T00:00:00Z",
                "windowEnd": "2026-04-19T23:59:59Z",
                "packetTitle": "House packet",
                "sections": [
                    {
                        "title": "Active thread",
                        "purpose": "Bound the most active symbolic material.",
                        "items": [],
                    }
                ],
                "includedMaterialIds": ["material_1"],
                "includedRecordRefs": [
                    {"recordType": "threshold_process", "recordId": "threshold_1"},
                    {"recordType": "life_chapter_snapshot", "recordId": "chapter_1"},
                ],
                "evidenceIds": ["evidence_1"],
                "source": "llm",
                "privacyClass": "approved_summary",
                "userFacingResponse": "A bounded packet is ready.",
                "createdAt": "2026-04-19T00:10:00Z",
                "updatedAt": "2026-04-19T00:10:00Z",
            }
        )

    def test_memory_kernel_snapshot_projects_namespaces_with_provenance(self) -> None:
        async def run() -> None:
            repository = InMemoryCirculatioRepository()
            await self._seed_repository(repository)
            snapshot = await repository.build_memory_kernel_snapshot("user_1")
            self.assertTrue(snapshot["items"])
            namespaces = {item["namespace"] for item in snapshot["items"]}
            self.assertIn("materials", namespaces)
            self.assertIn("personal_symbols", namespaces)
            self.assertIn("patterns", namespaces)
            self.assertIn("practice_sessions", namespaces)
            self.assertIn("individuation_records", namespaces)
            self.assertIn("living_myth_records", namespaces)
            self.assertIn("living_myth_reviews", namespaces)
            self.assertIn("analysis_packets", namespaces)
            for item in snapshot["items"]:
                self.assertIn("provenance", item)
                self.assertIn("importance", item)
                self.assertIn("privacyClass", item)

        asyncio.run(run())

    def test_memory_kernel_query_filters_namespace_and_limits(self) -> None:
        async def run() -> None:
            repository = InMemoryCirculatioRepository()
            await self._seed_repository(repository)
            snapshot = await repository.build_memory_kernel_snapshot(
                "user_1",
                query={"namespaces": ["personal_symbols"], "limit": 1},
            )
            self.assertEqual(len(snapshot["items"]), 1)
            self.assertEqual(snapshot["items"][0]["namespace"], "personal_symbols")

        asyncio.run(run())

    def test_graph_query_returns_native_nodes_and_edges(self) -> None:
        async def run() -> None:
            repository = InMemoryCirculatioRepository()
            await self._seed_repository(repository)
            result = await repository.query_graph("user_1", query={"includeEvidence": True})
            node_types = {item["type"] for item in result["nodes"]}
            edge_types = {item["type"] for item in result["edges"]}
            self.assertIn("DreamEntry", node_types)
            self.assertIn("InterpretationRun", node_types)
            self.assertIn("EvidenceItem", node_types)
            self.assertIn("ThresholdProcess", node_types)
            self.assertIn("LifeChapterSnapshot", node_types)
            self.assertIn("LivingMythReview", node_types)
            self.assertIn("AnalysisPacket", node_types)
            self.assertIn("DRAWS_FROM", edge_types)
            self.assertIn("USED_EVIDENCE", edge_types)
            self.assertIn("MENTIONS", edge_types)
            self.assertIn("MARKS_THRESHOLD", edge_types)
            self.assertIn("BELONGS_TO_CHAPTER", edge_types)
            self.assertIn("CONTAINED_IN_PACKET", edge_types)

        asyncio.run(run())

    def test_graph_query_rejects_disallowed_types_or_clamps_depth(self) -> None:
        async def run() -> None:
            repository = InMemoryCirculatioRepository()
            await self._seed_repository(repository)
            with self.assertRaises(ValidationError):
                await repository.query_graph("user_1", query={"nodeTypes": ["BadType"]})
            result = await repository.query_graph(
                "user_1",
                query={"rootNodeIds": ["material_1"], "maxDepth": 99},
            )
            self.assertTrue(any("maxDepth clamped" in warning for warning in result["warnings"]))

        asyncio.run(run())


if __name__ == "__main__":
    unittest.main()
