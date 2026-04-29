from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import webbrowser
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import cast

from circulatio.hermes.agent_bridge_contracts import BridgeResponseEnvelope
from circulatio.ritual_renderer.env import token_from_env_or_file
from circulatio.ritual_renderer.renderer import (
    MANIFEST_SCHEMA_VERSION,
    RENDERER_VERSION,
    artifact_id_for_plan,
)

_PROVIDER_SURFACES = {"audio", "captions", "image", "cinema", "music"}
_VIDEO_PROVIDER_PROFILES = {"chutes_video", "chutes_all"}
_MUSIC_PROVIDER_PROFILES = {"chutes_music", "chutes_all"}


@dataclass(frozen=True)
class HermesRitualHandoffConfig:
    repo_root: Path
    renderer_script: Path
    plan_store_root: Path
    artifact_public_root: Path
    base_url: str
    mode: str
    open_local_default: bool
    renderer_timeout_seconds: int

    @classmethod
    def from_env(cls) -> HermesRitualHandoffConfig:
        repo_root = Path(
            os.environ.get("CIRCULATIO_REPO_ROOT") or Path(__file__).resolve().parents[2]
        ).resolve()
        renderer_script = Path(
            os.environ.get("CIRCULATIO_RENDERER_SCRIPT")
            or repo_root / "scripts" / "render_ritual_artifact.py"
        ).resolve()
        plan_store_root = Path(
            os.environ.get("CIRCULATIO_RITUAL_PLAN_ROOT")
            or repo_root / "artifacts" / "rituals" / "plans"
        ).resolve()
        artifact_public_root = Path(
            os.environ.get("CIRCULATIO_RITUAL_ARTIFACT_ROOT")
            or repo_root / "apps" / "hermes-rituals-web" / "public" / "artifacts"
        ).resolve()
        timeout_raw = os.environ.get("CIRCULATIO_RITUAL_RENDER_TIMEOUT_SECONDS", "60")
        try:
            timeout = max(int(timeout_raw), 1)
        except ValueError:
            timeout = 60
        mode = os.environ.get("CIRCULATIO_RITUAL_HANDOFF_MODE", "render_static")
        if mode not in {"render_static", "plan_only"}:
            mode = "render_static"
        return cls(
            repo_root=repo_root,
            renderer_script=renderer_script,
            plan_store_root=plan_store_root,
            artifact_public_root=artifact_public_root,
            base_url=os.environ.get("CIRCULATIO_RITUALS_BASE_URL", "http://localhost:3000").rstrip(
                "/"
            ),
            mode=mode,
            open_local_default=os.environ.get("CIRCULATIO_RITUAL_OPEN") == "1",
            renderer_timeout_seconds=timeout,
        )


@dataclass(frozen=True)
class HermesHandoffRenderOptions:
    provider_profile: str
    surfaces: list[str]
    max_cost_usd: float
    transcribe_captions: bool
    transcription_provider: str
    openai_api_key_env: str
    openai_transcription_model: str
    openai_transcription_response_format: str
    request_timeout_seconds: int
    chutes_token_env: str
    allow_beta_video: bool
    allow_beta_music: bool
    music_steps: int
    music_duration_seconds: int
    video_image: str
    provider_backed: bool
    warnings: list[str]


