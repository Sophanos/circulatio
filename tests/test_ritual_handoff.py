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
            policy = self._chutes_policy()

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
                {"audio": True, "captions": True, "image": True},
            )

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
                        render_policy=self._chutes_policy(),
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
                        render_policy=self._chutes_policy(),
                    )

            argv = run.call_args.args[0]
            self.assertIn("--mock-providers", argv)
            self.assertIn("ritual_handoff_chutes_skipped_missing_api_token", result["warnings"])

    def _handoff(self, temp: Path) -> tuple[HermesRitualArtifactHandoff, dict[str, object]]:
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
        return HermesRitualArtifactHandoff(config), self._plan()

    def _response(self, plan: dict[str, object]) -> dict[str, object]:
        return {
            "status": "ok",
            "requestId": "request_fixture",
            "result": {
                "plan": plan,
                "renderRequest": {
                    "allowedSurfaces": ["audio", "captions", "image", "cinema"],
                },
                "warnings": [],
            },
        }

    def _chutes_policy(self) -> dict[str, object]:
        return {
            "mode": "render_static",
            "externalProvidersAllowed": True,
            "providerAllowlist": ["mock", "chutes"],
            "providerProfile": "chutes_all",
            "surfaces": ["audio", "captions", "image", "cinema"],
            "transcribeCaptions": True,
            "requestTimeoutSeconds": 180,
            "maxCost": {"currency": "USD", "amount": 0.05},
        }

    def _fake_renderer(self, *, artifact_id: str, plan_id: str, provider: str = "mock"):
        def run(argv: list[str], **_: object) -> object:
            out_dir = Path(argv[argv.index("--out") + 1])
            self._write_manifest(
                out_dir, artifact_id=artifact_id, plan_id=plan_id, provider=provider
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
        manifest = {
            "schemaVersion": "hermes_ritual_artifact.v1",
            "artifactId": artifact_id,
            "planId": plan_id,
            "durationMs": 150000,
            "surfaces": {
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
            },
            "render": {
                "rendererVersion": "ritual-renderer.v1",
                "mode": "render_static" if provider == "chutes" else "dry_run_manifest",
                "providers": providers,
                "warnings": ["provider_warning"] if provider == "chutes" else [],
            },
        }
        (out_dir / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
        (out_dir / "captions.vtt").write_text("WEBVTT\n", encoding="utf-8")

    def _plan(self) -> dict[str, object]:
        return {
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
                "cinema": {"enabled": False},
            },
            "safetyBoundary": {
                "providerRestrictions": ["no_raw_material_to_external_provider"],
            },
        }


if __name__ == "__main__":
    unittest.main()
