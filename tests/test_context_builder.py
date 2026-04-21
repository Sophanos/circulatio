from __future__ import annotations

import asyncio
import os
import sys
import unittest

sys.path.insert(0, os.path.abspath("src"))

from circulatio.adapters.context_adapter import ContextAdapter
from circulatio.adapters.context_builder import CirculatioLifeContextBuilder
from circulatio.adapters.method_context_builder import CirculatioMethodContextBuilder
from circulatio.repositories.in_memory_circulatio_repository import InMemoryCirculatioRepository


class FakeLifeOs:
    async def get_life_context_snapshot(self, *, user_id: str, window_start: str, window_end: str):
        del user_id
        return {
            "windowStart": window_start,
            "windowEnd": window_end,
            "lifeEventRefs": [{"id": "life_event_1", "summary": "Hermes reference event"}],
            "focusSummary": "Hermes fallback context",
            "source": "hermes-life-os",
        }


class ContextBuilderTests(unittest.TestCase):
    async def _seed_native_records(self, repository: InMemoryCirculatioRepository) -> None:
        await repository.create_material(
            {
                "id": "material_charged",
                "userId": "user_1",
                "materialType": "charged_event",
                "title": "Meeting rupture",
                "summary": "A charged event around authority pressure was recorded.",
                "text": "PRIVATE RAW DREAM TEXT SHOULD NOT SURFACE",
                "materialDate": "2026-04-13T09:00:00Z",
                "createdAt": "2026-04-13T09:00:00Z",
                "updatedAt": "2026-04-13T09:00:00Z",
                "status": "active",
                "privacyClass": "approved_summary",
                "source": "hermes_command",
                "linkedContextSnapshotIds": [],
                "linkedPracticeSessionIds": [],
                "tags": ["authority", "tension"],
            }
        )
        await repository.create_symbol(
            {
                "id": "symbol_snake",
                "userId": "user_1",
                "canonicalName": "snake",
                "aliases": ["serpent"],
                "category": "animal",
                "recurrenceCount": 3,
                "firstSeen": "2026-04-10T09:00:00Z",
                "lastSeen": "2026-04-14T09:00:00Z",
                "valenceHistory": [
                    {
                        "date": "2026-04-13T09:00:00Z",
                        "tone": "charged",
                        "sourceId": "material_charged",
                    },
                    {
                        "date": "2026-04-14T09:00:00Z",
                        "tone": "watchful",
                        "sourceId": "material_charged",
                    },
                ],
                "personalAssociations": [],
                "linkedMaterialIds": ["material_charged"],
                "linkedLifeEventRefs": [],
                "status": "active",
                "createdAt": "2026-04-10T09:00:00Z",
                "updatedAt": "2026-04-14T09:00:00Z",
            }
        )
        await repository.create_pattern(
            {
                "id": "pattern_authority",
                "userId": "user_1",
                "patternType": "complex_candidate",
                "label": "Authority / autonomy",
                "formulation": "Authority pressure may be charging the symbolic field.",
                "status": "active",
                "activationIntensity": 0.8,
                "confidence": "medium",
                "evidenceIds": [],
                "counterevidenceIds": [],
                "linkedSymbols": ["snake"],
                "linkedSymbolIds": ["symbol_snake"],
                "linkedMaterialIds": ["material_charged"],
                "linkedLifeEventRefs": [],
                "createdAt": "2026-04-13T09:00:00Z",
                "updatedAt": "2026-04-14T09:00:00Z",
                "lastSeen": "2026-04-14T09:00:00Z",
            }
        )
        await repository.create_practice_session(
            {
                "id": "practice_1",
                "userId": "user_1",
                "materialId": "material_charged",
                "practiceType": "journaling",
                "target": "snake",
                "reason": "Track what the image is doing.",
                "instructions": ["Write the image.", "Note what changed."],
                "durationMinutes": 10,
                "contraindicationsChecked": ["none"],
                "requiresConsent": False,
                "status": "completed",
                "outcome": "The image felt less threatening after writing.",
                "activationBefore": "high",
                "activationAfter": "moderate",
                "createdAt": "2026-04-14T18:00:00Z",
                "updatedAt": "2026-04-14T18:30:00Z",
                "completedAt": "2026-04-14T18:30:00Z",
            }
        )

    def test_builder_derives_bounded_circulatio_backend_snapshot_from_records(self) -> None:
        async def run() -> None:
            repository = InMemoryCirculatioRepository()
            await self._seed_native_records(repository)
            builder = CirculatioLifeContextBuilder(repository)
            snapshot = await builder.build_life_context_snapshot(
                user_id="user_1",
                window_start="2026-04-12T00:00:00Z",
                window_end="2026-04-19T00:00:00Z",
            )
            self.assertIsNotNone(snapshot)
            assert snapshot is not None
            self.assertEqual(snapshot["source"], "circulatio-backend")
            self.assertLessEqual(len(snapshot.get("lifeEventRefs", [])), 5)
            self.assertLessEqual(len(snapshot.get("notableChanges", [])), 5)
            self.assertNotIn("PRIVATE RAW DREAM TEXT SHOULD NOT SURFACE", str(snapshot))

        asyncio.run(run())

    def test_builder_returns_none_when_no_native_signals_exist(self) -> None:
        async def run() -> None:
            repository = InMemoryCirculatioRepository()
            builder = CirculatioLifeContextBuilder(repository)
            snapshot = await builder.build_life_context_snapshot(
                user_id="user_1",
                window_start="2026-04-12T00:00:00Z",
                window_end="2026-04-19T00:00:00Z",
            )
            self.assertIsNone(snapshot)

        asyncio.run(run())

    def test_context_adapter_prefers_native_context_over_hermes(self) -> None:
        async def run() -> None:
            repository = InMemoryCirculatioRepository()
            await self._seed_native_records(repository)
            builder = CirculatioLifeContextBuilder(repository)
            adapter = ContextAdapter(repository, life_os=FakeLifeOs(), life_context_builder=builder)
            result = await adapter.build_material_input(
                {
                    "userId": "user_1",
                    "materialId": "material_new",
                    "materialType": "dream",
                    "materialText": "A serpent moved under the stairs.",
                    "materialDate": "2026-04-16T09:00:00Z",
                    "lifeOsWindow": {
                        "start": "2026-04-12T00:00:00Z",
                        "end": "2026-04-19T00:00:00Z",
                    },
                }
            )
            self.assertEqual(result["lifeContextSnapshot"]["source"], "circulatio-backend")

        asyncio.run(run())

    def test_context_adapter_uses_hermes_fallback_when_native_empty_and_window_provided(
        self,
    ) -> None:
        async def run() -> None:
            repository = InMemoryCirculatioRepository()
            builder = CirculatioLifeContextBuilder(repository)
            adapter = ContextAdapter(repository, life_os=FakeLifeOs(), life_context_builder=builder)
            result = await adapter.build_material_input(
                {
                    "userId": "user_1",
                    "materialType": "dream",
                    "materialText": "A serpent moved under the stairs.",
                    "materialDate": "2026-04-16T09:00:00Z",
                    "lifeOsWindow": {
                        "start": "2026-04-12T00:00:00Z",
                        "end": "2026-04-19T00:00:00Z",
                    },
                }
            )
            self.assertEqual(result["lifeContextSnapshot"]["source"], "hermes-life-os")

        asyncio.run(run())

    def test_context_adapter_builds_native_context_without_life_os_window(self) -> None:
        async def run() -> None:
            repository = InMemoryCirculatioRepository()
            await self._seed_native_records(repository)
            builder = CirculatioLifeContextBuilder(repository)
            adapter = ContextAdapter(repository, life_context_builder=builder)
            result = await adapter.build_material_input(
                {
                    "userId": "user_1",
                    "materialId": "material_new",
                    "materialType": "dream",
                    "materialText": "A serpent moved under the stairs.",
                    "materialDate": "2026-04-16T09:00:00Z",
                }
            )
            self.assertEqual(result["lifeContextSnapshot"]["source"], "circulatio-backend")

        asyncio.run(run())

    def test_context_adapter_builds_native_method_context(self) -> None:
        async def run() -> None:
            repository = InMemoryCirculatioRepository()
            await self._seed_native_records(repository)
            await repository.create_conscious_attitude_snapshot(
                {
                    "id": "attitude_1",
                    "userId": "user_1",
                    "source": "manual_checkin",
                    "status": "user_confirmed",
                    "windowStart": "2026-04-12T00:00:00Z",
                    "windowEnd": "2026-04-19T00:00:00Z",
                    "stanceSummary": "Trying to stay composed while feeling cornered.",
                    "activeValues": ["composure"],
                    "activeConflicts": ["authority vs autonomy"],
                    "avoidedThemes": ["confrontation"],
                    "confidence": "medium",
                    "evidenceIds": [],
                    "relatedMaterialIds": ["material_charged"],
                    "relatedGoalIds": [],
                    "privacyClass": "approved_summary",
                    "createdAt": "2026-04-14T09:00:00Z",
                    "updatedAt": "2026-04-14T09:00:00Z",
                }
            )
            await repository.create_body_state(
                {
                    "id": "body_1",
                    "userId": "user_1",
                    "source": "manual_body_note",
                    "observedAt": "2026-04-15T09:00:00Z",
                    "bodyRegion": "chest",
                    "sensation": "tightness",
                    "activation": "high",
                    "linkedMaterialIds": ["material_charged"],
                    "linkedSymbolIds": ["symbol_snake"],
                    "linkedGoalIds": [],
                    "evidenceIds": [],
                    "privacyClass": "approved_summary",
                    "status": "active",
                    "createdAt": "2026-04-15T09:00:00Z",
                    "updatedAt": "2026-04-15T09:00:00Z",
                }
            )
            method_builder = CirculatioMethodContextBuilder(repository)
            adapter = ContextAdapter(
                repository,
                life_context_builder=CirculatioLifeContextBuilder(repository),
                method_context_builder=method_builder,
            )
            result = await adapter.build_material_input(
                {
                    "userId": "user_1",
                    "materialId": "material_new",
                    "materialType": "dream",
                    "materialText": "A serpent moved under the stairs.",
                    "materialDate": "2026-04-16T09:00:00Z",
                }
            )
            self.assertIn("methodContextSnapshot", result)
            self.assertEqual(
                result["methodContextSnapshot"]["consciousAttitude"]["id"], "attitude_1"
            )
            self.assertEqual(result["methodContextSnapshot"]["recentBodyStates"][0]["id"], "body_1")

        asyncio.run(run())

    def test_build_practice_input_includes_native_life_and_method_context(self) -> None:
        async def run() -> None:
            repository = InMemoryCirculatioRepository()
            await self._seed_native_records(repository)
            await repository.create_conscious_attitude_snapshot(
                {
                    "id": "attitude_1",
                    "userId": "user_1",
                    "source": "manual_checkin",
                    "status": "user_confirmed",
                    "windowStart": "2026-04-12T00:00:00Z",
                    "windowEnd": "2026-04-19T00:00:00Z",
                    "stanceSummary": "Trying to stay with the image.",
                    "activeValues": ["patience"],
                    "activeConflicts": [],
                    "avoidedThemes": [],
                    "confidence": "medium",
                    "evidenceIds": [],
                    "relatedMaterialIds": [],
                    "relatedGoalIds": [],
                    "privacyClass": "approved_summary",
                    "createdAt": "2026-04-15T09:00:00Z",
                    "updatedAt": "2026-04-15T09:00:00Z",
                }
            )
            adapter = ContextAdapter(
                repository,
                life_os=FakeLifeOs(),
                life_context_builder=CirculatioLifeContextBuilder(repository),
                method_context_builder=CirculatioMethodContextBuilder(repository),
            )
            result = await adapter.build_practice_input(
                {
                    "userId": "user_1",
                    "windowStart": "2026-04-12T00:00:00Z",
                    "windowEnd": "2026-04-19T00:00:00Z",
                    "trigger": {"triggerType": "manual"},
                    "explicitQuestion": "What practice fits the image?",
                }
            )
            self.assertEqual(result["lifeContextSnapshot"]["source"], "circulatio-backend")
            self.assertIn("recentPracticeSessions", result["methodContextSnapshot"])

        asyncio.run(run())

    def test_practice_input_works_without_material_id(self) -> None:
        async def run() -> None:
            repository = InMemoryCirculatioRepository()
            adapter = ContextAdapter(
                repository,
                life_context_builder=CirculatioLifeContextBuilder(repository),
                method_context_builder=CirculatioMethodContextBuilder(repository),
            )
            result = await adapter.build_practice_input(
                {
                    "userId": "user_1",
                    "windowStart": "2026-04-12T00:00:00Z",
                    "windowEnd": "2026-04-19T00:00:00Z",
                    "trigger": {"triggerType": "manual"},
                }
            )
            self.assertEqual(result["trigger"]["triggerType"], "manual")
            self.assertIn("hermesMemoryContext", result)

        asyncio.run(run())

    def test_method_context_includes_recent_practice_sessions(self) -> None:
        async def run() -> None:
            repository = InMemoryCirculatioRepository()
            await self._seed_native_records(repository)
            await repository.create_conscious_attitude_snapshot(
                {
                    "id": "attitude_1",
                    "userId": "user_1",
                    "source": "manual_checkin",
                    "status": "user_confirmed",
                    "windowStart": "2026-04-12T00:00:00Z",
                    "windowEnd": "2026-04-19T00:00:00Z",
                    "stanceSummary": "Trying to stay with the image.",
                    "activeValues": ["patience"],
                    "activeConflicts": [],
                    "avoidedThemes": [],
                    "confidence": "medium",
                    "evidenceIds": [],
                    "relatedMaterialIds": [],
                    "relatedGoalIds": [],
                    "privacyClass": "approved_summary",
                    "createdAt": "2026-04-15T09:00:00Z",
                    "updatedAt": "2026-04-15T09:00:00Z",
                }
            )
            method_builder = CirculatioMethodContextBuilder(repository)
            snapshot = await method_builder.build_method_context_snapshot(
                user_id="user_1",
                window_start="2026-04-12T00:00:00Z",
                window_end="2026-04-19T00:00:00Z",
            )
            self.assertIsNotNone(snapshot)
            assert snapshot is not None
            self.assertIn("recentPracticeSessions", snapshot)
            self.assertEqual(snapshot["recentPracticeSessions"][0]["practiceType"], "journaling")

        asyncio.run(run())


if __name__ == "__main__":
    unittest.main()
