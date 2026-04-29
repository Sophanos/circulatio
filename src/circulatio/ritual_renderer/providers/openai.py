from __future__ import annotations

import json
import mimetypes
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, cast

from ..env import token_from_env_or_file


class OpenAITranscriptionError(RuntimeError):
    pass


OPENAI_TRANSCRIPTIONS_URL = "https://api.openai.com/v1/audio/transcriptions"
OPENAI_TRANSCRIPTION_MODELS = {
    "gpt-4o-transcribe",
    "gpt-4o-mini-transcribe",
    "gpt-4o-mini-transcribe-2025-12-15",
    "gpt-4o-transcribe-diarize",
    "whisper-1",
}


def transcribe_audio(
    *,
    token: str,
    audio_path: Path,
    model: str = "whisper-1",
    language: str | None = None,
    response_format: str = "verbose_json",
    timeout_seconds: int = 180,
) -> dict[str, Any]:
    clean_model = model if model in OPENAI_TRANSCRIPTION_MODELS else "whisper-1"
    clean_format = _response_format(clean_model, response_format)
    fields: dict[str, str] = {"model": clean_model, "response_format": clean_format}
    if language:
        fields["language"] = language
    if clean_model == "gpt-4o-transcribe-diarize" and clean_format == "diarized_json":
        fields["chunking_strategy"] = "auto"
    response = _post_multipart(
        token=token,
        url=OPENAI_TRANSCRIPTIONS_URL,
        fields=fields,
        file_field="file",
        file_path=audio_path,
        timeout_seconds=timeout_seconds,
    )
    if clean_format == "json" and isinstance(response, dict):
        response.setdefault("model", clean_model)
        return cast(dict[str, Any], response)
    if clean_format in {"verbose_json", "diarized_json"} and isinstance(response, dict):
        response.setdefault("model", clean_model)
        return cast(dict[str, Any], response)
    if clean_format in {"text", "vtt", "srt"} and isinstance(response, str):
        return {"text": response, "model": clean_model, "response_format": clean_format}
    if isinstance(response, dict):
        return cast(dict[str, Any], response)
    raise OpenAITranscriptionError("OpenAI transcription response had an unsupported shape.")


def caption_segments_from_transcription(transcription: dict[str, Any]) -> list[dict[str, object]]:
    raw_segments = transcription.get("segments")
    segments: list[dict[str, object]] = []
    if isinstance(raw_segments, list):
        for index, item in enumerate(raw_segments, start=1):
            if not isinstance(item, dict):
                continue
            text = str(item.get("text") or "").strip()
            if not text:
                continue
            start = _seconds_to_ms(item.get("start"))
            end = _seconds_to_ms(item.get("end"))
            if end <= start:
                continue
            segments.append(
                {
                    "id": str(item.get("id") or f"openai_seg_{index}"),
                    "startMs": start,
                    "endMs": end,
                    "text": text,
                }
            )
    if segments:
        return segments
    text = str(transcription.get("text") or "").strip()
    if not text:
        return []
    duration_ms = max(_seconds_to_ms(transcription.get("duration")), 1000)
    return [{"id": "openai_seg_1", "startMs": 0, "endMs": duration_ms, "text": text}]


def token_from_env(env_name: str = "OPENAI_API_KEY") -> str:
    return token_from_env_or_file(env_name)


def _response_format(model: str, requested: str) -> str:
    allowed = {"json", "text", "srt", "verbose_json", "vtt", "diarized_json"}
    clean = requested if requested in allowed else "json"
    if model == "gpt-4o-transcribe" or model.startswith("gpt-4o-mini-transcribe"):
        return clean if clean in {"json", "text"} else "json"
    if model == "gpt-4o-transcribe-diarize":
        return clean if clean in {"json", "text", "diarized_json"} else "diarized_json"
    return clean


def _seconds_to_ms(value: object) -> int:
    try:
        seconds = float(cast(float | int | str, value or 0))
    except (TypeError, ValueError):
        return 0
    return max(int(round(seconds * 1000)), 0)


def _post_multipart(
    *,
    token: str,
    url: str,
    fields: dict[str, str],
    file_field: str,
    file_path: Path,
    timeout_seconds: int,
) -> dict[str, Any] | str:
    if not token:
        raise OpenAITranscriptionError("OpenAI API token is required.")
    if not file_path.exists():
        raise OpenAITranscriptionError("Audio file for transcription does not exist.")
    boundary = "----circulatio-openai-transcription"
    body = bytearray()
    for name, value in fields.items():
        body.extend(f"--{boundary}\r\n".encode("ascii"))
        body.extend(f'Content-Disposition: form-data; name="{name}"\r\n\r\n'.encode("ascii"))
        body.extend(str(value).encode("utf-8"))
        body.extend(b"\r\n")
    filename = file_path.name
    mime_type = mimetypes.guess_type(filename)[0] or "application/octet-stream"
    body.extend(f"--{boundary}\r\n".encode("ascii"))
    disposition = f'Content-Disposition: form-data; name="{file_field}"; filename="{filename}"\r\n'
    body.extend(disposition.encode())
    body.extend(f"Content-Type: {mime_type}\r\n\r\n".encode("ascii"))
    body.extend(file_path.read_bytes())
    body.extend(b"\r\n")
    body.extend(f"--{boundary}--\r\n".encode("ascii"))
    request = urllib.request.Request(
        url,
        data=bytes(body),
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": f"multipart/form-data; boundary={boundary}",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
            content = response.read().decode("utf-8", errors="replace")
            content_type = response.headers.get("content-type", "")
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")[:400]
        message = f"OpenAI transcription failed: HTTP {exc.code} {detail}"
        raise OpenAITranscriptionError(message) from exc
    except OSError as exc:
        raise OpenAITranscriptionError(f"OpenAI transcription request failed: {exc}") from exc
    if "application/json" in content_type:
        try:
            parsed = json.loads(content)
        except json.JSONDecodeError as exc:
            raise OpenAITranscriptionError("OpenAI transcription returned invalid JSON.") from exc
        if not isinstance(parsed, dict):
            raise OpenAITranscriptionError("OpenAI transcription JSON was not an object.")
        return cast(dict[str, Any], parsed)
    if content.strip().startswith("{"):
        try:
            parsed = json.loads(content)
        except json.JSONDecodeError:
            return content
        if isinstance(parsed, dict):
            return cast(dict[str, Any], parsed)
    return content


__all__ = [
    "OPENAI_TRANSCRIPTIONS_URL",
    "OPENAI_TRANSCRIPTION_MODELS",
    "OpenAITranscriptionError",
    "caption_segments_from_transcription",
    "token_from_env",
    "transcribe_audio",
]
