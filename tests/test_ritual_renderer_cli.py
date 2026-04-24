from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


class RitualRendererCliTests(unittest.TestCase):
    def test_render_ritual_artifact_dry_run_writes_manifest_and_captions(self) -> None:
        root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as tempdir:
            temp = Path(tempdir)
            plan_path = temp / "plan.json"
            out_dir = temp / "artifact"
            plan_path.write_text(json.dumps({"plan": self._fixture_plan()}), encoding="utf-8")

            completed = subprocess.run(
                [
                    sys.executable,
                    str(root / "scripts" / "render_ritual_artifact.py"),
                    "--plan",
                    str(plan_path),
                    "--out",
                    str(out_dir),
                    "--mock-providers",
                    "--dry-run",
                ],
                cwd=root,
                check=True,
                capture_output=True,
                text=True,
            )

            cli_result = json.loads(completed.stdout)
            manifest_path = out_dir / "manifest.json"
            captions_path = out_dir / "captions.vtt"
            self.assertEqual(cli_result["manifest"], str(manifest_path))
            self.assertTrue(manifest_path.exists())
            self.assertTrue(captions_path.exists())

            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            self.assertEqual(manifest["schemaVersion"], "hermes_ritual_artifact.v1")
            self.assertEqual(manifest["planId"], "ritual_plan_fixture")
            self.assertTrue(manifest["surfaces"]["breath"]["enabled"])
            self.assertTrue(manifest["surfaces"]["meditation"]["enabled"])
            self.assertTrue(manifest["surfaces"]["captions"]["segments"])
            self.assertEqual(manifest["render"]["providers"], ["mock"])
            self.assertIn("WEBVTT", captions_path.read_text(encoding="utf-8"))

    def _fixture_plan(self) -> dict[str, object]:
        return {
            "id": "ritual_plan_fixture",
            "schemaVersion": "circulatio.presentation.plan.v1",
            "userId": "user_1",
            "title": "Fixture ritual",
            "ritualIntent": "weekly_integration",
            "narrativeMode": "hybrid",
            "sourceType": "weekly_review_summary",
            "sourceRefs": [
                {
                    "sourceType": "weekly_review",
                    "recordId": "weekly_fixture",
                    "role": "primary",
                    "title": "Weekly review",
                    "evidenceIds": [],
                    "approvalState": "read_only_generated",
                }
            ],
            "generatedAt": "2026-04-24T09:00:00Z",
            "windowStart": "2026-04-12T00:00:00Z",
            "windowEnd": "2026-04-19T23:59:59Z",
            "privacyClass": "private",
            "locale": "en-US",
            "duration": {"targetSeconds": 300, "minSeconds": 180, "maxSeconds": 480},
            "text": {
                "summary": "A fixture ritual.",
                "body": "Let this arrive as material already held. Take a measured breath.",
            },
            "voiceScript": {
                "segments": [
                    {
                        "id": "seg_opening",
                        "role": "opening",
                        "text": "Let this arrive as material already held.",
                        "pace": "measured",
                        "tone": "steady",
                        "pauseAfterMs": 1200,
                        "sourceRefIds": ["weekly_fixture"],
                    },
                    {
                        "id": "seg_breath",
                        "role": "breath_instruction",
                        "text": "Take a measured breath and lengthen the exhale.",
                        "pace": "measured",
                        "tone": "steady",
                        "pauseAfterMs": 1600,
                        "sourceRefIds": [],
                    },
                ],
                "silenceMarkers": [],
                "contraindications": [],
            },
            "speechMarkupPlan": {
                "format": "structured_intent",
                "ssmlAllowed": False,
                "pausePolicy": "renderer_may_render_pauses",
            },
            "breath": {
                "enabled": True,
                "pattern": "lengthened_exhale",
                "inhaleSeconds": 4,
                "holdSeconds": 0,
                "exhaleSeconds": 6,
                "restSeconds": 2,
                "cycles": 5,
                "visualForm": "pacer",
                "syncMarkers": [],
            },
            "meditation": {
                "enabled": True,
                "fieldType": "coherence_convergence",
                "durationMs": 180000,
                "sourceRefs": ["weekly_fixture"],
                "macroProgressPolicy": "session_progress",
                "microMotion": "convergence",
                "instructionDensity": "sparse",
                "safetyBoundary": "grounding_only_if_activation_high",
                "syncMarkers": [],
            },
            "visualPromptPlan": {
                "image": {
                    "enabled": False,
                    "privacyNotes": ["no raw dream text"],
                    "sourceRefIds": ["weekly_fixture"],
                },
                "cinema": {"enabled": False, "storyboard": [], "maxDurationSeconds": 30},
            },
            "interactionSpec": {
                "finishPrompt": "What did you notice?",
                "captureReactionTime": False,
                "captureBodyResponse": True,
                "maxPrompts": 1,
            },
            "deliveryPolicy": {
                "renderMode": "dry_run_manifest",
                "frontendRoute": "/artifacts/{artifactId}",
            },
            "safetyBoundary": {
                "depthWorkAllowed": True,
                "blockedSurfaces": [],
                "groundingInstruction": "Stop if this increases activation; orient to the room.",
                "providerRestrictions": ["no_raw_material_to_external_provider"],
            },
            "provenance": {
                "evidenceIds": [],
                "contextSnapshotIds": [],
                "threadKeys": [],
                "generatedFromSurface": "weekly_review_summary",
            },
            "stableHash": "abcdef1234567890abcdef1234567890abcdef1234567890abcdef1234567890",
        }

