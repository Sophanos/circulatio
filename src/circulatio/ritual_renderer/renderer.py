from __future__ import annotations

import base64
import hashlib
import json
import os
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal, cast

from .contracts import (
    CaptionSegment,
    RitualArtifactManifest,
    RitualManifestSection,
    RitualRenderOptions,
)
from .providers.chutes import (
    ChutesAsset,
    ChutesProviderError,
    caption_segments_from_transcription,
    generate_image,
    generate_music,
    generate_video,
    synthesize_speech,
    transcribe_audio,
)

RENDERER_VERSION = "ritual-renderer.v1"
MANIFEST_SCHEMA_VERSION: Literal["hermes_ritual_artifact.v1"] = "hermes_ritual_artifact.v1"
RitualSectionKind = Literal["arrival", "breath", "image", "reflection", "closing"]
RitualSectionLens = Literal["cinema", "photo", "breath", "meditation", "body"]


def artifact_id_for_plan(plan: dict[str, object]) -> str:
    stable_hash = str(plan.get("stableHash") or "").strip()
    if not stable_hash:
        encoded = json.dumps(plan, sort_keys=True, ensure_ascii=False, default=str).encode()
        stable_hash = hashlib.sha256(encoded).hexdigest()
    return f"ritual_artifact_{stable_hash[:16]}"


def render_plan_file(
    *,
    plan_path: str | Path,
    out_dir: str | Path,
    options: RitualRenderOptions | None = None,
) -> RitualArtifactManifest:
    raw = json.loads(Path(plan_path).read_text(encoding="utf-8"))
    plan = raw.get("plan") if isinstance(raw, dict) and isinstance(raw.get("plan"), dict) else raw
    if not isinstance(plan, dict):
        raise ValueError("Plan file must contain a plan object or a plan result with a plan field.")
    return RitualRenderer(options or {}).render(plan=cast(dict[str, object], plan), out_dir=out_dir)


