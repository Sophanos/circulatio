from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from copy import deepcopy
from pathlib import Path
from unittest.mock import patch

from circulatio.ritual_renderer.providers import chutes
from circulatio.ritual_renderer.providers.chutes import ChutesProviderError
from circulatio.ritual_renderer.renderer import artifact_id_for_plan, render_plan_file


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
                    "--public-base",
                    "/artifacts/ritual_artifact_abcdef1234567890",
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
            self.assertEqual(
                [section["kind"] for section in manifest["sections"]],
                ["arrival", "breath", "reflection", "closing"],
            )
            self.assertEqual(manifest["sections"][1]["startMs"], 12000)
            self.assertEqual(manifest["sections"][1]["endMs"], 72000)
            self.assertEqual(manifest["sections"][-1]["endMs"], 300000)
            self.assertEqual(manifest["render"]["providers"], ["mock"])
            self.assertEqual(
                manifest["surfaces"]["captions"]["tracks"][0]["src"],
                "/artifacts/ritual_artifact_abcdef1234567890/captions.vtt",
            )
            self.assertIn("WEBVTT", captions_path.read_text(encoding="utf-8"))

    def test_manifest_explicit_sections_win_and_preserve_gaps(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            temp = Path(tempdir)
            plan = deepcopy(self._fixture_plan())
            plan["sections"] = [
                {
                    "id": "sec-arrival",
                    "kind": "arrival",
                    "title": "Arrival",
                    "startMs": 0,
                    "endMs": 12000,
                    "preferredLens": "breath",
                },
                {
                    "id": "sec-closing",
                    "kind": "closing",
                    "title": "Closing",
                    "startMs": 252000,
                    "endMs": 300000,
                    "preferredLens": "body",
                    "capturePrompt": "What did you notice?",
                },
            ]
            plan_path = temp / "plan.json"
            out_dir = temp / "artifact"
            plan_path.write_text(json.dumps({"plan": plan}), encoding="utf-8")

            manifest = render_plan_file(
                plan_path=plan_path,
                out_dir=out_dir,
                options={
                    "mockProviders": True,
                    "dryRun": True,
                    "publicBasePath": "/artifacts/test",
                },
            )

            self.assertEqual(
                [section["id"] for section in manifest["sections"]],
                [
                    "sec-arrival",
                    "sec-closing",
                ],
            )
            self.assertEqual(manifest["sections"][0]["endMs"], 12000)
            self.assertEqual(manifest["sections"][1]["startMs"], 252000)

    def test_artifact_id_for_plan_uses_stable_hash_prefix(self) -> None:
        self.assertEqual(
            artifact_id_for_plan(self._fixture_plan()),
            "ritual_artifact_abcdef1234567890",
        )

    def test_chutes_all_with_explicit_photo_podcast_surfaces_skips_music_and_cinema(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            temp = Path(tempdir)
            plan = deepcopy(self._fixture_plan())
            visual = plan["visualPromptPlan"]
            visual["image"] = {
                "enabled": True,
                "prompt": "A symbolic non literal threshold image.",
                "providerPromptPolicy": "sanitized_visual_only",
                "privacyNotes": ["no raw dream text"],
                "sourceRefIds": ["weekly_fixture"],
            }
            plan_path = temp / "plan.json"
            out_dir = temp / "artifact"
            plan_path.write_text(json.dumps({"plan": plan}), encoding="utf-8")

            def synthesize(*, out_path: Path, **_: object) -> dict[str, object]:
                out_path.write_bytes(b"audio")
                return {
                    "path": out_path,
                    "mimeType": "audio/wav",
                    "provider": "chutes",
                    "model": "chutes-kokoro",
                }

            def generate_picture(*, out_path: Path, **_: object) -> dict[str, object]:
                out_path.write_bytes(b"image")
                return {
                    "path": out_path,
                    "mimeType": "image/png",
                    "provider": "chutes",
                    "model": "chutes-z-image-turbo",
                }

            with patch.dict(os.environ, {"CHUTES_API_TOKEN": "test-token"}):
                with patch(
                    "circulatio.ritual_renderer.renderer.synthesize_speech", side_effect=synthesize
                ):
                    with patch(
                        "circulatio.ritual_renderer.renderer.transcribe_audio",
                        return_value={"segments": [{"start": 0, "end": 1.5, "text": "Hello."}]},
                    ):
                        with patch(
                            "circulatio.ritual_renderer.renderer.generate_image",
                            side_effect=generate_picture,
                        ):
                            with patch(
                                "circulatio.ritual_renderer.renderer.generate_music"
                            ) as music:
                                with patch(
                                    "circulatio.ritual_renderer.renderer.generate_video"
                                ) as video:
                                    manifest = render_plan_file(
                                        plan_path=plan_path,
                                        out_dir=out_dir,
                                        options={
                                            "providerProfile": "chutes_all",
                                            "surfaces": ["audio", "captions", "image"],
                                            "transcribeCaptions": True,
                                            "maxCostUsd": 0.05,
                                            "requestTimeoutSeconds": 5,
                                            "publicBasePath": "/artifacts/test",
                                        },
                                    )

            music.assert_not_called()
            video.assert_not_called()
            self.assertEqual(manifest["surfaces"]["audio"]["provider"], "chutes")
            self.assertEqual(manifest["surfaces"]["image"]["provider"], "chutes")
            self.assertNotIn("music", manifest["surfaces"])
            self.assertFalse(manifest["surfaces"]["cinema"]["enabled"])

    def test_chutes_speech_profile_without_token_writes_warning_manifest(self) -> None:
        root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as tempdir:
            temp = Path(tempdir)
            plan_path = temp / "plan.json"
            out_dir = temp / "artifact"
            plan_path.write_text(json.dumps({"plan": self._fixture_plan()}), encoding="utf-8")
            env = dict(os.environ)
            env.pop("CHUTES_API_TOKEN", None)

            subprocess.run(
                [
                    sys.executable,
                    str(root / "scripts" / "render_ritual_artifact.py"),
                    "--plan",
                    str(plan_path),
                    "--out",
                    str(out_dir),
                    "--provider-profile",
                    "chutes_speech",
                    "--surfaces",
                    "audio",
                    "--max-cost-usd",
                    "0.01",
                ],
                cwd=root,
                env=env,
                check=True,
                capture_output=True,
                text=True,
            )

            manifest = json.loads((out_dir / "manifest.json").read_text(encoding="utf-8"))
            self.assertIn("chutes_provider_missing_api_token", manifest["render"]["warnings"])
            self.assertEqual(manifest["surfaces"]["audio"]["provider"], "mock")

    def test_chutes_cinema_path_requires_beta_and_uses_generated_image(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            temp = Path(tempdir)
            plan = deepcopy(self._fixture_plan())
            plan["visualPromptPlan"]["image"] = {
                "enabled": True,
                "prompt": "A symbolic non literal threshold image.",
                "providerPromptPolicy": "sanitized_visual_only",
                "privacyNotes": ["no raw dream text"],
                "sourceRefIds": ["weekly_fixture"],
            }
            plan["visualPromptPlan"]["cinema"] = {
                "enabled": True,
                "providerPromptPolicy": "sanitized_visual_only",
                "maxDurationSeconds": 8,
                "storyboard": [
                    {
                        "id": "shot_1",
                        "prompt": "Slow non-literal movement through an abstract threshold field.",
                        "sourceRefIds": ["weekly_fixture"],
                        "durationMs": 8000,
                    }
                ],
            }
            plan_path = temp / "plan.json"
            out_dir = temp / "artifact"
            plan_path.write_text(json.dumps({"plan": plan}), encoding="utf-8")

            def generate_picture(*, out_path: Path, **_: object) -> dict[str, object]:
                out_path.write_bytes(b"image")
                return {
                    "path": out_path,
                    "mimeType": "image/png",
                    "provider": "chutes",
                    "model": "chutes-z-image-turbo",
                }

            video_inputs: list[str] = []

            def generate_movie(*, image: str, out_path: Path, **_: object) -> dict[str, object]:
                video_inputs.append(image)
                out_path.write_bytes(b"video")
                return {
                    "path": out_path,
                    "mimeType": "video/mp4",
                    "provider": "chutes",
                    "model": "chutes-wan-2-2-i2v-14b-fast",
                }

            with patch.dict(os.environ, {"CHUTES_API_TOKEN": "test-token"}):
                with patch(
                    "circulatio.ritual_renderer.renderer.generate_image",
                    side_effect=generate_picture,
                ):
                    with patch(
                        "circulatio.ritual_renderer.renderer.generate_video",
                        side_effect=generate_movie,
                    ):
                        manifest = render_plan_file(
                            plan_path=plan_path,
                            out_dir=out_dir,
                            options={
                                "providerProfile": "chutes_all",
                                "surfaces": ["image", "cinema"],
                                "maxCostUsd": 0.05,
                                "requestTimeoutSeconds": 5,
                                "allowBetaVideo": True,
                                "publicBasePath": "/artifacts/test",
                            },
                        )

            self.assertTrue(video_inputs)
            self.assertEqual(manifest["surfaces"]["image"]["provider"], "chutes")
            cinema = manifest["surfaces"]["cinema"]
            self.assertTrue(cinema["enabled"])
            self.assertEqual(cinema["provider"], "chutes")
            self.assertEqual(cinema["model"], "chutes-wan-2-2-i2v-14b-fast")
            self.assertEqual(cinema["posterSrc"], "/artifacts/test/image.png")
            self.assertEqual(cinema["playbackMode"], "transport_synced")
            self.assertEqual(cinema["presentation"], "full_background")
            self.assertTrue(cinema["checksum"])

    def test_chutes_cinema_skips_missing_sanitized_storyboard_without_prompt_fallback(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            temp = Path(tempdir)
            plan = deepcopy(self._fixture_plan())
            plan["text"]["summary"] = "Do not use this broad summary as a video prompt."
            plan["visualPromptPlan"]["cinema"] = {
                "enabled": True,
                "providerPromptPolicy": "sanitized_visual_only",
                "maxDurationSeconds": 8,
                "storyboard": [],
            }
            video_image = temp / "seed.png"
            video_image.write_bytes(b"image")
            plan_path = temp / "plan.json"
            out_dir = temp / "artifact"
            plan_path.write_text(json.dumps({"plan": plan}), encoding="utf-8")

            with patch.dict(os.environ, {"CHUTES_API_TOKEN": "test-token"}):
                with patch("circulatio.ritual_renderer.renderer.generate_video") as video:
                    manifest = render_plan_file(
                        plan_path=plan_path,
                        out_dir=out_dir,
                        options={
                            "providerProfile": "chutes_video",
                            "surfaces": ["cinema"],
                            "maxCostUsd": 0.05,
                            "allowBetaVideo": True,
                            "videoImage": str(video_image),
                        },
                    )

            video.assert_not_called()
            self.assertFalse(manifest["surfaces"]["cinema"]["enabled"])
            self.assertIn(
                "chutes_video_skipped_no_sanitized_storyboard",
                manifest["render"]["warnings"],
            )

    def test_chutes_wan_video_payload_matches_live_i2v_contract(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            temp = Path(tempdir)
            captured: dict[str, object] = {}

            def fake_post_asset(**kwargs: object) -> dict[str, object]:
                captured.update(kwargs)
                out_path = kwargs["out_path"]
                assert isinstance(out_path, Path)
                out_path.write_bytes(b"video")
                return {
                    "path": out_path,
                    "mimeType": "video/mp4",
                    "provider": "chutes",
                    "model": "chutes-wan-2-2-i2v-14b-fast",
                }

            with patch(
                "circulatio.ritual_renderer.providers.chutes._post_asset",
                side_effect=fake_post_asset,
            ):
                chutes.generate_video(
                    token="test-token",
                    prompt="Slow abstract movement.",
                    image="base64-image",
                    out_path=temp / "cinema.mp4",
                    timeout_seconds=9,
                )

            self.assertEqual(captured["url"], chutes.WAN_I2V_GENERATE_URL)
            payload = captured["payload"]
            self.assertIsInstance(payload, dict)
            payload = payload if isinstance(payload, dict) else {}
            self.assertEqual(payload["prompt"], "Slow abstract movement.")
            self.assertEqual(payload["image"], "base64-image")
            self.assertEqual(payload["frames"], 81)
            self.assertEqual(payload["resolution"], "480p")
            self.assertEqual(payload["fps"], 16)
            self.assertTrue(payload["fast"])
            self.assertEqual(payload["seed"], 42)
            self.assertEqual(payload["guidance_scale"], 1.0)
            self.assertEqual(payload["guidance_scale_2"], 1.0)

    def test_chutes_video_warning_is_sanitized(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            temp = Path(tempdir)
            plan = deepcopy(self._fixture_plan())
            plan["visualPromptPlan"]["cinema"] = {
                "enabled": True,
                "providerPromptPolicy": "sanitized_visual_only",
                "maxDurationSeconds": 8,
                "storyboard": [
                    {
                        "id": "shot_1",
                        "prompt": "PRIVATE PROMPT TEXT",
                        "sourceRefIds": ["weekly_fixture"],
                        "durationMs": 8000,
                    }
                ],
            }
            video_image = temp / "seed.png"
            video_image.write_bytes(b"image")
            plan_path = temp / "plan.json"
            out_dir = temp / "artifact"
            plan_path.write_text(json.dumps({"plan": plan}), encoding="utf-8")

            with patch.dict(os.environ, {"CHUTES_API_TOKEN": "test-token"}):
                with patch(
                    "circulatio.ritual_renderer.renderer.generate_video",
                    side_effect=ChutesProviderError("Chutes HTTP 500: PRIVATE PROMPT TEXT"),
                ):
                    manifest = render_plan_file(
                        plan_path=plan_path,
                        out_dir=out_dir,
                        options={
                            "providerProfile": "chutes_video",
                            "surfaces": ["cinema"],
                            "maxCostUsd": 0.05,
                            "allowBetaVideo": True,
                            "videoImage": str(video_image),
                        },
                    )

            warnings = manifest["render"]["warnings"]
            self.assertIn("chutes_video_failed:http_500", warnings)
            self.assertFalse(any("PRIVATE PROMPT TEXT" in warning for warning in warnings))

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
