from __future__ import annotations

import asyncio
import json
import unittest

from circulatio.hermes.runtime import (
    build_hermes_circulatio_runtime,
    build_in_memory_circulatio_runtime,
)
from circulatio_hermes_plugin.runtime import get_runtime, reset_runtimes, set_runtime
from circulatio_hermes_plugin.tools import (
    alive_today_tool,
    interpret_material_tool,
    journey_page_tool,
    record_interpretation_feedback_tool,
    store_reflection_tool,
)
from tests._helpers import FakeCirculatioLlm
from tests.journey_case_helpers import load_journey_case, seed_history_seed


class JourneyFamiliesBridgeTests(unittest.TestCase):
    def setUp(self) -> None:
        reset_runtimes()

    def _install_fake_runtime(self) -> None:
        set_runtime(build_hermes_circulatio_runtime(db_path=":memory:", llm=FakeCirculatioLlm()))

    def _install_in_memory_runtime(self) -> None:
        set_runtime(build_in_memory_circulatio_runtime(llm=FakeCirculatioLlm()))

    def _tool_kwargs(self, *, call_id: str, session_id: str = "sess_1") -> dict[str, object]:
        return {
            "platform": "cli",
            "profile": "default",
            "session_id": session_id,
            "message_id": call_id,
            "tool_call_id": call_id,
        }

    def test_journey_page_case_tool_stays_read_only(self) -> None:
        async def run() -> None:
            case = load_journey_case("journey_page_read_only_001")
            self._install_in_memory_runtime()
            runtime = get_runtime("default")
            await seed_history_seed(
                case=case,
                repository=runtime.repository,
                service=runtime.service,
                user_id="hermes:default:local",
            )

            before_reviews = await runtime.repository.list_weekly_reviews("hermes:default:local")
            response = json.loads(
                await journey_page_tool(
                    {
                        "windowStart": "2026-04-12T00:00:00Z",
                        "windowEnd": "2026-04-19T23:59:59Z",
                    },
                    **self._tool_kwargs(call_id="journey_case_journey_page"),
                )
            )
            after_reviews = await runtime.repository.list_weekly_reviews("hermes:default:local")

            self.assertEqual(response["status"], "ok")
            self.assertEqual(response["result"]["journeyPage"]["practiceContainer"]["kind"], "practice_follow_up")
            self.assertEqual(before_reviews, after_reviews)

        asyncio.run(run())

    def test_feedback_case_routes_to_feedback_tool_without_new_material(self) -> None:
        async def run() -> None:
            case = load_journey_case("feedback_correction_001")
            self.assertEqual(
                case["turns"][0]["expected"]["toolSequence"]["equals"],
                ["circulatio_record_interpretation_feedback"],
            )
            self._install_fake_runtime()
            stored = json.loads(
                await store_reflection_tool(
                    {"text": "A sharp image stayed after the conflict."},
                    **self._tool_kwargs(call_id="journey_case_feedback_store"),
                )
            )
            interpreted = json.loads(
                await interpret_material_tool(
                    {"materialId": stored["result"]["materialId"]},
                    **self._tool_kwargs(call_id="journey_case_feedback_interpret"),
                )
            )
            runtime = get_runtime("default")
            before_materials = await runtime.repository.list_materials("hermes:default:local")
            feedback = json.loads(
                await record_interpretation_feedback_tool(
                    {
                        "runId": interpreted["result"]["runId"],
                        "feedback": "too_much",
                        "note": "That missed me.",
                        "locale": "en-US",
                    },
                    **self._tool_kwargs(call_id="journey_case_feedback_record"),
                )
            )
            after_materials = await runtime.repository.list_materials("hermes:default:local")

            self.assertEqual(feedback["status"], "ok")
            self.assertEqual(len(before_materials), len(after_materials))

        asyncio.run(run())

    def test_reentry_case_uses_alive_today_surface_without_review_write(self) -> None:
        async def run() -> None:
            case = load_journey_case("practice_reentry_001")
            self._install_in_memory_runtime()
            runtime = get_runtime("default")
            await seed_history_seed(
                case=case,
                repository=runtime.repository,
                service=runtime.service,
                user_id="hermes:default:local",
            )

            before_reviews = await runtime.repository.list_weekly_reviews("hermes:default:local")
            response = json.loads(
                await alive_today_tool(
                    {
                        "windowStart": "2026-04-12T00:00:00Z",
                        "windowEnd": "2026-04-19T23:59:59Z",
                    },
                    **self._tool_kwargs(call_id="journey_case_alive_today"),
                )
            )
            after_reviews = await runtime.repository.list_weekly_reviews("hermes:default:local")

            self.assertEqual(response["status"], "ok")
            self.assertTrue(response["result"]["summaryId"])
            self.assertEqual(before_reviews, after_reviews)

        asyncio.run(run())


if __name__ == "__main__":
    unittest.main()
