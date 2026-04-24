from __future__ import annotations

import asyncio
import unittest

from tests.journey_case_helpers import build_service_fixture, load_journey_case, seed_history_seed


class JourneyFamiliesServiceTests(unittest.TestCase):
    def test_journey_page_case_stays_read_mostly(self) -> None:
        async def run() -> None:
            case = load_journey_case("journey_page_read_only_001")
            repository, service, _ = build_service_fixture()
            await seed_history_seed(
                case=case,
                repository=repository,
                service=service,
                user_id="user_1",
            )

            before_practices = await repository.list_practice_sessions("user_1")
            page = await service.generate_journey_page(
                {
                    "userId": "user_1",
                    "windowStart": "2026-04-12T00:00:00Z",
                    "windowEnd": "2026-04-19T23:59:59Z",
                }
            )
            after_practices = await repository.list_practice_sessions("user_1")
            reviews = await repository.list_weekly_reviews("user_1")

            self.assertEqual(page["practiceContainer"]["kind"], "practice_follow_up")
            self.assertEqual(len(after_practices), len(before_practices))
            self.assertEqual(reviews, [])

        asyncio.run(run())

    def test_reentry_alive_today_case_remains_ephemeral(self) -> None:
        async def run() -> None:
            case = load_journey_case("practice_reentry_001")
            repository, service, llm = build_service_fixture()
            await seed_history_seed(
                case=case,
                repository=repository,
                service=service,
                user_id="user_1",
            )

            before_reviews = await repository.list_weekly_reviews("user_1")
            summary = await service.generate_alive_today(
                user_id="user_1",
                window_start="2026-04-12T00:00:00Z",
                window_end="2026-04-19T23:59:59Z",
            )
            after_reviews = await repository.list_weekly_reviews("user_1")

            self.assertTrue(summary["summary"]["userFacingResponse"])
            self.assertEqual(before_reviews, after_reviews)
            self.assertEqual(len(llm.alive_today_calls), 1)

        asyncio.run(run())

    def test_embodied_recurrence_case_can_store_body_state_without_interpretation(self) -> None:
        async def run() -> None:
            case = load_journey_case("embodied_recurrence_003")
            repository, service, _ = build_service_fixture()
            turn = case["turns"][0]
            stored = await service.store_body_state(
                {
                    "userId": "user_1",
                    "sensation": "heart racing",
                    "observedAt": "2026-04-19T10:00:00Z",
                    "bodyRegion": "chest",
                    "activation": "overwhelming",
                    "noteText": turn["userTurn"],
                }
            )
            runs = await repository.list_interpretation_runs("user_1")

            self.assertEqual(stored["bodyState"]["activation"], "overwhelming")
            self.assertEqual(runs, [])

        asyncio.run(run())


if __name__ == "__main__":
    unittest.main()
