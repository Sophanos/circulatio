from __future__ import annotations

import base64
import binascii
import json
import mimetypes
import urllib.error
import urllib.request
from collections.abc import Iterable
from pathlib import Path
from typing import Any, TypedDict, cast


class ChutesProviderError(RuntimeError):
    pass


class ChutesAsset(TypedDict):
    path: Path
    mimeType: str
    provider: str
    model: str


KOKORO_SPEAK_URL = "https://chutes-kokoro.chutes.ai/speak"
WHISPER_TRANSCRIBE_URL = "https://chutes-whisper-large-v3.chutes.ai/transcribe"
DIFFRHYTHM_GENERATE_URL = "https://chutes-diffrhythm.chutes.ai/generate"
WAN_I2V_GENERATE_URL = "https://chutes-wan-2-2-i2v-14b-fast.chutes.ai/generate"
Z_IMAGE_GENERATE_URL = "https://chutes-z-image-turbo.chutes.ai/generate"

_AUDIO_KEYS = (
    "audio_b64",
    "audioBase64",
    "audio",
    "wav_b64",
    "wav",
    "mp3_b64",
    "mp3",
    "data",
    "output",
    "result",
)
_IMAGE_KEYS = (
    "image_b64",
    "imageBase64",
    "image",
    "png_b64",
    "png",
    "data",
    "output",
    "result",
)
_VIDEO_KEYS = (
    "video_b64",
    "videoBase64",
    "video",
    "mp4_b64",
    "mp4",
    "data",
    "output",
    "result",
)
_URL_KEYS = (
    "url",
    "audio_url",
    "image_url",
    "video_url",
    "output_url",
    "download_url",
)


def synthesize_speech(
    *,
    token: str,
    text: str,
    out_path: Path,
    timeout_seconds: int = 180,
) -> ChutesAsset:
    return _post_asset(
        token=token,
        url=KOKORO_SPEAK_URL,
        payload={"text": text},
        out_path=out_path,
        default_mime="audio/wav",
        model="chutes-kokoro",
        base64_keys=_AUDIO_KEYS,
        timeout_seconds=timeout_seconds,
    )


def transcribe_audio(
    *,
    token: str,
    audio_path: Path,
    language: str | None = None,
    timeout_seconds: int = 180,
) -> dict[str, Any]:
    audio_b64 = base64.b64encode(audio_path.read_bytes()).decode("ascii")
    response = _post_json(
        token=token,
        url=WHISPER_TRANSCRIBE_URL,
        payload={"language": language, "audio_b64": audio_b64},
        timeout_seconds=timeout_seconds,
    )
    if not isinstance(response, dict):
        raise ChutesProviderError("Chutes Whisper response was not a JSON object.")
    return cast(dict[str, Any], response)


def generate_image(
    *,
    token: str,
    prompt: str,
    out_path: Path,
    timeout_seconds: int = 180,
) -> ChutesAsset:
    return _post_asset(
        token=token,
        url=Z_IMAGE_GENERATE_URL,
        payload={"prompt": prompt},
        out_path=out_path,
        default_mime="image/png",
        model="chutes-z-image-turbo",
        base64_keys=_IMAGE_KEYS,
        timeout_seconds=timeout_seconds,
    )


def generate_music(
    *,
    token: str,
    out_path: Path,
    steps: int = 32,
    audio_b64: str | None = None,
    timeout_seconds: int = 240,
) -> ChutesAsset:
    return _post_asset(
        token=token,
        url=DIFFRHYTHM_GENERATE_URL,
        payload={"steps": steps, "audio_b64": audio_b64},
        out_path=out_path,
        default_mime="audio/wav",
        model="chutes-diffrhythm",
        base64_keys=_AUDIO_KEYS,
        timeout_seconds=timeout_seconds,
    )


