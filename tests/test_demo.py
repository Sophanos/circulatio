from __future__ import annotations

import asyncio
import os
import sys
import unittest

sys.path.insert(0, os.path.abspath("src"))

import demo


class RoadmapDemoTests(unittest.TestCase):
    def test_demo_runs_tool_and_command_paths(self) -> None:
        result = asyncio.run(demo.run_demo())

        tool_labels = [str(item["label"]) for item in result["toolScenarios"]]
        self.assertIn("Hold-first reflection capture via Hermes tool intent", tool_labels)
        self.assertIn(
            "Autonomous journey container created from a recurring held thread",
            tool_labels,
        )
        self.assertIn("Journey page assembles a read-mostly host surface", tool_labels)
        self.assertIn("Threshold review for a liminal period", tool_labels)
        self.assertIn("Living myth review for chapter-scale synthesis", tool_labels)
        self.assertIn("Bounded analysis packet for journaling or analysis prep", tool_labels)

        responses = [item["response"] for item in result["toolScenarios"]]
        self.assertTrue(all(response["status"] == "ok" for response in responses))
        self.assertTrue(any(response.get("pendingProposals") for response in responses))

        commands = [str(item["rawArgs"]) for item in result["commandScenarios"]]
        self.assertTrue(any(command.startswith("reflect ") for command in commands))
        self.assertTrue(any(command.startswith("journey ") for command in commands))
        self.assertTrue(any(command.startswith("packet ") for command in commands))

        transcript = demo.render_demo(result)
        self.assertIn(
            "I was thinking why I always think about her when Im doing my wash.", transcript
        )
        self.assertIn("## Tool Scenarios", transcript)
        self.assertIn("## Command Scenarios", transcript)
        self.assertIn("circulatio_store_reflection", transcript)
        self.assertIn("circulatio_create_journey", transcript)
        self.assertIn("circulatio_journey_page", transcript)
        self.assertIn("/circulation reflect", transcript)
        self.assertIn("/circulation journey", transcript)


if __name__ == "__main__":
    unittest.main()