class HermesRitualArtifactHandoff:
    def __init__(self, config: HermesRitualHandoffConfig | None = None) -> None:
        self._config = config or HermesRitualHandoffConfig.from_env()

    def render_from_bridge_response(
        self,
        response: BridgeResponseEnvelope,
        *,
        open_local: bool = False,
        render_policy: dict[str, object] | None = None,
    ) -> dict[str, object]:
        if self._config.mode == "plan_only":
            return {"status": "skipped", "warnings": []}
        result = response.get("result")
        if response.get("status") != "ok" or not isinstance(result, dict):
            return {"status": "skipped", "warnings": []}
        plan = result.get("plan")
        if not isinstance(plan, dict):
            return {"status": "skipped", "warnings": []}

        try:
            return self._render(
                response=response,
                result=result,
                plan=cast(dict[str, object], plan),
                open_local=open_local or self._config.open_local_default,
                render_policy=render_policy,
            )
        except subprocess.TimeoutExpired:
            return self._failure(retryable=True)
        except (OSError, subprocess.CalledProcessError) as exc:
            return self._failure(retryable=True, detail=str(exc))
        except ValueError as exc:
            return self._failure(retryable=False, detail=str(exc))

    def _render(
        self,
        *,
        response: BridgeResponseEnvelope,
        result: dict[str, object],
        plan: dict[str, object],
        open_local: bool,
        render_policy: dict[str, object] | None,
    ) -> dict[str, object]:
        plan_id = str(plan.get("id") or result.get("planId") or "").strip()
        if not plan_id:
            raise ValueError("Ritual plan id is required for local handoff.")
        artifact_id = artifact_id_for_plan(plan)
        public_base = f"/artifacts/{artifact_id}"
        route = f"/artifacts/{artifact_id}"
        url = f"{self._config.base_url}{route}"
        plan_path = self._persist_plan(response=response, result=result, plan=plan, plan_id=plan_id)
        render_options = self._render_options(
            render_policy=render_policy,
            result=result,
            plan=plan,
        )
        final_dir = self._config.artifact_public_root / artifact_id
        final_manifest = final_dir / "manifest.json"
        if (
            final_manifest.exists()
            and self._manifest_valid(final_manifest, artifact_id, plan_id)
            and self._manifest_satisfies_render_request(final_manifest, render_options)
        ):
            return self._success(
                artifact_id=artifact_id,
                url=url,
                route=route,
                public_base=public_base,
                plan_path=plan_path,
                manifest_path=final_manifest,
                opened=self._open_if_requested(url, open_local),
                handoff_warnings=render_options.warnings,
            )

        request_short = str(response.get("requestId") or "request")[-12:].replace(os.sep, "_")
        staging_dir = self._config.artifact_public_root / f".tmp-{artifact_id}-{request_short}"
        shutil.rmtree(staging_dir, ignore_errors=True)
        staging_dir.parent.mkdir(parents=True, exist_ok=True)
        try:
            self._run_renderer(
                plan_path=plan_path,
                out_dir=staging_dir,
                public_base=public_base,
                options=render_options,
            )
            staging_manifest = staging_dir / "manifest.json"
            if not self._manifest_valid(staging_manifest, artifact_id, plan_id):
                raise ValueError("Rendered ritual artifact manifest failed validation.")
            if (
                final_manifest.exists()
                and self._manifest_valid(final_manifest, artifact_id, plan_id)
                and self._manifest_satisfies_render_request(final_manifest, render_options)
            ):
                shutil.rmtree(staging_dir, ignore_errors=True)
            else:
                if final_dir.exists():
                    backup = final_dir.with_name(f"{final_dir.name}.bak-{request_short}")
                    shutil.rmtree(backup, ignore_errors=True)
                    final_dir.replace(backup)
                staging_dir.replace(final_dir)
        except (subprocess.TimeoutExpired, subprocess.CalledProcessError, OSError, ValueError):
            shutil.rmtree(staging_dir, ignore_errors=True)
            raise

        return self._success(
            artifact_id=artifact_id,
            url=url,
            route=route,
            public_base=public_base,
            plan_path=plan_path,
            manifest_path=final_manifest,
            opened=self._open_if_requested(url, open_local),
            handoff_warnings=render_options.warnings,
        )

    def _persist_plan(
        self,
        *,
        response: BridgeResponseEnvelope,
        result: dict[str, object],
        plan: dict[str, object],
        plan_id: str,
    ) -> Path:
        self._config.plan_store_root.mkdir(parents=True, exist_ok=True)
        plan_path = self._config.plan_store_root / f"{plan_id}.json"
        payload = {
            "schemaVersion": "circulatio.presentation.handoff_plan.v1",
            "createdAt": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
            "source": "hermes_plugin_local_handoff",
            "requestId": response.get("requestId"),
            "idempotencyKey": response.get("idempotencyKey"),
            "plan": plan,
            "renderRequest": result.get("renderRequest"),
            "costEstimate": result.get("costEstimate"),
            "warnings": result.get("warnings", []),
        }
        tmp_path = plan_path.with_suffix(plan_path.suffix + ".tmp")
        tmp_path.write_text(
            json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        with tmp_path.open("r+b") as handle:
            handle.flush()
            os.fsync(handle.fileno())
        tmp_path.replace(plan_path)
        return plan_path

    def _run_renderer(
        self,
        *,
        plan_path: Path,
        out_dir: Path,
        public_base: str,
        options: HermesHandoffRenderOptions,
    ) -> None:
        if not self._config.renderer_script.exists():
            renderer_path = self._display_path(self._config.renderer_script)
            raise OSError(f"Renderer script not found: {renderer_path}")
        argv = [
            sys.executable,
            str(self._config.renderer_script),
            "--plan",
            str(plan_path),
            "--out",
            str(out_dir),
            "--public-base",
            public_base,
        ]
        timeout = self._config.renderer_timeout_seconds
        if options.provider_backed:
            argv.extend(
                [
                    "--provider-profile",
                    options.provider_profile,
                    "--surfaces",
                    ",".join(options.surfaces),
                    "--max-cost-usd",
                    str(options.max_cost_usd),
                    "--request-timeout-seconds",
                    str(options.request_timeout_seconds),
                    "--chutes-token-env",
                    options.chutes_token_env,
                ]
            )
            if options.transcribe_captions:
                argv.append("--transcribe-captions")
            if options.transcription_provider:
                argv.extend(["--transcription-provider", options.transcription_provider])
            if options.openai_api_key_env:
                argv.extend(["--openai-api-key-env", options.openai_api_key_env])
            if options.openai_transcription_model:
                argv.extend(
                    ["--openai-transcription-model", options.openai_transcription_model]
                )
            if options.openai_transcription_response_format:
                argv.extend(
                    [
                        "--openai-transcription-response-format",
                        options.openai_transcription_response_format,
                    ]
                )
            if options.allow_beta_video and "cinema" in options.surfaces:
                argv.append("--allow-beta-video")
            if "music" in options.surfaces:
                argv.extend(["--music-steps", str(options.music_steps)])
                if options.music_duration_seconds > 0:
                    argv.extend(
                        ["--music-duration-seconds", str(options.music_duration_seconds)]
                    )
            if options.allow_beta_music and "music" in options.surfaces:
                argv.append("--allow-beta-music")
            if options.video_image and "cinema" in options.surfaces:
                argv.extend(["--video-image", options.video_image])
            timeout = max(timeout, 300, options.request_timeout_seconds * 3 + 30)
            if "music" in options.surfaces:
                timeout = max(timeout, 930)
        else:
            argv.extend(["--mock-providers", "--dry-run"])
        subprocess.run(
            argv,
            cwd=self._config.repo_root,
            check=True,
            capture_output=True,
            text=True,
            timeout=timeout,
        )

    def _render_options(
        self,
        *,
        render_policy: dict[str, object] | None,
        result: dict[str, object],
        plan: dict[str, object],
    ) -> HermesHandoffRenderOptions:
        policy = render_policy or {}
        warnings: list[str] = []
        profile = str(policy.get("providerProfile") or "mock").strip()
        mode = str(policy.get("mode") or "dry_run_manifest").strip()
        requested = self._requested_provider_surfaces(policy.get("surfaces"))
        if not requested:
            requested = ["audio", "captions", "image"]
        allowed = set(self._result_allowed_surfaces(result))
        selected = [
            surface for surface in requested if surface in allowed and surface in _PROVIDER_SURFACES
        ]
        provider_allowlist = self._provider_allowlist(policy.get("providerAllowlist"))
        max_cost = self._max_cost_usd(policy)
        timeout = self._positive_int(policy.get("requestTimeoutSeconds"), default=180)
        token_env = (
            str(policy.get("chutesTokenEnv") or "CHUTES_API_TOKEN").strip() or "CHUTES_API_TOKEN"
        )
        openai_key_env = (
            str(policy.get("openaiApiKeyEnv") or "OPENAI_API_KEY").strip() or "OPENAI_API_KEY"
        )
        transcription_provider = self._transcription_provider(policy)
        openai_transcription_model = (
            str(policy.get("openaiTranscriptionModel") or "whisper-1").strip() or "whisper-1"
        )
        openai_transcription_response_format = (
            str(policy.get("openaiTranscriptionResponseFormat") or "verbose_json").strip()
            or "verbose_json"
        )
        allow_beta_video = bool(policy.get("allowBetaVideo"))
        allow_beta_music = bool(policy.get("allowBetaMusic"))
        music_steps = self._positive_int(policy.get("musicSteps"), default=32)
        music_duration = self._positive_int(policy.get("musicDurationSeconds"), default=0)
        video_image = str(policy.get("videoImage") or "").strip()
        transcribe = bool(policy.get("transcribeCaptions")) or "captions" in selected
        provider_backed = False
        chutes_requested = profile.startswith("chutes_")
        blocking_warnings: list[str] = []
        if chutes_requested:
            if mode != "render_static":
                blocking_warnings.append("ritual_handoff_chutes_skipped_by_render_mode")
            if not bool(policy.get("externalProvidersAllowed")):
                blocking_warnings.append(
                    "ritual_handoff_chutes_skipped_external_providers_disabled"
                )
            if "chutes" not in provider_allowlist:
                blocking_warnings.append("ritual_handoff_chutes_skipped_provider_not_allowed")
            if max_cost <= 0:
                blocking_warnings.append("ritual_handoff_chutes_skipped_zero_budget")
            if not token_from_env_or_file(token_env, cwd=self._config.repo_root):
                blocking_warnings.append("ritual_handoff_chutes_skipped_missing_api_token")
            if not self._plan_allows_external_providers(plan):
                blocking_warnings.append("ritual_handoff_chutes_skipped_by_plan_policy")
            if "cinema" in requested:
                if "cinema" not in allowed or not self._plan_allows_cinema(plan):
                    warnings.append("ritual_handoff_chutes_skipped_by_plan_policy")
                    selected = [surface for surface in selected if surface != "cinema"]
                if not bool(policy.get("videoAllowed")):
                    warnings.append("ritual_handoff_cinema_skipped_without_video_allowed")
                    selected = [surface for surface in selected if surface != "cinema"]
                if not allow_beta_video:
                    warnings.append("ritual_handoff_cinema_skipped_without_beta_gate")
                    selected = [surface for surface in selected if surface != "cinema"]
                if profile not in _VIDEO_PROVIDER_PROFILES:
                    warnings.append("ritual_handoff_cinema_skipped_provider_profile")
                    selected = [surface for surface in selected if surface != "cinema"]
            if "music" in requested:
                if "music" not in allowed or not self._plan_allows_music(plan):
                    warnings.append("ritual_handoff_music_skipped_by_plan_policy")
                    selected = [surface for surface in selected if surface != "music"]
                if not allow_beta_music:
                    warnings.append("ritual_handoff_music_skipped_without_beta_gate")
                    selected = [surface for surface in selected if surface != "music"]
                if profile not in _MUSIC_PROVIDER_PROFILES:
                    warnings.append("ritual_handoff_music_skipped_provider_profile")
                    selected = [surface for surface in selected if surface != "music"]
            if transcription_provider == "openai" and transcribe:
                if "openai" not in provider_allowlist:
                    warnings.append(
                        "ritual_handoff_openai_transcription_skipped_provider_not_allowed"
                    )
                    transcription_provider = "fallback"
                elif not bool(policy.get("externalProvidersAllowed")):
                    warnings.append(
                        "ritual_handoff_openai_transcription_skipped_external_providers_disabled"
                    )
                    transcription_provider = "fallback"
                elif not token_from_env_or_file(openai_key_env, cwd=self._config.repo_root):
                    warnings.append("ritual_handoff_openai_transcription_skipped_missing_api_token")
                    transcription_provider = "fallback"
                elif not self._plan_allows_external_providers(plan):
                    warnings.append(
                        "ritual_handoff_openai_transcription_skipped_by_plan_policy"
                    )
                    transcription_provider = "fallback"
            if not selected:
                blocking_warnings.append("ritual_handoff_chutes_skipped_no_allowed_surfaces")
            warnings = list(dict.fromkeys([*blocking_warnings, *warnings]))
            provider_backed = not blocking_warnings and bool(selected)
        return HermesHandoffRenderOptions(
            provider_profile=profile if chutes_requested else "mock",
            surfaces=selected,
            max_cost_usd=max_cost,
            transcribe_captions=transcribe,
            transcription_provider=transcription_provider,
            openai_api_key_env=openai_key_env,
            openai_transcription_model=openai_transcription_model,
            openai_transcription_response_format=openai_transcription_response_format,
            request_timeout_seconds=timeout,
            chutes_token_env=token_env,
            allow_beta_video=allow_beta_video,
            allow_beta_music=allow_beta_music,
            music_steps=music_steps,
            music_duration_seconds=music_duration,
            video_image=video_image,
            provider_backed=provider_backed,
            warnings=warnings,
        )

    def _manifest_valid(self, manifest_path: Path, artifact_id: str, plan_id: str) -> bool:
        if not manifest_path.exists():
            return False
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return False
        surfaces = manifest.get("surfaces") if isinstance(manifest, dict) else None
        captions = surfaces.get("captions") if isinstance(surfaces, dict) else None
        caption_segments = captions.get("segments") if isinstance(captions, dict) else None
        captions_file = manifest_path.with_name("captions.vtt")
        return (
            manifest.get("schemaVersion") == MANIFEST_SCHEMA_VERSION
            and manifest.get("artifactId") == artifact_id
            and manifest.get("planId") == plan_id
            and (bool(caption_segments) or captions_file.exists())
        )

    def _manifest_satisfies_render_request(
        self,
        manifest_path: Path,
        options: HermesHandoffRenderOptions,
    ) -> bool:
        if not options.provider_backed:
            return True
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return False
        surfaces = manifest.get("surfaces") if isinstance(manifest, dict) else None
        if not isinstance(surfaces, dict):
            return False
        if "audio" in options.surfaces:
            audio = surfaces.get("audio")
            if not (
                isinstance(audio, dict) and audio.get("src") and audio.get("provider") == "chutes"
            ):
                return False
        if "image" in options.surfaces:
            image = surfaces.get("image")
            if not (
                isinstance(image, dict)
                and image.get("enabled") is True
                and image.get("src")
                and image.get("provider") == "chutes"
            ):
                return False
        if "captions" in options.surfaces:
            captions = surfaces.get("captions")
            segments = captions.get("segments") if isinstance(captions, dict) else None
            if not (bool(segments) or manifest_path.with_name("captions.vtt").exists()):
                return False
        if "cinema" in options.surfaces:
            cinema = surfaces.get("cinema")
            if not (
                isinstance(cinema, dict)
                and cinema.get("enabled") is True
                and cinema.get("src")
                and cinema.get("provider") == "chutes"
            ):
                return False
        if "music" in options.surfaces:
            music = surfaces.get("music")
            if not (
                isinstance(music, dict) and music.get("src") and music.get("provider") == "chutes"
            ):
                return False
        return True

    def _success(
        self,
        *,
        artifact_id: str,
        url: str,
        route: str,
        public_base: str,
        plan_path: Path,
        manifest_path: Path,
        opened: tuple[bool, list[str]],
        handoff_warnings: list[str] | None = None,
    ) -> dict[str, object]:
        did_open, open_warnings = opened
        manifest = self._read_manifest(manifest_path)
        render = cast(dict[str, object], manifest.get("render") or {})
        surfaces = cast(dict[str, object], manifest.get("surfaces") or {})
        raw_warnings = render.get("warnings")
        render_warnings = (
            [str(item) for item in raw_warnings] if isinstance(raw_warnings, list) else []
        )
        warnings = list(
            dict.fromkeys([*(handoff_warnings or []), *render_warnings, *open_warnings])
        )
        return {
            "status": "ok",
            "warnings": warnings,
            "artifactUrl": url,
            "artifact": {
                "artifactId": artifact_id,
                "url": url,
                "route": route,
                "publicBasePath": public_base,
                "planPath": self._display_path(plan_path),
                "manifestPath": self._display_path(manifest_path),
                "rendererVersion": str(render.get("rendererVersion") or RENDERER_VERSION),
                "mode": str(render.get("mode") or "dry_run_manifest"),
                "providers": self._manifest_providers(render.get("providers")),
                "surfaces": self._surface_summary(surfaces),
                "renderWarnings": render_warnings,
                "opened": did_open,
            },
        }

    def _failure(self, *, retryable: bool, detail: str | None = None) -> dict[str, object]:
        artifact = {"status": "render_failed", "mode": "dry_run_manifest", "providers": ["mock"]}
        if detail:
            artifact["detail"] = detail
        return {
            "status": "render_failed",
            "retryable": retryable,
            "warnings": ["ritual_handoff_render_failed"],
            "artifact": artifact,
        }

    def _open_if_requested(self, url: str, open_local: bool) -> tuple[bool, list[str]]:
        if not open_local:
            return False, []
        if not (url.startswith("http://localhost") or url.startswith("http://127.0.0.1")):
            return False, ["ritual_handoff_open_skipped_non_local_url"]
        try:
            return bool(webbrowser.open(url, new=2)), []
        except Exception:
            return False, ["ritual_handoff_open_failed"]

    def _display_path(self, path: Path) -> str:
        return os.path.relpath(path, self._config.repo_root)

    def _read_manifest(self, path: Path) -> dict[str, object]:
        try:
            manifest = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return {}
        return manifest if isinstance(manifest, dict) else {}

    def _manifest_providers(self, value: object) -> list[str]:
        if not isinstance(value, list):
            return ["mock"]
        providers = [str(item) for item in value if str(item)]
        return providers or ["mock"]

    def _surface_summary(self, surfaces: dict[str, object]) -> dict[str, object]:
        audio = surfaces.get("audio")
        captions = surfaces.get("captions")
        image = surfaces.get("image")
        cinema = surfaces.get("cinema")
        music = surfaces.get("music")
        caption_segments = captions.get("segments") if isinstance(captions, dict) else None
        caption_tracks = captions.get("tracks") if isinstance(captions, dict) else None
        summary: dict[str, object] = {
            "audio": bool(isinstance(audio, dict) and audio.get("src")),
            "captions": bool(caption_segments or caption_tracks),
            "image": bool(isinstance(image, dict) and image.get("enabled") and image.get("src")),
        }
        if "cinema" in surfaces:
            summary["cinema"] = bool(
                isinstance(cinema, dict) and cinema.get("enabled") and cinema.get("src")
            )
        if "music" in surfaces:
            summary["music"] = {
                "available": bool(isinstance(music, dict) and music.get("src")),
                "provider": music.get("provider") if isinstance(music, dict) else None,
                "mimeType": music.get("mimeType") if isinstance(music, dict) else None,
            }
        return summary

    def _transcription_provider(self, policy: dict[str, object]) -> str:
        value = str(policy.get("transcriptionProvider") or "").strip().lower()
        if value in {"openai", "chutes", "fallback"}:
            return value
        return "chutes"

    def _requested_provider_surfaces(self, value: object) -> list[str]:
        if not isinstance(value, list):
            return []
        surfaces: list[str] = []
        for item in value:
            surface = str(item).strip().lower()
            if surface in {"speech", "voice"}:
                surface = "audio"
            elif surface in {"cc", "transcript"}:
                surface = "captions"
            elif surface in {"video", "movie"}:
                surface = "cinema"
            if surface in _PROVIDER_SURFACES and surface not in surfaces:
                surfaces.append(surface)
        return surfaces

    def _result_allowed_surfaces(self, result: dict[str, object]) -> list[str]:
        render_request = result.get("renderRequest")
        if not isinstance(render_request, dict):
            return []
        allowed = render_request.get("allowedSurfaces")
        if not isinstance(allowed, list):
            return []
        return [str(item).strip().lower() for item in allowed]

    def _provider_allowlist(self, value: object) -> set[str]:
        if not isinstance(value, list):
            return set()
        return {str(item).strip().lower() for item in value if str(item).strip()}

    def _max_cost_usd(self, policy: dict[str, object]) -> float:
        raw = policy.get("maxCostUsd")
        if raw is None:
            max_cost = policy.get("maxCost")
            raw = max_cost.get("amount") if isinstance(max_cost, dict) else None
        try:
            return float(cast(str | float | int, raw or 0))
        except (TypeError, ValueError):
            return 0

    def _positive_int(self, value: object, *, default: int) -> int:
        try:
            parsed = int(cast(str | float | int, value or default))
        except (TypeError, ValueError):
            return default
        return max(parsed, 1)

    def _plan_allows_external_providers(self, plan: dict[str, object]) -> bool:
        safety = cast(dict[str, object], plan.get("safetyBoundary") or {})
        raw_restrictions = safety.get("providerRestrictions")
        restrictions = (
            {str(item) for item in raw_restrictions}
            if isinstance(raw_restrictions, list)
            else set()
        )
        if "external_providers_disabled" in restrictions:
            return False
        return "no_raw_material_to_external_provider" in restrictions

    def _plan_allows_cinema(self, plan: dict[str, object]) -> bool:
        visual = cast(dict[str, object], plan.get("visualPromptPlan") or {})
        cinema = cast(dict[str, object], visual.get("cinema") or {})
        return bool(cinema.get("enabled")) and self._plan_allows_external_providers(plan)

    def _plan_allows_music(self, plan: dict[str, object]) -> bool:
        music = cast(dict[str, object], plan.get("music") or {})
        return bool(music.get("enabled")) and self._plan_allows_external_providers(plan)
