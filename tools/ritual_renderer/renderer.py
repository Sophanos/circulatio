from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import cast

from .contracts import CaptionSegment, RitualArtifactManifest, RitualRenderOptions

RENDERER_VERSION = "ritual-renderer.v1"
MANIFEST_SCHEMA_VERSION = "hermes_ritual_artifact.v1"


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
        duration_ms = int(plan.get("duration", {}).get("targetSeconds", 300)) * 1000
        captions = self._caption_segments(plan, duration_ms=duration_ms)
        captions_path = output / "captions.vtt"
        captions_path.write_text(self._webvtt(captions), encoding="utf-8")
        manifest = self._manifest(
            plan=plan,
            artifact_id=artifact_id,
            duration_ms=duration_ms,
            captions=captions,
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
        stable_hash = str(plan.get("stableHash") or "").strip()
        if not stable_hash:
            encoded = json.dumps(plan, sort_keys=True, ensure_ascii=False, default=str).encode()
            stable_hash = hashlib.sha256(encoded).hexdigest()
        return f"ritual_artifact_{stable_hash[:16]}"

    def _manifest(
        self,
        *,
        plan: dict[str, object],
        artifact_id: str,
        duration_ms: int,
        captions: list[CaptionSegment],
    ) -> RitualArtifactManifest:
        public_base = str(
            self._options.get("publicBasePath") or f"/artifacts/{artifact_id}"
        ).rstrip("/")
        breath = cast(dict[str, object], plan.get("breath") or {})
        meditation = cast(dict[str, object], plan.get("meditation") or {})
        audio_surface = self._audio_surface(
            plan=plan, public_base=public_base, duration_ms=duration_ms
        )
        surfaces: dict[str, object] = {
            "text": {
                "body": cast(dict[str, object], plan.get("text") or {}).get("body", "")
            },
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
                "inhaleSeconds": int(breath.get("inhaleSeconds", 4) or 4),
                "holdSeconds": int(breath.get("holdSeconds", 0) or 0),
                "exhaleSeconds": int(breath.get("exhaleSeconds", 6) or 6),
                "restSeconds": int(breath.get("restSeconds", 2) or 2),
                "cycles": int(breath.get("cycles", 5) or 5),
                "visualForm": str(breath.get("visualForm") or "pacer"),
                "phaseLabels": True,
            },
            "meditation": {
                "enabled": bool(meditation.get("enabled", False)),
                "fieldType": str(meditation.get("fieldType") or "coherence_convergence"),
                "durationMs": int(
                    meditation.get("durationMs", min(duration_ms, 180000)) or 180000
                ),
                "macroProgressPolicy": str(
                    meditation.get("macroProgressPolicy") or "session_progress"
                ),
                "microMotion": str(meditation.get("microMotion") or "convergence"),
                "instructionDensity": str(meditation.get("instructionDensity") or "sparse"),
            },
            "image": {
                "enabled": False,
                "src": None,
                "alt": "No generated image for this artifact.",
                "provider": None,
            },
            "cinema": {
                "enabled": False,
                "src": None,
                "posterSrc": None,
                "mimeType": None,
                "durationMs": None,
                "provider": None,
            },
        }
        if audio_surface.get("src") is None:
            surfaces["audio"] = audio_surface
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
            "surfaces": surfaces,
            "timeline": self._timeline(plan=plan, captions=captions),
            "interaction": {
                "finishPrompt": cast(dict[str, object], plan.get("interactionSpec") or {}).get(
                    "finishPrompt", "What did you notice?"
                ),
                "captureBodyResponse": True,
                "completionEndpoint": f"/api/artifacts/{artifact_id}/complete",
                "returnCommand": f"/circulation ritual complete {artifact_id}",
            },
            "safety": {
                "stopInstruction": cast(dict[str, object], plan.get("safetyBoundary") or {}).get(
                    "groundingInstruction",
                    "Stop if this increases activation; orient to the room.",
                ),
                "contraindications": cast(
                    dict[str, object], plan.get("voiceScript") or {}
                ).get("contraindications", []),
                "blockedSurfaces": cast(dict[str, object], plan.get("safetyBoundary") or {}).get(
                    "blockedSurfaces", []
                ),
            },
            "render": {
                "rendererVersion": RENDERER_VERSION,
                "mode": str(
                    cast(dict[str, object], plan.get("deliveryPolicy") or {}).get(
                        "renderMode"
                    )
                    or "dry_run_manifest"
                ),
                "providers": ["mock"],
                "cacheKeys": [str(plan.get("stableHash"))] if plan.get("stableHash") else [],
                "budget": {"currency": "USD", "estimated": 0, "actual": 0},
                "warnings": [],
            },
        }

    def _audio_surface(
        self,
        *,
        plan: dict[str, object],
        public_base: str,
        duration_ms: int,
    ) -> dict[str, object]:
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

    def _caption_segments(
        self, plan: dict[str, object], *, duration_ms: int
    ) -> list[CaptionSegment]:
        voice_script = cast(dict[str, object], plan.get("voiceScript") or {})
        raw_segments = [
            item for item in voice_script.get("segments", []) if isinstance(item, dict)
        ]
        captions: list[CaptionSegment] = []
        cursor = 0
        for index, segment in enumerate(raw_segments, start=1):
            text = " ".join(str(segment.get("text") or "").split())
            if not text:
                continue
            word_count = max(len(text.split()), 1)
            segment_ms = min(max(word_count * 520, 3200), 14000)
            pause_ms = int(segment.get("pauseAfterMs", 0) or 0)
            end = min(cursor + segment_ms, duration_ms)
            captions.append(
                {"id": f"cap_{index}", "startMs": cursor, "endMs": end, "text": text}
            )
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
        return sorted(timeline, key=lambda item: int(item.get("atMs", 0)))

    def _webvtt(self, captions: list[CaptionSegment]) -> str:
        blocks = ["WEBVTT", ""]
        for caption in captions:
            blocks.append(caption["id"])
            blocks.append(
                f"{self._vtt_time(caption['startMs'])} --> "
                f"{self._vtt_time(caption['endMs'])}"
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


__all__ = ["RitualRenderer", "render_plan_file"]
