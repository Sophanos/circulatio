from __future__ import annotations

import hashlib
import json
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Any


class LlmCallCache:
    def __init__(
        self,
        cache_root: Path,
        *,
        event_sink: Callable[[str, dict[str, object] | None], None] | None = None,
    ) -> None:
        self._cache_root = cache_root
        self._cache_root.mkdir(parents=True, exist_ok=True)
        self._path = self._cache_root / "llm_calls.jsonl"
        self._event_sink = event_sink
        self._records = self._load_records()

    @property
    def path(self) -> Path:
        return self._path

    def _emit_warning(self, message: str, details: dict[str, object] | None = None) -> None:
        if self._event_sink is not None:
            self._event_sink(message, details)

    def _load_records(self) -> dict[str, dict[str, object]]:
        if not self._path.exists():
            return {}
        records: dict[str, dict[str, object]] = {}
        for line_number, raw_line in enumerate(self._path.read_text().splitlines(), start=1):
            line = raw_line.strip()
            if not line:
                continue
            try:
                payload = json.loads(line)
            except json.JSONDecodeError:
                self._emit_warning(
                    "Ignoring corrupt LLM cache entry.",
                    {"path": str(self._path), "line": line_number},
                )
                continue
            if not isinstance(payload, dict):
                self._emit_warning(
                    "Ignoring non-object LLM cache entry.",
                    {"path": str(self._path), "line": line_number},
                )
                continue
            cache_key = str(payload.get("cacheKey") or "").strip()
            if not cache_key:
                self._emit_warning(
                    "Ignoring LLM cache entry without cacheKey.",
                    {"path": str(self._path), "line": line_number},
                )
                continue
            records[cache_key] = payload
        return records

    def get(self, cache_key: str) -> dict[str, object] | None:
        payload = self._records.get(cache_key)
        if payload is None:
            return None
        return dict(payload)

    def put(self, payload: Mapping[str, object]) -> None:
        cache_key = str(payload.get("cacheKey") or "").strip()
        if not cache_key:
            raise ValueError("LLM cache payload requires cacheKey.")
        normalized = {str(key): value for key, value in payload.items()}
        self._records[cache_key] = normalized
        try:
            with self._path.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(normalized, sort_keys=True, default=str) + "\n")
        except OSError:
            self._emit_warning(
                "Failed to persist LLM cache entry.",
                {"path": str(self._path), "cacheKey": cache_key},
            )


def build_cache_key(*, schema_name: str | None, metadata: Mapping[str, object]) -> str:
    payload: dict[str, Any] = {
        "schemaName": schema_name,
        **{str(key): value for key, value in metadata.items()},
    }
    encoded = json.dumps(payload, sort_keys=True, default=str).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()
