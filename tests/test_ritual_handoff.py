from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from circulatio.ritual_renderer.renderer import artifact_id_for_plan
from circulatio_hermes_plugin.ritual_handoff import (
    HermesRitualArtifactHandoff,
    HermesRitualHandoffConfig,
)


class HermesRitualHandoffTests(unittest.TestCase):
    def test_handoff_defaults_to_mock_dry_run_renderer(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            temp = Path(tempdir)
            handoff, plan = self._handoff(temp)
            response = self._response(plan)
            artifact_id = artifact_id_for_plan(plan)

            with patch(
                "circulatio_hermes_plugin.ritual_handoff.subprocess.run",
                side_effect=self._fake_renderer(artifact_id=artifact_id, plan_id=str(plan["id"])),
            ) as run:
                result = handoff.render_from_bridge_response(response)

            argv = run.call_args.args[0]
            self.assertIn("--mock-providers", argv)
            self.assertIn("--dry-run", argv)
            self.assertNotIn("--provider-profile", argv)
            self.assertEqual(result["status"], "ok")
            artifact = result["artifact"]
            self.assertEqual(artifact["providers"], ["mock"])
            self.assertFalse(artifact["surfaces"]["audio"])
            self.assertTrue(artifact["surfaces"]["captions"])

    def test_handoff_uses_chutes_command_only_when_provider_gates_pass(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            temp = Path(tempdir)
            handoff, plan = self._handoff(temp)
            response = self._response(plan)
            artifact_id = artifact_id_for_plan(plan)
            policy = self._chutes_policy(surfaces=["audio", "captions", "image"])

            with patch.dict(os.environ, {"CHUTES_API_TOKEN": "test-token"}):
                with patch(
                    "circulatio_hermes_plugin.ritual_handoff.subprocess.run",
                    side_effect=self._fake_renderer(
                        artifact_id=artifact_id,
                        plan_id=str(plan["id"]),
                        provider="chutes",
                    ),
                ) as run:
                    result = handoff.render_from_bridge_response(response, render_policy=policy)

            argv = run.call_args.args[0]
            self.assertIn("--provider-profile", argv)
            self.assertIn("chutes_all", argv)
            self.assertIn("--surfaces", argv)
            self.assertEqual(argv[argv.index("--surfaces") + 1], "audio,captions,image")
            self.assertIn("--transcribe-captions", argv)
            self.assertIn("--max-cost-usd", argv)
            self.assertNotIn("--mock-providers", argv)
            self.assertNotIn("--dry-run", argv)
            self.assertGreaterEqual(run.call_args.kwargs["timeout"], 300)
            artifact = result["artifact"]
            self.assertEqual(artifact["providers"], ["mock", "chutes"])
            self.assertEqual(
                artifact["surfaces"],
                {"audio": True, "captions": True, "image": True, "cinema": False},
            )

    def test_handoff_passes_provider_backed_cinema_flags_when_all_gates_pass(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            temp = Path(tempdir)
            handoff, plan = self._handoff(temp, cinema_enabled=True)
            response = self._response(plan)
            artifact_id = artifact_id_for_plan(plan)
            video_image = str(temp / "seed.png")
            (temp / "seed.png").write_bytes(b"image")
            policy = self._chutes_policy(
                profile="chutes_video",
                surfaces=["cinema"],
                video_allowed=True,
                allow_beta_video=True,
                video_image=video_image,
            )

            with patch.dict(os.environ, {"CHUTES_API_TOKEN": "test-token"}):
                with patch(
                    "circulatio_hermes_plugin.ritual_handoff.subprocess.run",
                    side_effect=self._fake_renderer(
                        artifact_id=artifact_id,
                        plan_id=str(plan["id"]),
                        provider="chutes",
                    ),
                ) as run:
                    result = handoff.render_from_bridge_response(response, render_policy=policy)

            argv = run.call_args.args[0]
            self.assertEqual(argv[argv.index("--provider-profile") + 1], "chutes_video")
            self.assertEqual(argv[argv.index("--surfaces") + 1], "cinema")
            self.assertIn("--allow-beta-video", argv)
            self.assertEqual(argv[argv.index("--video-image") + 1], video_image)
            self.assertTrue(result["artifact"]["surfaces"]["cinema"])

    def test_handoff_passes_provider_backed_music_flags_when_all_gates_pass(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            temp = Path(tempdir)
            handoff, plan = self._handoff(temp, music_enabled=True)
            response = self._response(plan)
            artifact_id = artifact_id_for_plan(plan)
            policy = self._chutes_policy(
                profile="chutes_music",
                surfaces=["music"],
                allow_beta_music=True,
                music_steps=48,
            )

            with patch.dict(os.environ, {"CHUTES_API_TOKEN": "test-token"}):
                with patch(
                    "circulatio_hermes_plugin.ritual_handoff.subprocess.run",
                    side_effect=self._fake_renderer(
                        artifact_id=artifact_id,
                        plan_id=str(plan["id"]),
                        provider="chutes",
                    ),
                ) as run:
                    result = handoff.render_from_bridge_response(response, render_policy=policy)

            argv = run.call_args.args[0]
            self.assertEqual(argv[argv.index("--provider-profile") + 1], "chutes_music")
            self.assertEqual(argv[argv.index("--surfaces") + 1], "music")
            self.assertIn("--allow-beta-music", argv)
            self.assertEqual(argv[argv.index("--music-steps") + 1], "48")
            self.assertEqual(
                result["artifact"]["surfaces"]["music"],
                {"available": True, "provider": "chutes", "mimeType": "audio/wav"},
            )

    def test_music_request_without_beta_gate_falls_back_with_warning(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            temp = Path(tempdir)
            handoff, plan = self._handoff(temp, music_enabled=True)
            response = self._response(plan)
            artifact_id = artifact_id_for_plan(plan)
            policy = self._chutes_policy(
                profile="chutes_music",
                surfaces=["music"],
                allow_beta_music=False,
            )

            with patch.dict(os.environ, {"CHUTES_API_TOKEN": "test-token"}):
                with patch(
                    "circulatio_hermes_plugin.ritual_handoff.subprocess.run",
                    side_effect=self._fake_renderer(
                        artifact_id=artifact_id,
                        plan_id=str(plan["id"]),
                    ),
                ) as run:
                    result = handoff.render_from_bridge_response(response, render_policy=policy)

            argv = run.call_args.args[0]
            self.assertIn("--mock-providers", argv)
            self.assertIn("ritual_handoff_music_skipped_without_beta_gate", result["warnings"])

    def test_music_request_not_allowed_by_render_request_falls_back_with_warning(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            temp = Path(tempdir)
            handoff, plan = self._handoff(temp, music_enabled=True)
            response = self._response(plan, allowed_surfaces=["audio", "captions", "image"])
            artifact_id = artifact_id_for_plan(plan)
            policy = self._chutes_policy(
                profile="chutes_music",
                surfaces=["music"],
                allow_beta_music=True,
            )

            with patch.dict(os.environ, {"CHUTES_API_TOKEN": "test-token"}):
                with patch(
                    "circulatio_hermes_plugin.ritual_handoff.subprocess.run",
                    side_effect=self._fake_renderer(
                        artifact_id=artifact_id,
                        plan_id=str(plan["id"]),
                    ),
                ) as run:
                    result = handoff.render_from_bridge_response(response, render_policy=policy)

            argv = run.call_args.args[0]
            self.assertIn("--mock-providers", argv)
            self.assertIn("ritual_handoff_music_skipped_by_plan_policy", result["warnings"])

    def test_chutes_all_without_explicit_cinema_surface_does_not_enable_video(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            temp = Path(tempdir)
            handoff, plan = self._handoff(temp, cinema_enabled=True)
            response = self._response(plan)
            artifact_id = artifact_id_for_plan(plan)
            policy = self._chutes_policy(surfaces=None, allow_beta_video=True, video_allowed=True)

            with patch.dict(os.environ, {"CHUTES_API_TOKEN": "test-token"}):
                with patch(
                    "circulatio_hermes_plugin.ritual_handoff.subprocess.run",
                    side_effect=self._fake_renderer(
                        artifact_id=artifact_id,
                        plan_id=str(plan["id"]),
                        provider="chutes",
                    ),
                ) as run:
                    result = handoff.render_from_bridge_response(response, render_policy=policy)

            argv = run.call_args.args[0]
            self.assertEqual(argv[argv.index("--surfaces") + 1], "audio,captions,image")
            self.assertNotIn("--allow-beta-video", argv)
            self.assertFalse(result["artifact"]["surfaces"]["cinema"])

    def test_cinema_request_without_beta_gate_falls_back_with_warning(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            temp = Path(tempdir)
            handoff, plan = self._handoff(temp, cinema_enabled=True)
            response = self._response(plan)
            artifact_id = artifact_id_for_plan(plan)
            policy = self._chutes_policy(
                profile="chutes_video",
                surfaces=["cinema"],
                video_allowed=True,
                allow_beta_video=False,
            )

            with patch.dict(os.environ, {"CHUTES_API_TOKEN": "test-token"}):
                with patch(
                    "circulatio_hermes_plugin.ritual_handoff.subprocess.run",
                    side_effect=self._fake_renderer(
                        artifact_id=artifact_id,
                        plan_id=str(plan["id"]),
                    ),
                ) as run:
                    result = handoff.render_from_bridge_response(response, render_policy=policy)

            argv = run.call_args.args[0]
            self.assertIn("--mock-providers", argv)
            self.assertIn("ritual_handoff_cinema_skipped_without_beta_gate", result["warnings"])

    def test_existing_mock_manifest_does_not_block_provider_rerender(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            temp = Path(tempdir)
            handoff, plan = self._handoff(temp)
            response = self._response(plan)
            artifact_id = artifact_id_for_plan(plan)
            final_dir = temp / "public" / artifact_id
            final_dir.mkdir(parents=True)
            self._write_manifest(
                final_dir,
                artifact_id=artifact_id,
                plan_id=str(plan["id"]),
                provider="mock",
            )

            with patch.dict(os.environ, {"CHUTES_API_TOKEN": "test-token"}):
                with patch(
                    "circulatio_hermes_plugin.ritual_handoff.subprocess.run",
                    side_effect=self._fake_renderer(
                        artifact_id=artifact_id,
                        plan_id=str(plan["id"]),
                        provider="chutes",
                    ),
                ) as run:
                    result = handoff.render_from_bridge_response(
                        response,
                        render_policy=self._chutes_policy(surfaces=["audio", "captions", "image"]),
                    )

            self.assertTrue(run.called)
            manifest = json.loads((final_dir / "manifest.json").read_text(encoding="utf-8"))
            self.assertEqual(manifest["surfaces"]["audio"]["provider"], "chutes")
            self.assertEqual(result["artifact"]["providers"], ["mock", "chutes"])

    def test_missing_chutes_token_falls_back_to_mock_with_warning(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            temp = Path(tempdir)
            handoff, plan = self._handoff(temp)
            response = self._response(plan)
            artifact_id = artifact_id_for_plan(plan)
            env = dict(os.environ)
            env.pop("CHUTES_API_TOKEN", None)

            with patch.dict(os.environ, env, clear=True):
                with patch(
                    "circulatio_hermes_plugin.ritual_handoff.subprocess.run",
                    side_effect=self._fake_renderer(
                        artifact_id=artifact_id, plan_id=str(plan["id"])
                    ),
                ) as run:
                    result = handoff.render_from_bridge_response(
                        response,
                        render_policy=self._chutes_policy(surfaces=["audio", "captions", "image"]),
                    )

            argv = run.call_args.args[0]
            self.assertIn("--mock-providers", argv)
            self.assertIn("ritual_handoff_chutes_skipped_missing_api_token", result["warnings"])

    def _handoff(
        self, temp: Path, *, cinema_enabled: bool = False, music_enabled: bool = False
    ) -> tuple[HermesRitualArtifactHandoff, dict[str, object]]:
        script = temp / "render_ritual_artifact.py"
        script.write_text("", encoding="utf-8")
        config = HermesRitualHandoffConfig(
            repo_root=temp,
            renderer_script=script,
            plan_store_root=temp / "plans",
            artifact_public_root=temp / "public",
            base_url="http://localhost:3000",
            mode="render_static",
            open_local_default=False,
            renderer_timeout_seconds=60,
        )
        return HermesRitualArtifactHandoff(config), self._plan(
            cinema_enabled=cinema_enabled,
            music_enabled=music_enabled,
        )

    def _response(
        self, plan: dict[str, object], *, allowed_surfaces: list[str] | None = None
    ) -> dict[str, object]:
        if allowed_surfaces is None:
            allowed_surfaces = ["audio", "captions", "image", "cinema"]
            if isinstance(plan.get("music"), dict):
                allowed_surfaces.append("music")
        return {
            "status": "ok",
            "requestId": "request_fixture",
            "result": {
                "plan": plan,
                "renderRequest": {
                    "allowedSurfaces": allowed_surfaces,
                },
                "warnings": [],
            },
        }

    def _chutes_policy(
        self,
        *,
        profile: str = "chutes_all",
        surfaces: list[str] | None = None,
        video_allowed: bool = False,
        allow_beta_video: bool = False,
        allow_beta_music: bool = False,
        music_steps: int = 32,
        video_image: str = "",
    ) -> dict[str, object]:
        policy: dict[str, object] = {
            "mode": "render_static",
            "externalProvidersAllowed": True,
            "providerAllowlist": ["mock", "chutes"],
            "providerProfile": profile,
            "transcribeCaptions": True,
            "requestTimeoutSeconds": 180,
            "maxCost": {"currency": "USD", "amount": 0.05},
            "videoAllowed": video_allowed,
            "allowBetaVideo": allow_beta_video,
            "allowBetaMusic": allow_beta_music,
            "musicSteps": music_steps,
        }
        if surfaces is not None:
            policy["surfaces"] = surfaces
        if video_image:
            policy["videoImage"] = video_image
        return policy

    def _fake_renderer(self, *, artifact_id: str, plan_id: str, provider: str = "mock"):
        def run(argv: list[str], **_: object) -> object:
            out_dir = Path(argv[argv.index("--out") + 1])
            surfaces = ""
            if "--surfaces" in argv:
                surfaces = str(argv[argv.index("--surfaces") + 1])
            self._write_manifest(
                out_dir,
                artifact_id=artifact_id,
                plan_id=plan_id,
                provider=provider,
                cinema="cinema" in surfaces.split(","),
                music="music" in surfaces.split(","),
            )
            return object()

        return run

    def _write_manifest(
        self,
        out_dir: Path,
        *,
        artifact_id: str,
        plan_id: str,
        provider: str,
        cinema: bool = False,
        music: bool = False,
    ) -> None:
        out_dir.mkdir(parents=True, exist_ok=True)
        audio = {
            "src": None,
            "provider": "mock",
            "mimeType": None,
            "durationMs": None,
            "voiceId": "mock_steady",
            "checksum": None,
        }
        image = {"enabled": False, "src": None, "provider": None}
        cinema_surface = {
            "enabled": False,
            "src": None,
            "posterSrc": None,
            "mimeType": None,
            "durationMs": None,
            "provider": None,
        }
        music_surface = None
        providers = ["mock"]
        if provider == "chutes":
            providers.append("chutes")
            audio = {
                "src": f"/artifacts/{artifact_id}/audio.wav",
                "provider": "chutes",
                "mimeType": "audio/wav",
                "durationMs": None,
                "voiceId": "chutes-kokoro",
                "checksum": "audio-checksum",
            }
            image = {
                "enabled": True,
                "src": f"/artifacts/{artifact_id}/image.png",
                "provider": "chutes",
                "mimeType": "image/png",
                "checksum": "image-checksum",
            }
            if cinema:
                cinema_surface = {
                    "enabled": True,
                    "src": f"/artifacts/{artifact_id}/cinema.mp4",
                    "posterSrc": f"/artifacts/{artifact_id}/image.png",
                    "provider": "chutes",
                    "model": "chutes-wan-2-2-i2v-14b-fast",
                    "mimeType": "video/mp4",
                    "durationMs": None,
                    "checksum": "video-checksum",
                }
            if music:
                music_surface = {
                    "src": f"/artifacts/{artifact_id}/music.wav",
                    "provider": "chutes",
                    "model": "chutes-diffrhythm",
                    "mimeType": "audio/wav",
                    "durationMs": None,
                    "checksum": "music-checksum",
                }
        surfaces = {
            "text": {"body": "A rendered artifact."},
            "audio": audio,
            "captions": {
                "tracks": [
                    {
                        "src": f"/artifacts/{artifact_id}/captions.vtt",
                        "format": "webvtt",
                        "lang": "en-US",
                        "kind": "subtitles",
                        "label": "English",
                    }
                ],
                "segments": [
                    {"id": "seg_1", "startMs": 0, "endMs": 3000, "text": "Hello."},
                ],
            },
            "image": image,
            "cinema": cinema_surface,
        }
        if music_surface is not None:
            surfaces["music"] = music_surface
        manifest = {
            "schemaVersion": "hermes_ritual_artifact.v1",
            "artifactId": artifact_id,
            "planId": plan_id,
            "durationMs": 150000,
            "surfaces": surfaces,
            "render": {
                "rendererVersion": "ritual-renderer.v1",
                "mode": "render_static" if provider == "chutes" else "dry_run_manifest",
                "providers": providers,
                "warnings": ["provider_warning"] if provider == "chutes" else [],
            },
        }
        (out_dir / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
        (out_dir / "captions.vtt").write_text("WEBVTT\n", encoding="utf-8")

    def _plan(self, *, cinema_enabled: bool = False, music_enabled: bool = False) -> dict[str, object]:
        plan: dict[str, object] = {
            "id": "ritual_plan_fixture",
            "title": "Fixture podcast ritual",
            "locale": "en-US",
            "stableHash": "abcdef1234567890abcdef1234567890abcdef1234567890abcdef1234567890",
            "deliveryPolicy": {"renderMode": "render_static"},
            "voiceScript": {
                "segments": [
                    {
                        "id": "seg_opening",
                        "role": "opening",
                        "text": "Let this arrive as material already held.",
                    }
                ]
            },
            "visualPromptPlan": {
                "image": {
                    "enabled": True,
                    "prompt": "A symbolic non literal threshold image.",
                    "providerPromptPolicy": "sanitized_visual_only",
                },
                "cinema": {
                    "enabled": cinema_enabled,
                    "providerPromptPolicy": "sanitized_visual_only" if cinema_enabled else "none",
                    "storyboard": (
                        [
                            {
                                "id": "shot_1",
                                "prompt": "Slow non-literal symbolic motion.",
                                "sourceRefIds": ["weekly_fixture"],
                                "durationMs": 8000,
                            }
                        ]
                        if cinema_enabled
                        else []
                    ),
                },
            },
            "safetyBoundary": {
                "providerRestrictions": ["no_raw_material_to_external_provider"],
            },
        }
        if music_enabled:
            plan["music"] = {
                "enabled": True,
                "role": "ambient_bed",
                "sourceRefs": ["weekly_fixture"],
                "providerPromptPolicy": "none",
            }
        return plan


if __name__ == "__main__":
    unittest.main()
