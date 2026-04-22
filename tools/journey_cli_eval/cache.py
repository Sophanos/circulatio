from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


class JourneyEvalCache:
    def __init__(self, cache_root: Path) -> None:
        self._cache_root = cache_root
        self._cache_root.mkdir(parents=True, exist_ok=True)

    def _path_for(self, cache_key: str) -> Path:
        return self._cache_root / cache_key[:2] / f"{cache_key}.json"

    def get(self, cache_key: str) -> dict[str, object] | None:
        path = self._path_for(cache_key)
        if not path.exists():
            return None
        payload = json.loads(path.read_text())
        if not isinstance(payload, dict):
            return None
        return {str(key): value for key, value in payload.items()}

    def put(self, cache_key: str, payload: dict[str, object]) -> None:
        path = self._path_for(cache_key)
        path.parent.mkdir(parents=True, exist_ok=True)
        normalized = {"cacheKey": cache_key, **payload}
        path.write_text(json.dumps(normalized, indent=2, sort_keys=True, default=str))


def build_cache_key(
    *,
    adapter_name: str,
    adapter_config: dict[str, object],
    adapter_version: str | None,
    case: dict[str, object],
    prompt_text: str,
    artifact_hashes: dict[str, str],
    git_sha: str | None,
) -> str:
    payload: dict[str, Any] = {
        "cacheSchemaVersion": 2,
        "adapter": adapter_name,
        "adapterConfig": adapter_config,
        "adapterVersion": adapter_version,
        "case": case,
        "promptText": prompt_text,
        "artifactHashes": artifact_hashes,
        "gitSha": git_sha,
    }
    encoded = json.dumps(payload, sort_keys=True, default=str).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()