class RitualRenderer:
    def __init__(self, options: RitualRenderOptions | None = None) -> None:
        self._options = options or {}

    def render(
        self,
        *,
        plan: dict[str, object],
        out_dir: str | Path,
    ) -> RitualArtifactManifest:
        self._validate_plan(plan)
        output = Path(out_dir)
        output.mkdir(parents=True, exist_ok=True)
        artifact_id = self._artifact_id(plan)
        public_base = self._public_base(artifact_id)
        duration = cast(dict[str, object], plan.get("duration") or {})
        duration_ms = self._int_value(duration.get("targetSeconds"), default=300) * 1000
        captions = self._caption_segments(plan, duration_ms=duration_ms)
        provider_assets, provider_captions, provider_warnings = self._render_provider_assets(
            plan=plan,
            output=output,
            public_base=public_base,
            duration_ms=duration_ms,
        )
        if provider_captions:
            captions = provider_captions
        captions_path = output / "captions.vtt"
        captions_path.write_text(self._webvtt(captions), encoding="utf-8")
        manifest = self._manifest(
            plan=plan,
            artifact_id=artifact_id,
            public_base=public_base,
            duration_ms=duration_ms,
            captions=captions,
            provider_assets=provider_assets,
            render_warnings=provider_warnings,
        )
        (output / "manifest.json").write_text(
            json.dumps(manifest, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        return manifest

    def _validate_plan(self, plan: dict[str, object]) -> None:
        if plan.get("schemaVersion") != "circulatio.presentation.plan.v1":
            raise ValueError("Unsupported plan schemaVersion.")
        if not plan.get("id"):
            raise ValueError("Plan id is required.")
        if not isinstance(plan.get("voiceScript"), dict):
            raise ValueError("Plan voiceScript is required.")

    def _artifact_id(self, plan: dict[str, object]) -> str:
        return artifact_id_for_plan(plan)

    def _public_base(self, artifact_id: str) -> str:
        return str(self._options.get("publicBasePath") or f"/artifacts/{artifact_id}").rstrip("/")

    def _manifest(
        self,
        *,
        plan: dict[str, object],
        artifact_id: str,
        public_base: str,
        duration_ms: int,
        captions: list[CaptionSegment],
        provider_assets: dict[str, dict[str, object]],
        render_warnings: list[str],
    ) -> RitualArtifactManifest:
        breath = cast(dict[str, object], plan.get("breath") or {})
        meditation = cast(dict[str, object], plan.get("meditation") or {})
        audio_surface = self._audio_surface(
            plan=plan,
            public_base=public_base,
            duration_ms=duration_ms,
            provider_assets=provider_assets,
        )
        surfaces: dict[str, object] = {
            "text": {"body": cast(dict[str, object], plan.get("text") or {}).get("body", "")},
            "audio": audio_surface,
            "captions": {
                "tracks": [
                    {
                        "src": f"{public_base}/captions.vtt",
                        "format": "webvtt",
                        "lang": str(plan.get("locale") or "en-US"),
                        "kind": "subtitles",
                        "label": "English",
                    }
                ],
                "segments": captions,
            },
            "breath": {
                "enabled": bool(breath.get("enabled", False)),
                "pattern": str(breath.get("pattern") or "lengthened_exhale"),
                "inhaleSeconds": self._int_value(breath.get("inhaleSeconds"), default=4),
                "holdSeconds": self._int_value(breath.get("holdSeconds"), default=0),
                "exhaleSeconds": self._int_value(breath.get("exhaleSeconds"), default=6),
                "restSeconds": self._int_value(breath.get("restSeconds"), default=2),
                "cycles": self._int_value(breath.get("cycles"), default=5),
                "visualForm": str(breath.get("visualForm") or "pacer"),
                "phaseLabels": True,
            },
            "meditation": {
                "enabled": bool(meditation.get("enabled", False)),
                "fieldType": str(meditation.get("fieldType") or "coherence_convergence"),
                "durationMs": self._int_value(
                    meditation.get("durationMs"), default=min(duration_ms, 180000)
                ),
                "macroProgressPolicy": str(
                    meditation.get("macroProgressPolicy") or "session_progress"
                ),
                "microMotion": str(meditation.get("microMotion") or "convergence"),
                "instructionDensity": str(meditation.get("instructionDensity") or "sparse"),
            },
            "image": self._image_surface(provider_assets),
            "cinema": self._cinema_surface(provider_assets),
        }
        if "music" in provider_assets:
            surfaces["music"] = provider_assets["music"]
        providers = ["mock"]
        if any(asset.get("provider") == "chutes" for asset in provider_assets.values()):
            providers.append("chutes")
        sections = self._sections(
            plan=plan,
            surfaces=surfaces,
            captions=captions,
            duration_ms=duration_ms,
        )
        return {
            "schemaVersion": MANIFEST_SCHEMA_VERSION,
            "artifactId": artifact_id,
            "planId": str(plan["id"]),
            "createdAt": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
            "title": str(plan.get("title") or "Ritual artifact"),
            "description": str(
                cast(dict[str, object], plan.get("text") or {}).get("summary") or ""
            ),
            "privacyClass": str(plan.get("privacyClass") or "private"),
            "locale": str(plan.get("locale") or "en-US"),
            "sourceRefs": cast(list[dict[str, object]], plan.get("sourceRefs") or []),
            "durationMs": duration_ms,
            "sections": sections,
            "surfaces": surfaces,
            "timeline": self._timeline(plan=plan, captions=captions),
            "interaction": {
                "finishPrompt": cast(dict[str, object], plan.get("interactionSpec") or {}).get(
                    "finishPrompt", "What did you notice?"
                ),
                "captureBodyResponse": True,
                "completionEndpoint": f"/api/artifacts/{artifact_id}/complete",
                "returnCommand": f"/circulation ritual complete {artifact_id}",
                "completion": {
                    "enabled": True,
                    "endpoint": f"/api/artifacts/{artifact_id}/complete",
                    "idempotencyRequired": True,
                    "captureReflection": True,
                    "capturePracticeFeedback": True,
                    "completionIdStrategy": "client_uuid",
                },
            },
            "safety": {
                "stopInstruction": cast(dict[str, object], plan.get("safetyBoundary") or {}).get(
                    "groundingInstruction",
                    "Stop if this increases activation; orient to the room.",
                ),
                "contraindications": cast(dict[str, object], plan.get("voiceScript") or {}).get(
                    "contraindications", []
                ),
                "blockedSurfaces": cast(dict[str, object], plan.get("safetyBoundary") or {}).get(
                    "blockedSurfaces", []
                ),
            },
            "render": {
                "rendererVersion": RENDERER_VERSION,
                "mode": str(
                    cast(dict[str, object], plan.get("deliveryPolicy") or {}).get("renderMode")
                    or "dry_run_manifest"
                ),
                "providers": providers,
                "cacheKeys": [str(plan.get("stableHash"))] if plan.get("stableHash") else [],
                "budget": {"currency": "USD", "estimated": 0, "actual": 0},
                "warnings": render_warnings,
            },
        }

    def _audio_surface(
        self,
        *,
        plan: dict[str, object],
        public_base: str,
        duration_ms: int,
        provider_assets: dict[str, dict[str, object]],
    ) -> dict[str, object]:
        if "audio" in provider_assets:
            return provider_assets["audio"]
        del duration_ms
        render_mode = str(
            cast(dict[str, object], plan.get("deliveryPolicy") or {}).get("renderMode") or ""
        )
        voice_segments = cast(dict[str, object], plan.get("voiceScript") or {}).get("segments", [])
        audio_requested = any(
            isinstance(segment, dict) and str(segment.get("role")) != "silence"
            for segment in cast(list[object], voice_segments)
        )
        if not audio_requested or render_mode == "plan_only":
            return {
                "src": None,
                "mimeType": None,
                "durationMs": None,
                "provider": None,
                "voiceId": None,
                "checksum": None,
            }
        return {
            "src": None,
            "mimeType": None,
            "durationMs": None,
            "provider": "mock",
            "voiceId": "mock_steady",
            "checksum": None,
            "placeholderSrc": f"{public_base}/audio.wav",
        }

    def _image_surface(self, provider_assets: dict[str, dict[str, object]]) -> dict[str, object]:
        if "image" in provider_assets:
            return {"enabled": True, **provider_assets["image"]}
        return {
            "enabled": False,
            "src": None,
            "alt": "No generated image for this artifact.",
            "provider": None,
        }

    def _cinema_surface(self, provider_assets: dict[str, dict[str, object]]) -> dict[str, object]:
        if "cinema" in provider_assets:
            return {"enabled": True, **provider_assets["cinema"]}
        return {
            "enabled": False,
            "src": None,
            "posterSrc": None,
            "mimeType": None,
            "durationMs": None,
            "provider": None,
        }

    def _render_provider_assets(
        self,
        *,
        plan: dict[str, object],
        output: Path,
        public_base: str,
        duration_ms: int,
    ) -> tuple[dict[str, dict[str, object]], list[CaptionSegment], list[str]]:
        del duration_ms
        profile = str(self._options.get("providerProfile") or "mock").strip()
        selected = self._selected_surfaces(profile)
        if not profile.startswith("chutes") or not selected:
            return {}, [], []
        warnings: list[str] = []
        if self._options.get("dryRun"):
            return {}, [], ["chutes_provider_skipped_in_dry_run"]
        if self._options.get("mockProviders"):
            return {}, [], ["chutes_provider_skipped_by_mock_providers"]
        if not self._plan_allows_external_providers(plan):
            return {}, [], ["chutes_provider_blocked_by_plan_policy"]
        max_cost = float(self._options.get("maxCostUsd", 0) or 0)
        if max_cost <= 0:
            return {}, [], ["chutes_provider_blocked_by_zero_budget"]
        token = os.environ.get(str(self._options.get("chutesTokenEnv") or "CHUTES_API_TOKEN"), "")
        if not token:
            return {}, [], ["chutes_provider_missing_api_token"]
        timeout = int(self._options.get("requestTimeoutSeconds", 180) or 180)
        assets: dict[str, dict[str, object]] = {}
        captions: list[CaptionSegment] = []
        if "audio" in selected:
            self._try_render_chutes_audio(
                plan=plan,
                output=output,
                public_base=public_base,
                token=token,
                timeout=timeout,
                assets=assets,
                captions=captions,
                warnings=warnings,
            )
        if "image" in selected:
            self._try_render_chutes_image(
                plan=plan,
                output=output,
                public_base=public_base,
                token=token,
                timeout=timeout,
                assets=assets,
                warnings=warnings,
            )
        if "music" in selected and not self._options.get("allowBetaMusic"):
            warnings.append("chutes_music_skipped_without_beta_gate")
            selected.discard("music")
        if "cinema" in selected and not self._options.get("allowBetaVideo"):
            warnings.append("chutes_video_skipped_without_beta_gate")
            selected.discard("cinema")
        if "cinema" in selected and not self._plan_allows_video(plan):
            warnings.append("chutes_video_blocked_by_plan_video_policy")
            selected.discard("cinema")
        if "music" in selected:
            self._try_render_chutes_music(
                output=output,
                public_base=public_base,
                token=token,
                timeout=max(timeout, 240),
                assets=assets,
                warnings=warnings,
            )
        if "cinema" in selected:
            self._try_render_chutes_video(
                plan=plan,
                output=output,
                public_base=public_base,
                token=token,
                timeout=max(timeout, 360),
                assets=assets,
                warnings=warnings,
            )
        return assets, captions, warnings

    def _try_render_chutes_audio(
        self,
        *,
        plan: dict[str, object],
        output: Path,
        public_base: str,
        token: str,
        timeout: int,
        assets: dict[str, dict[str, object]],
        captions: list[CaptionSegment],
        warnings: list[str],
    ) -> None:
        text = self._voice_text(plan)
        if not text:
            warnings.append("chutes_audio_skipped_empty_voice_script")
            return
        try:
            asset = synthesize_speech(
                token=token,
                text=text,
                out_path=output / "audio.wav",
                timeout_seconds=timeout,
            )
        except ChutesProviderError as exc:
            warnings.append(self._provider_warning("chutes_audio_failed", exc))
            return

        assets["audio"] = {
            **self._asset_ref(asset, public_base=public_base),
            "voiceId": "chutes-kokoro",
        }
        if not (
            self._options.get("transcribeCaptions")
            or "captions"
            in self._selected_surfaces(str(self._options.get("providerProfile") or ""))
        ):
            return

        try:
            transcription = transcribe_audio(
                token=token,
                audio_path=asset["path"],
                timeout_seconds=timeout,
            )
        except ChutesProviderError as exc:
            warnings.append(self._provider_warning("chutes_transcription_failed", exc))
            return

        captions.extend(
            cast(
                list[CaptionSegment],
                caption_segments_from_transcription(transcription),
            )
        )
        if not captions:
            warnings.append("chutes_transcription_returned_no_timed_segments")

    def _try_render_chutes_image(
        self,
        *,
        plan: dict[str, object],
        output: Path,
        public_base: str,
        token: str,
        timeout: int,
        assets: dict[str, dict[str, object]],
        warnings: list[str],
    ) -> None:
        prompt = self._image_prompt(plan)
        if not prompt:
            warnings.append("chutes_image_skipped_no_enabled_prompt")
            return
        try:
            asset = generate_image(
                token=token,
                prompt=prompt,
                out_path=output / "image.png",
                timeout_seconds=timeout,
            )
            assets["image"] = {
                **self._asset_ref(asset, public_base=public_base),
                "alt": "Generated non-literal ritual image.",
            }
        except ChutesProviderError as exc:
            warnings.append(self._provider_warning("chutes_image_failed", exc))

    def _try_render_chutes_music(
        self,
        *,
        output: Path,
        public_base: str,
        token: str,
        timeout: int,
        assets: dict[str, dict[str, object]],
        warnings: list[str],
    ) -> None:
        steps = int(self._options.get("musicSteps", 32) or 32)
        try:
            asset = generate_music(
                token=token,
                out_path=output / "music.wav",
                steps=steps,
                timeout_seconds=timeout,
            )
            assets["music"] = self._asset_ref(asset, public_base=public_base)
        except ChutesProviderError as exc:
            warnings.append(self._provider_warning("chutes_music_failed", exc))

    def _try_render_chutes_video(
        self,
        *,
        plan: dict[str, object],
        output: Path,
        public_base: str,
        token: str,
        timeout: int,
        assets: dict[str, dict[str, object]],
        warnings: list[str],
    ) -> None:
        visual = cast(dict[str, object], plan.get("visualPromptPlan") or {})
        cinema = cast(dict[str, object], visual.get("cinema") or {})
        if cinema.get("providerPromptPolicy") != "sanitized_visual_only":
            warnings.append("chutes_video_skipped_without_sanitized_prompt")
            return
        prompt = self._video_prompt(plan)
        if not prompt:
            warnings.append("chutes_video_skipped_no_sanitized_storyboard")
            return
        image = self._video_image_payload(output=output, assets=assets)
        if not image:
            warnings.append("chutes_video_skipped_no_image_input")
            return
        try:
            asset = generate_video(
                token=token,
                prompt=prompt,
                image=image,
                out_path=output / "cinema.mp4",
                timeout_seconds=timeout,
            )
            assets["cinema"] = {
                **self._asset_ref(asset, public_base=public_base),
                "posterSrc": self._cinema_poster_src(assets),
                "title": str(plan.get("title") or "Ritual artifact"),
                "playbackMode": "transport_synced",
                "presentation": "full_background",
            }
        except ChutesProviderError as exc:
            warnings.append(self._provider_warning("chutes_video_failed", exc))

    def _selected_surfaces(self, profile: str) -> set[str]:
        raw = {item.lower() for item in self._options.get("surfaces", [])}
        selected = {"cinema" if item in {"video", "movie"} else item for item in raw}
        selected = {"audio" if item in {"speech", "voice"} else item for item in selected}
        selected = {"captions" if item in {"cc", "transcript"} else item for item in selected}
        if selected:
            return selected
        defaults = {
            "chutes_speech": {"audio"},
            "chutes_audio": {"audio"},
            "chutes_image": {"image"},
            "chutes_music": {"music"},
            "chutes_video": {"cinema"},
            "chutes_all": {"audio", "captions", "image"},
        }
        return defaults.get(profile, set())

    def _plan_allows_external_providers(self, plan: dict[str, object]) -> bool:
        safety = cast(dict[str, object], plan.get("safetyBoundary") or {})
        restrictions = {
            str(item) for item in cast(list[object], safety.get("providerRestrictions") or [])
        }
        if "external_providers_disabled" in restrictions:
            return False
        if "no_raw_material_to_external_provider" not in restrictions:
            return False
        return True

    def _plan_allows_video(self, plan: dict[str, object]) -> bool:
        visual = cast(dict[str, object], plan.get("visualPromptPlan") or {})
        cinema = cast(dict[str, object], visual.get("cinema") or {})
        return bool(cinema.get("enabled"))

    def _asset_ref(self, asset: ChutesAsset, *, public_base: str) -> dict[str, object]:
        return {
            "src": f"{public_base}/{asset['path'].name}",
            "mimeType": asset["mimeType"],
            "durationMs": None,
            "provider": asset["provider"],
            "model": asset["model"],
            "checksum": self._file_sha256(asset["path"]),
        }

    def _voice_text(self, plan: dict[str, object]) -> str:
        voice_script = cast(dict[str, object], plan.get("voiceScript") or {})
        segments = voice_script.get("segments", [])
        lines = []
        for segment in cast(list[object], segments):
            if not isinstance(segment, dict):
                continue
            if str(segment.get("role") or "") == "silence":
                continue
            text = " ".join(str(segment.get("text") or "").split())
            if text:
                lines.append(text)
        return "\n\n".join(lines)

    def _image_prompt(self, plan: dict[str, object]) -> str:
        visual = cast(dict[str, object], plan.get("visualPromptPlan") or {})
        image = cast(dict[str, object], visual.get("image") or {})
        if not image.get("enabled"):
            return ""
        if image.get("providerPromptPolicy") != "sanitized_visual_only":
            return ""
        return " ".join(str(image.get("prompt") or "").split())

    def _video_prompt(self, plan: dict[str, object]) -> str:
        visual = cast(dict[str, object], plan.get("visualPromptPlan") or {})
        cinema = cast(dict[str, object], visual.get("cinema") or {})
        if not cinema.get("enabled"):
            return ""
        if cinema.get("providerPromptPolicy") != "sanitized_visual_only":
            return ""
        storyboard = cinema.get("storyboard")
        if isinstance(storyboard, list) and storyboard:
            first = storyboard[0]
            if isinstance(first, dict):
                prompt = " ".join(str(first.get("prompt") or first.get("text") or "").split())
                if prompt:
                    return prompt
        return ""

    def _video_image_payload(
        self,
        *,
        output: Path,
        assets: dict[str, dict[str, object]],
    ) -> str:
        configured = str(self._options.get("videoImage") or "").strip()
        if configured:
            path = Path(configured)
            if path.exists():
                return base64.b64encode(path.read_bytes()).decode("ascii")
            return configured
        image_asset = assets.get("image")
        if image_asset:
            src = str(image_asset.get("src") or "")
            image_path = output / Path(src).name
            if image_path.exists():
                return base64.b64encode(image_path.read_bytes()).decode("ascii")
        return ""

    def _cinema_poster_src(self, assets: dict[str, dict[str, object]]) -> str | None:
        image = assets.get("image")
        if not image:
            return None
        src = image.get("src")
        return str(src) if src else None

    def _provider_warning(self, code: str, exc: ChutesProviderError) -> str:
        detail = str(exc)
        if "HTTP " in detail:
            marker = detail.split("HTTP ", 1)[1][:3]
            if marker.isdigit():
                return f"{code}:http_{marker}"
        if "asset payload" in detail or "downloadable URL" in detail:
            return f"{code}:asset_payload_missing"
        if "not a JSON object" in detail or "not JSON" in detail:
            return f"{code}:response_invalid"
        if "request failed" in detail.lower():
            return f"{code}:request_failed"
        return f"{code}:provider_error"

    def _file_sha256(self, path: Path) -> str:
        return hashlib.sha256(path.read_bytes()).hexdigest()

    def _sections(
        self,
        *,
        plan: dict[str, object],
        surfaces: dict[str, object],
        captions: list[CaptionSegment],
        duration_ms: int,
    ) -> list[RitualManifestSection]:
        explicit = self._explicit_sections(plan=plan, captions=captions, duration_ms=duration_ms)
        if explicit:
            return explicit

        breath = cast(dict[str, object], surfaces.get("breath") or {})
        meditation = cast(dict[str, object], surfaces.get("meditation") or {})
        image = cast(dict[str, object], surfaces.get("image") or {})
        cinema = cast(dict[str, object], surfaces.get("cinema") or {})

        sections: list[RitualManifestSection] = []
        cursor = 0
        arrival_ms = min(12_000, max(6_000, round(duration_ms * 0.04)))
        closing_ms = min(48_000, max(18_000, round(duration_ms * 0.16)))
        closing_start = max(arrival_ms, duration_ms - closing_ms)

        def add(section: RitualManifestSection) -> None:
            nonlocal cursor
            if section["endMs"] <= section["startMs"]:
                return
            sections.append(self._section_with_captions(section, captions))
            cursor = section["endMs"]

        add(
            {
                "id": "section-arrival",
                "title": "Arrival",
                "startMs": 0,
                "endMs": min(arrival_ms, duration_ms),
                "kind": "arrival",
                "preferredLens": self._primary_lens(image=image, cinema=cinema),
                "channels": {"voice": True, "ambient": True},
            }
        )

        breath_ms = self._breath_duration_ms(breath)
        if breath_ms > 0 and cursor < closing_start:
            add(
                {
                    "id": "section-breath",
                    "title": "Breath",
                    "startMs": cursor,
                    "endMs": min(cursor + breath_ms, closing_start),
                    "kind": "breath",
                    "preferredLens": "breath",
                    "skippable": True,
                    "channels": {"voice": True, "breath": True, "pulse": True},
                }
            )

        if self._has_visual_surface(image=image, cinema=cinema) and cursor < closing_start:
            image_ms = min(30_000, max(12_000, round(duration_ms * 0.1)))
            add(
                {
                    "id": "section-image",
                    "title": "Image return",
                    "startMs": cursor,
                    "endMs": min(cursor + image_ms, closing_start),
                    "kind": "image",
                    "preferredLens": self._primary_lens(image=image, cinema=cinema),
                    "skippable": True,
                    "channels": {"voice": True, "ambient": True},
                }
            )

        if cursor < closing_start:
            add(
                {
                    "id": "section-reflection",
                    "title": "Reflection",
                    "startMs": cursor,
                    "endMs": closing_start,
                    "kind": "reflection",
                    "preferredLens": (
                        "meditation"
                        if bool(meditation.get("enabled"))
                        else self._primary_lens(
                            image=image,
                            cinema=cinema,
                        )
                    ),
                    "skippable": True,
                    "channels": {"voice": True, "ambient": True},
                }
            )

        if closing_start < duration_ms:
            finish_prompt = str(
                cast(dict[str, object], plan.get("interactionSpec") or {}).get(
                    "finishPrompt", "What did you notice?"
                )
            )
            add(
                {
                    "id": "section-closing",
                    "title": "Closing",
                    "startMs": closing_start,
                    "endMs": duration_ms,
                    "kind": "closing",
                    "preferredLens": "body",
                    "capturePrompt": finish_prompt,
                    "channels": {"voice": True, "breath": True},
                }
            )

        return sections

    def _explicit_sections(
        self,
        *,
        plan: dict[str, object],
        captions: list[CaptionSegment],
        duration_ms: int,
    ) -> list[RitualManifestSection]:
        raw_sections = plan.get("sections")
        if not isinstance(raw_sections, list):
            return []

        sections: list[RitualManifestSection] = []
        valid_kinds = {"arrival", "breath", "image", "reflection", "closing"}
        valid_lenses = {"cinema", "photo", "breath", "meditation", "body"}
        for index, raw in enumerate(raw_sections, start=1):
            if not isinstance(raw, dict):
                continue
            start_ms = self._bounded_ms(raw.get("startMs"), duration_ms)
            end_ms = self._bounded_ms(raw.get("endMs"), duration_ms)
            if end_ms <= start_ms:
                continue
            raw_kind = str(raw.get("kind") or "reflection")
            kind: RitualSectionKind = (
                cast(RitualSectionKind, raw_kind) if raw_kind in valid_kinds else "reflection"
            )
            section: RitualManifestSection = {
                "id": str(raw.get("id") or f"section-{index}"),
                "title": str(raw.get("title") or kind.replace("_", " ").title()),
                "startMs": start_ms,
                "endMs": end_ms,
                "kind": kind,
            }
            raw_preferred_lens = str(raw.get("preferredLens") or "").strip()
            if raw_preferred_lens in valid_lenses:
                section["preferredLens"] = cast(RitualSectionLens, raw_preferred_lens)
            capture_prompt = str(raw.get("capturePrompt") or "").strip()
            if capture_prompt:
                section["capturePrompt"] = capture_prompt
            if isinstance(raw.get("channels"), dict):
                section["channels"] = {
                    str(key): bool(value)
                    for key, value in cast(dict[str, object], raw["channels"]).items()
                }
            if "skippable" in raw:
                section["skippable"] = bool(raw.get("skippable"))
            sections.append(self._section_with_captions(section, captions))
        return sorted(sections, key=lambda item: item["startMs"])

    def _bounded_ms(self, value: object, duration_ms: int) -> int:
        return max(0, min(self._int_value(value, default=0), duration_ms))

    def _section_with_captions(
        self,
        section: RitualManifestSection,
        captions: list[CaptionSegment],
    ) -> RitualManifestSection:
        overlapping = [
            caption
            for caption in captions
            if caption["endMs"] > section["startMs"] and caption["startMs"] < section["endMs"]
        ]
        if not overlapping:
            return section
        enriched = cast(RitualManifestSection, dict(section))
        enriched["captionCount"] = len(overlapping)
        enriched["transcript"] = " ".join(caption["text"] for caption in overlapping)
        return enriched

    def _breath_duration_ms(self, breath: dict[str, object]) -> int:
        if not breath.get("enabled"):
            return 0
        cycle_seconds = sum(
            self._int_value(breath.get(key), default=0)
            for key in ("inhaleSeconds", "holdSeconds", "exhaleSeconds", "restSeconds")
        )
        cycles = max(self._int_value(breath.get("cycles"), default=1), 1)
        return max(cycle_seconds, 1) * cycles * 1000

    def _has_visual_surface(
        self,
        *,
        image: dict[str, object],
        cinema: dict[str, object],
    ) -> bool:
        return bool(
            (image.get("enabled") and image.get("src"))
            or (cinema.get("enabled") and cinema.get("src"))
        )

    def _primary_lens(
        self,
        *,
        image: dict[str, object],
        cinema: dict[str, object],
    ) -> RitualSectionLens:
        if cinema.get("enabled") and cinema.get("src"):
            return "cinema"
        if image.get("enabled") and image.get("src"):
            return "photo"
        return "breath"

    def _caption_segments(
        self, plan: dict[str, object], *, duration_ms: int
    ) -> list[CaptionSegment]:
        voice_script = cast(dict[str, object], plan.get("voiceScript") or {})
        raw_voice_segments = voice_script.get("segments") or []
        raw_segments = [
            item for item in cast(list[object], raw_voice_segments) if isinstance(item, dict)
        ]
        captions: list[CaptionSegment] = []
        cursor = 0
        for index, segment in enumerate(raw_segments, start=1):
            text = " ".join(str(segment.get("text") or "").split())
            if not text:
                continue
            word_count = max(len(text.split()), 1)
            segment_ms = min(max(word_count * 520, 3200), 14000)
            pause_ms = self._int_value(segment.get("pauseAfterMs"), default=0)
            end = min(cursor + segment_ms, duration_ms)
            captions.append({"id": f"cap_{index}", "startMs": cursor, "endMs": end, "text": text})
            cursor = min(end + pause_ms, duration_ms)
            if cursor >= duration_ms:
                break
        if captions and captions[-1]["endMs"] < duration_ms:
            captions[-1]["endMs"] = min(duration_ms, captions[-1]["endMs"] + 2000)
        return captions

    def _timeline(
        self,
        *,
        plan: dict[str, object],
        captions: list[CaptionSegment],
    ) -> list[dict[str, object]]:
        timeline: list[dict[str, object]] = []
        for caption in captions:
            timeline.append({"atMs": caption["startMs"], "kind": "voice", "ref": caption["id"]})
        breath = cast(dict[str, object], plan.get("breath") or {})
        if breath.get("enabled"):
            timeline.append({"atMs": 0, "kind": "breath_phase", "phase": "inhale"})
        meditation = cast(dict[str, object], plan.get("meditation") or {})
        if meditation.get("enabled"):
            timeline.append({"atMs": 90000, "kind": "meditation_phase", "phase": "settle"})
        return sorted(timeline, key=lambda item: self._int_value(item.get("atMs"), default=0))

    def _int_value(self, value: object, *, default: int) -> int:
        if value is None:
            return default
        try:
            return int(cast(str | float | int, value))
        except (TypeError, ValueError):
            return default

    def _webvtt(self, captions: list[CaptionSegment]) -> str:
        blocks = ["WEBVTT", ""]
        for caption in captions:
            blocks.append(caption["id"])
            blocks.append(
                f"{self._vtt_time(caption['startMs'])} --> {self._vtt_time(caption['endMs'])}"
            )
            blocks.append(caption["text"])
            blocks.append("")
        return "\n".join(blocks)

    def _vtt_time(self, ms: int) -> str:
        total = max(ms, 0)
        hours, remainder = divmod(total, 3_600_000)
        minutes, remainder = divmod(remainder, 60_000)
        seconds, millis = divmod(remainder, 1000)
        return f"{hours:02}:{minutes:02}:{seconds:02}.{millis:03}"


__all__ = ["artifact_id_for_plan", "render_plan_file", "RitualRenderer"]
