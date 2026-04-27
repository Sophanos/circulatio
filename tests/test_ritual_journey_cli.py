from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from tools.journey_cli_eval.ritual_mode import run_ritual_journey_eval


class RitualJourneyCliTests(unittest.TestCase):
    def test_ritual_eval_writes_report_bundle(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp = Path(temp_dir)
            report = run_ritual_journey_eval(
                output_root=temp / "runs",
                render_artifact_root=temp / "public" / "artifacts",
                plan_root=temp / "plans",
                run_id="ritual_test_run",
            )
            run_dir = Path(str(report["runDir"]))
            self.assertTrue(report["passed"], report["findings"])
            for name in (
                "report.json",
                "report.md",
                "timeline.json",
                "tool_calls.json",
                "browser_checks.json",
                "artifacts_checked.json",
            ):
                self.assertTrue((run_dir / name).exists(), name)
            self.assertTrue((run_dir / "screenshots").is_dir())

            artifacts = json.loads((run_dir / "artifacts_checked.json").read_text())
            browser_checks = json.loads((run_dir / "browser_checks.json").read_text())
            self.assertGreaterEqual(len(artifacts), 3)
            self.assertGreaterEqual(len(browser_checks), 3)
            self.assertTrue(
                any(
                    check["name"] == "completion_submit_works" and check["status"] == "pass"
                    for audit in browser_checks
                    for check in audit["checks"]
                )
            )
            self.assertTrue(
                any(
                    "ritual_handoff_chutes_skipped_missing_api_token"
                    in artifact.get("warnings", [])
                    for artifact in artifacts
                )
            )

            scorecard = report["scorecard"]
            self.assertEqual(scorecard["negative_cases"]["negative_no_consent"]["status"], "pass")
            self.assertEqual(scorecard["negative_cases"]["negative_zero_budget"]["status"], "pass")
            self.assertEqual(
                scorecard["negative_cases"]["negative_video_blocked"]["status"], "pass"
            )

            tool_calls_text = (run_dir / "tool_calls.json").read_text()
            self.assertIn("[redacted:", tool_calls_text)
            self.assertNotIn("I stood before a blue gate", tool_calls_text)
            self.assertIn("## JTBD", (run_dir / "report.md").read_text())


if __name__ == "__main__":
    unittest.main()
