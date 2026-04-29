from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from tools.journey_cli_eval.browser_driver import (
    BrowserDriverConfig,
    BrowserDriverTask,
    run_browser_driver_task,
)
from tools.journey_cli_eval.ritual_mode import (
    RitualJourneyConfig,
    _browser_e2e_status,
    _merge_browser_driver_result,
    _render_markdown,
    _stable_guidance_session_id,
    run_ritual_journey_eval,
)


class RitualJourneyCliTests(unittest.TestCase):
    def test_ritual_eval_writes_report_bundle(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp = Path(temp_dir)
            report = run_ritual_journey_eval(
                output_root=temp / "runs",
                render_artifact_root=temp / "public" / "artifacts",
                plan_root=temp / "plans",
                browser_driver="off",
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
                "browser_driver_results.json",
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
            self.assertIn("## Browser Driver", (run_dir / "report.md").read_text())

    def test_stable_guidance_session_id_matches_typescript_contract(self) -> None:
        self.assertEqual(
            _stable_guidance_session_id(
                host_session_id="host-1", artifact_id="artifact-1", user_id="user-1"
            ),
            "guidance_eaje5c",
        )
        self.assertEqual(
            _stable_guidance_session_id(
                host_session_id="artifact:ritual-river-gate",
                artifact_id="ritual-river-gate",
                user_id="local-user",
            ),
            "guidance_5xetby",
        )

    def test_browser_driver_unavailable_skips_without_requirement(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp = Path(temp_dir)
            result = run_browser_driver_task(
                BrowserDriverConfig(
                    enabled=True,
                    driver="agent-browser",
                    command="definitely-missing-agent-browser",
                    required=False,
                    base_url="http://localhost:3000",
                    timeout_seconds=1,
                    screenshots_dir=temp / "screenshots",
                    run_dir=temp,
                ),
                BrowserDriverTask(
                    artifact_id="artifact-1",
                    artifact_url="http://localhost:3000/artifacts/artifact-1",
                    live_url="http://localhost:3000/live/guidance-1?artifactId=artifact-1",
                    completion_endpoint="/api/artifacts/artifact-1/complete",
                    idempotency_key="completion-1",
                    guidance_session_id="guidance-1",
                ),
            ).to_json()

        self.assertEqual(result["status"], "skip")
        self.assertEqual(result["reason"], "agent_browser_not_found")

    def test_required_browser_driver_skip_fails_e2e_score(self) -> None:
        config = RitualJourneyConfig(
            run_id="test",
            run_dir=Path("/tmp/ritual-test"),
            artifact_root=Path("/tmp/artifacts"),
            plan_root=Path("/tmp/plans"),
            base_url="http://localhost:3000",
            provider_profile="mock",
            live_providers=False,
            include_video=False,
            include_music=False,
            allow_beta_video=False,
            allow_beta_music=False,
            max_cost_usd=0.0,
            chutes_token_env="CHUTES_API_TOKEN",
            transcription_provider="fallback",
            openai_api_key_env="OPENAI_API_KEY",
            openai_transcription_model="whisper-1",
            http_check=False,
            request_timeout_seconds=180,
            browser_driver="agent-browser",
            browser_driver_command="definitely-missing-agent-browser",
            require_browser_driver=True,
            browser_timeout_seconds=1,
        )
        status = _browser_e2e_status(
            [
                {
                    "checks": [
                        {
                            "name": "browser_driver_available",
                            "status": "skip",
                            "detail": "agent_browser_not_found",
                        }
                    ]
                }
            ],
            "browser_driver_available",
            config=config,
        )

        self.assertEqual(status["status"], "fail")

    def test_browser_driver_result_merge_adds_expected_checks(self) -> None:
        config = RitualJourneyConfig(
            run_id="test",
            run_dir=Path("/tmp/ritual-test"),
            artifact_root=Path("/tmp/artifacts"),
            plan_root=Path("/tmp/plans"),
            base_url="http://localhost:3000",
            provider_profile="mock",
            live_providers=False,
            include_video=False,
            include_music=False,
            allow_beta_video=False,
            allow_beta_music=False,
            max_cost_usd=0.0,
            chutes_token_env="CHUTES_API_TOKEN",
            transcription_provider="fallback",
            openai_api_key_env="OPENAI_API_KEY",
            openai_transcription_model="whisper-1",
            http_check=False,
            request_timeout_seconds=180,
            browser_driver="agent-browser",
            browser_driver_command="agent-browser",
            require_browser_driver=False,
            browser_timeout_seconds=180,
        )
        audit = {"checks": []}
        artifact = {"artifactId": "artifact-1", "liveUrl": "http://localhost:3000/live/guidance-1"}
        result = {
            "status": "skip",
            "reason": "agent_browser_not_found",
            "live_url": artifact["liveUrl"],
            "screenshots": [],
            "steps": [
                {
                    "name": "browser_driver_available",
                    "status": "skip",
                    "detail": "agent-browser not found",
                }
            ],
            "completion_post": {},
        }

        _merge_browser_driver_result(audit, artifact, result, config=config)
        check_names = {check["name"] for check in audit["checks"]}

        self.assertIn("browser_driver_available", check_names)
        self.assertIn("browser_live_route_handoff", check_names)
        self.assertEqual(artifact["browserDriverResult"], "skip")

    def test_browser_driver_markdown_includes_live_url(self) -> None:
        markdown = _render_markdown(
            report={
                "runId": "test",
                "passed": True,
                "jtbd": [],
                "selectedToolSequence": [],
                "scorecard": {},
                "findings": [],
                "nextEnhancements": [],
                "browserDriver": {"driver": "agent-browser", "required": False},
            },
            artifacts=[],
            browser_checks=[],
            browser_driver_results=[
                {
                    "artifact_id": "artifact-1",
                    "status": "skip",
                    "reason": "agent_browser_not_found",
                    "artifact_url": "http://localhost:3000/artifacts/artifact-1",
                    "live_url": "http://localhost:3000/live/guidance-1?artifactId=artifact-1",
                    "completion_post": {},
                    "screenshots": [],
                }
            ],
        )

        self.assertIn("## Browser Driver", markdown)
        self.assertIn("http://localhost:3000/live/guidance-1?artifactId=artifact-1", markdown)


if __name__ == "__main__":
    unittest.main()
