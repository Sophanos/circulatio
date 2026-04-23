from __future__ import annotations

import os
import sys
import unittest

sys.path.insert(0, os.path.abspath("src"))

from circulatio.hermes.command_parser import CirculatioCommandParser
from circulatio.hermes.result_renderer import CirculatioResultRenderer


class JourneyExperimentHostSurfaceTests(unittest.TestCase):
    def test_command_parser_supports_journey_experiment_start(self) -> None:
        parser = CirculatioCommandParser()

        parsed = parser.parse(
            'journey experiment start --journey-label "Laundry return" --title "Current tending" '
            '--summary "Stay with the thread lightly." --body-first'
        )

        self.assertEqual(parsed.operation, "circulatio.journey.experiment.start")
        self.assertEqual(parsed.payload["journeyLabel"], "Laundry return")
        self.assertEqual(parsed.payload["title"], "Current tending")
        self.assertTrue(parsed.payload["bodyFirst"])

    def test_command_parser_supports_journey_experiment_quiet(self) -> None:
        parser = CirculatioCommandParser()

        parsed = parser.parse("journey experiment quiet experiment_1")

        self.assertEqual(parsed.operation, "circulatio.journey.experiment.respond")
        self.assertEqual(parsed.payload["experimentId"], "experiment_1")
        self.assertEqual(parsed.payload["action"], "quiet")

    def test_result_renderer_renders_journey_experiment(self) -> None:
        renderer = CirculatioResultRenderer()

        rendered = renderer.render(
            {
                "requestId": "req_1",
                "idempotencyKey": "key_1",
                "replayed": False,
                "status": "ok",
                "message": "Started current tending for this journey.",
                "result": {
                    "experimentId": "experiment_1",
                    "journeyExperiment": {
                        "id": "experiment_1",
                        "journeyId": "journey_1",
                        "title": "Current tending",
                        "summary": "Stay with the thread lightly.",
                        "status": "active",
                        "preferredMoveKind": "ask_body_checkin",
                    },
                },
                "pendingProposals": [],
                "affectedEntityIds": [],
                "errors": [],
            }
        )

        self.assertIn("Current tending: Current tending (active)", rendered)
        self.assertIn("Experiment id: experiment_1", rendered)
        self.assertIn("Quiet: /circulation journey experiment quiet experiment_1", rendered)


if __name__ == "__main__":
    unittest.main()
