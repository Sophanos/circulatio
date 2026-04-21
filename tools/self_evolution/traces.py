from __future__ import annotations

import json
import uuid
from collections.abc import Mapping
from pathlib import Path
from typing import Any

_TRACE_FILES = {
    "generation_trace": "generation_trace.jsonl",
    "execution_trace": "execution_traces.jsonl",
    "judge_trace": "judge_scores.jsonl",
    "candidate_event": "run_events.jsonl",
}


class JsonlTraceSink:
    def __init__(self, run_dir: Path, *, trace_raw: bool = False, strict: bool = False) -> None:
        self._run_dir = run_dir
        self._run_dir.mkdir(parents=True, exist_ok=True)
        self._trace_raw = trace_raw
        self._strict = strict
        self._sanitized_path = run_dir / "sanitized_traces.jsonl"
        self._paths = {kind: run_dir / filename for kind, filename in _TRACE_FILES.items()}

    def trace_paths(self) -> dict[str, Path]:
        return {
            "sanitized_traces": self._sanitized_path,
            **{kind: path for kind, path in self._paths.items()},
        }

    def record(self, category: str, payload: Mapping[str, object]) -> str:
        if category not in self._paths:
            raise ValueError(f"Unknown trace category: {category}")
        trace_id = str(payload.get("traceId") or uuid.uuid4())
        normalized = {
            "schemaVersion": 1,
            "traceId": trace_id,
            **{str(key): value for key, value in payload.items()},
        }
        sanitized = self._sanitize(category, normalized)
        self._append(self._paths[category], normalized)
        self._append(self._sanitized_path, sanitized)
        return trace_id

    def warning(self, message: str, details: dict[str, object] | None = None) -> None:
        self.record(
            "candidate_event",
            {
                "eventType": "warning",
                "message": message,
                "details": details or {},
            },
        )

    def _sanitize(self, category: str, payload: dict[str, object]) -> dict[str, object]:
        sanitized = json.loads(json.dumps(payload, default=str))
        if not self._trace_raw:
            if "rawText" in sanitized:
                sanitized["rawText"] = None
                sanitized["rawTextRedacted"] = True
            if "parsedOutput" in sanitized and category == "execution_trace":
                output = sanitized.get("parsedOutput")
                if isinstance(output, dict):
                    sanitized["outputSummary"] = {
                        "keys": sorted(str(key) for key in output.keys()),
                        "selectedTool": output.get("selectedTool"),
                    }
        return sanitized

    def _append(self, path: Path, payload: dict[str, Any]) -> None:
        try:
            with path.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(payload, sort_keys=True, default=str) + "\n")
        except OSError as exc:
            if self._strict:
                raise RuntimeError(f"Failed to write trace file: {path}") from exc


def summarize_trace_findings(findings: list[str], *, limit: int = 5) -> list[str]:
    return [str(item) for item in findings[:limit]]