def generate_video(
    *,
    token: str,
    prompt: str,
    image: str,
    out_path: Path,
    timeout_seconds: int = 360,
) -> ChutesAsset:
    return _post_asset(
        token=token,
        url=WAN_I2V_GENERATE_URL,
        payload={
            "fast": True,
            "seed": None,
            "image": image,
            "frames": 81,
            "prompt": prompt,
            "guidance_scale_2": 1,
        },
        out_path=out_path,
        default_mime="video/mp4",
        model="chutes-wan-2-2-i2v-14b-fast",
        base64_keys=_VIDEO_KEYS,
        timeout_seconds=timeout_seconds,
    )


def caption_segments_from_transcription(response: dict[str, Any]) -> list[dict[str, object]]:
    raw_segments = _find_list(response, ("segments", "chunks"))
    captions: list[dict[str, object]] = []
    if raw_segments:
        for index, item in enumerate(raw_segments, start=1):
            if not isinstance(item, dict):
                continue
            text = " ".join(str(item.get("text") or "").split())
            if not text:
                continue
            start_seconds = _float_or_none(item.get("start"))
            end_seconds = _float_or_none(item.get("end"))
            if start_seconds is None or end_seconds is None or end_seconds <= start_seconds:
                continue
            captions.append(
                {
                    "id": f"cap_chutes_{index}",
                    "startMs": int(start_seconds * 1000),
                    "endMs": int(end_seconds * 1000),
                    "text": text,
                }
            )
    return captions


