from __future__ import annotations

import json
import uuid
from collections.abc import Mapping
from pathlib import Path
from typing import Any

_TRACE_FILES = {
    "adapter_run": "adapter_runs.jsonl",
    "scoring": "scoring.jsonl",
    "runner_event": "run_events.jsonl",
}


class JourneyTraceSink:
    def __init__(self, run_dir: Path) -> None:
        self._run_dir = run_dir
        self._run_dir.mkdir(parents=True, exist_ok=True)
        self._sanitized_path = run_dir / "sanitized_traces.jsonl"
        self._paths = {kind: run_dir / name for kind, name in _TRACE_FILES.items()}

    def trace_paths(self) -> dict[str, Path]:
        return {
            "sanitized_traces": self._sanitized_path,
            **self._paths,
        }

    def record(self, category: str, payload: Mapping[str, object]) -> str:
        if category not in self._paths:
            raise ValueError(f"Unknown journey trace category '{category}'.")
        trace_id = str(payload.get("traceId") or uuid.uuid4())
        normalized = {
            "schemaVersion": 1,
            "traceId": trace_id,
            **{str(key): value for key, value in payload.items()},
        }
        sanitized = self._sanitize(normalized)
        self._append(self._paths[category], normalized)
        self._append(self._sanitized_path, sanitized)
        return trace_id

    def warning(self, message: str, details: dict[str, object] | None = None) -> None:
        self.record(
            "runner_event",
            {
                "eventType": "warning",
                "message": message,
                "details": details or {},
            },
        )

    def _sanitize(self, payload: dict[str, object]) -> dict[str, object]:
        sanitized = json.loads(json.dumps(payload, default=str))
        for key in ("stdoutText", "stderrText", "rawText"):
            if key in sanitized:
                sanitized[key] = None
                sanitized[f"{key}Redacted"] = True
        return sanitized

    def _append(self, path: Path, payload: dict[str, Any]) -> None:
        with path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(payload, sort_keys=True, default=str) + "\n")