def _post_asset(
    *,
    token: str,
    url: str,
    payload: dict[str, object],
    out_path: Path,
    default_mime: str,
    model: str,
    base64_keys: Iterable[str],
    timeout_seconds: int,
) -> ChutesAsset:
    body, content_type = _post_bytes(
        token=token,
        url=url,
        payload=payload,
        timeout_seconds=timeout_seconds,
    )
    mime_type = _content_mime(content_type)
    if mime_type and not mime_type.startswith("application/json"):
        written_path = _write_asset_bytes(out_path, body, mime_type)
        return {
            "path": written_path,
            "mimeType": mime_type,
            "provider": "chutes",
            "model": model,
        }

    try:
        decoded = json.loads(body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        written_path = _write_asset_bytes(out_path, body, default_mime)
        return {
            "path": written_path,
            "mimeType": default_mime,
            "provider": "chutes",
            "model": model,
        }

    if not isinstance(decoded, dict):
        raise ChutesProviderError(f"{model} response was not a JSON object.")
    url_value = _find_url(decoded)
    if url_value:
        downloaded, downloaded_mime = _download_asset(
            url=url_value,
            out_path=out_path,
            default_mime=default_mime,
            timeout_seconds=timeout_seconds,
        )
        return {
            "path": downloaded,
            "mimeType": downloaded_mime,
            "provider": "chutes",
            "model": model,
        }
    b64_value, mime_from_payload = _find_base64_value(decoded, base64_keys)
    if not b64_value:
        raise ChutesProviderError(
            f"{model} response did not include an asset payload or downloadable URL."
        )
    asset_bytes = base64.b64decode(b64_value, validate=False)
    written_path = _write_asset_bytes(out_path, asset_bytes, mime_from_payload or default_mime)
    return {
        "path": written_path,
        "mimeType": mime_from_payload or default_mime,
        "provider": "chutes",
        "model": model,
    }


def _post_json(
    *,
    token: str,
    url: str,
    payload: dict[str, object],
    timeout_seconds: int,
) -> Any:
    body, _ = _post_bytes(
        token=token,
        url=url,
        payload=payload,
        timeout_seconds=timeout_seconds,
    )
    try:
        return json.loads(body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ChutesProviderError("Chutes response was not JSON.") from exc


def _post_bytes(
    *,
    token: str,
    url: str,
    payload: dict[str, object],
    timeout_seconds: int,
) -> tuple[bytes, str]:
    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "Accept": "application/json, audio/*, image/*, video/*",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
            content_type = response.headers.get("Content-Type", "")
            return response.read(), content_type
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")[:500]
        raise ChutesProviderError(f"Chutes HTTP {exc.code}: {detail}") from exc
    except urllib.error.URLError as exc:
        raise ChutesProviderError(f"Chutes request failed: {exc.reason}") from exc


def _download_asset(
    *,
    url: str,
    out_path: Path,
    default_mime: str,
    timeout_seconds: int,
) -> tuple[Path, str]:
    request = urllib.request.Request(url, headers={"Accept": "audio/*, image/*, video/*"})
    with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
        content_type = response.headers.get("Content-Type", "")
        mime_type = _content_mime(content_type) or default_mime
        return _write_asset_bytes(out_path, response.read(), mime_type), mime_type


def _write_asset_bytes(out_path: Path, payload: bytes, mime_type: str) -> Path:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    suffix = mimetypes.guess_extension(mime_type.split(";", 1)[0]) or out_path.suffix
    final_path = out_path.with_suffix(suffix or out_path.suffix)
    final_path.write_bytes(payload)
    return final_path


def _content_mime(content_type: str) -> str:
    return content_type.split(";", 1)[0].strip().lower()


def _find_url(value: Any) -> str | None:
    if isinstance(value, dict):
        for key in _URL_KEYS:
            candidate = value.get(key)
            if isinstance(candidate, str) and candidate.startswith(("http://", "https://")):
                return candidate
        for nested in value.values():
            found = _find_url(nested)
            if found:
                return found
    if isinstance(value, list):
        for item in value:
            found = _find_url(item)
            if found:
                return found
    if isinstance(value, str) and value.startswith(("http://", "https://")):
        return value
    return None


def _find_base64_value(value: Any, keys: Iterable[str]) -> tuple[str | None, str | None]:
    keys_lower = {key.lower() for key in keys}
    if isinstance(value, dict):
        for key, candidate in value.items():
            if key.lower() in keys_lower and isinstance(candidate, str):
                parsed, mime = _parse_base64_value(candidate)
                if parsed:
                    return parsed, mime
        for candidate in value.values():
            parsed, mime = _find_base64_value(candidate, keys)
            if parsed:
                return parsed, mime
    if isinstance(value, list):
        for item in value:
            parsed, mime = _find_base64_value(item, keys)
            if parsed:
                return parsed, mime
    if isinstance(value, str):
        return _parse_base64_value(value)
    return None, None


def _parse_base64_value(value: str) -> tuple[str | None, str | None]:
    normalized = value.strip()
    if not normalized:
        return None, None
    if normalized.startswith("data:") and ";base64," in normalized:
        header, payload = normalized.split(",", 1)
        mime = header.removeprefix("data:").split(";", 1)[0]
        return payload.strip(), mime or None
    if normalized.startswith(("http://", "https://")):
        return None, None
    compact = "".join(normalized.split())
    if len(compact) < 64:
        return None, None
    try:
        base64.b64decode(compact, validate=True)
    except (ValueError, binascii.Error):
        return None, None
    return compact, None


def _find_list(value: Any, keys: Iterable[str]) -> list[Any] | None:
    keys_lower = {key.lower() for key in keys}
    if isinstance(value, dict):
        for key, candidate in value.items():
            if key.lower() in keys_lower and isinstance(candidate, list):
                return candidate
        for candidate in value.values():
            found = _find_list(candidate, keys)
            if found:
                return found
    if isinstance(value, list):
        for item in value:
            found = _find_list(item, keys)
            if found:
                return found
    return None


def _float_or_none(value: Any) -> float | None:
    try:
        if value is None:
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


__all__ = [
    "ChutesAsset",
    "ChutesProviderError",
    "caption_segments_from_transcription",
    "generate_image",
    "generate_music",
    "generate_video",
    "synthesize_speech",
    "transcribe_audio",
]
