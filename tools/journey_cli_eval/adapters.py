from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path

from .config import AdapterConfig


@dataclass
class CommandSpec:
    adapter: str
    case_id: str
    argv: list[str]
    cwd: Path
    stdin_text: str | None
    timeout_seconds: int
    output_mode: str
    command_display: list[str]
    prompt_path: Path | None = None
    synthetic_stdout: str | None = None
    synthetic_stderr: str = ""


@dataclass
class RawCliRun:
    adapter: str
    case_id: str
    attempt: int
    command_display: list[str]
    command_hash: str
    cwd: str
    started_at: str
    duration_ms: int
    exit_code: int | None
    timed_out: bool
    stdout_path: str
    stderr_path: str
    stdout_sha256: str
    stderr_sha256: str
    version: str | None
    error: str | None
    adapter_status: str
    workspace_diff: list[dict[str, object]] = field(default_factory=list)
    cache_hit: bool = False
    stdout_text: str = ""
    stderr_text: str = ""

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


def command_hash(command_display: list[str], *, stdin_text: str | None = None) -> str:
    payload = json.dumps(
        {
            "command": command_display,
            "stdin": hashlib.sha256((stdin_text or "").encode("utf-8")).hexdigest(),
        },
        sort_keys=True,
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def adapter_requested_names(
    requested: str | list[str],
    configs: dict[str, AdapterConfig],
) -> list[str]:
    items = [requested] if isinstance(requested, str) else requested
    normalized = [str(item) for item in items]
    if normalized == ["all"]:
        return [name for name, config in configs.items() if config.enabled_by_default]
    return normalized


def adapter_available(config: AdapterConfig) -> bool:
    if config.name == "fake":
        return True
    if not config.binary:
        return False
    return shutil.which(config.binary) is not None


def collect_adapter_version(config: AdapterConfig) -> str | None:
    if config.name == "fake" or not config.version_command:
        return "built-in"
    if not adapter_available(config):
        return None
    try:
        result = subprocess.run(
            config.version_command,
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
    except OSError:
        return None
    output = (result.stdout or result.stderr or "").strip()
    return output.splitlines()[0] if output else None


def _matcher_pick(matcher: object, *, default: object = None) -> object:
    if not isinstance(matcher, dict):
        return default
    for key in ("equals", "contains", "prefix"):
        if key in matcher:
            return matcher[key]
    options = matcher.get("oneOf")
    if isinstance(options, list) and options:
        return options[0]
    return default


def _response_from_expected(case: dict[str, object]) -> dict[str, object]:
    turn_results: list[dict[str, object]] = []
    for turn in list(case.get("turns", [])):
        if not isinstance(turn, dict):
            continue
        expected = turn.get("expected") if isinstance(turn.get("expected"), dict) else {}
        tool_value = _matcher_pick(expected.get("toolSequence"), default=[])
        if isinstance(tool_value, list):
            tool_sequence = [str(item) for item in tool_value if item is not None]
        elif tool_value is None:
            tool_sequence = []
        else:
            tool_sequence = [str(tool_value)]
        capture_value = _matcher_pick(expected.get("captureTargets"), default=[])
        if isinstance(capture_value, list):
            capture_targets = [str(item) for item in capture_value if item is not None]
        elif capture_value is None:
            capture_targets = []
        else:
            capture_targets = [str(capture_value)]
        turn_results.append(
            {
                "turnId": str(turn.get("turnId") or ""),
                "selectedToolSequence": tool_sequence,
                "selectedSurface": _matcher_pick(expected.get("selectedSurface"), default=None),
                "selectedMoveKind": _matcher_pick(expected.get("selectedMoveKind"), default=None),
                "depthLevel": _matcher_pick(expected.get("depthLevel"), default=None),
                "captureTargets": capture_targets,
                "writeActions": list(expected.get("allowedWrites", [])),
                "askedClarification": bool(expected.get("shouldAskClarification", False)),
                "performedHostInterpretation": bool(
                    expected.get("shouldPerformHostInterpretation", False)
                ),
                "forbiddenEscalationsPresent": [],
                "hostReply": "I held that and can stay with the next small step.",
                "confidence": 0.9,
                "rationale": (
                    "Fake adapter mirrors the case expectation "
                    "for deterministic harness tests."
                ),
            }
        )
    return {
        "caseId": str(case.get("caseId") or ""),
        "turnResults": turn_results,
        "globalNotes": [],
    }


def _fake_stdout(case: dict[str, object], *, mode: str) -> str:
    if mode == "malformed_json":
        return '{"caseId": "broken", "turnResults": [}'
    if mode == "host_interpretation":
        payload = _response_from_expected(case)
        if payload["turnResults"]:
            payload["turnResults"][0]["performedHostInterpretation"] = True
            payload["turnResults"][0]["hostReply"] = "This means your shadow is active."
        return json.dumps(payload)
    return json.dumps(_response_from_expected(case))


def build_command(
    config: AdapterConfig,
    *,
    prompt_text: str,
    workspace_dir: Path,
    case: dict[str, object],
    timeout_override: int | None = None,
) -> CommandSpec:
    timeout_seconds = timeout_override or config.timeout_seconds
    prompt_path: Path | None = None
    argv = list(config.command)
    stdin_text: str | None = None
    command_display = list(argv)
    if config.name == "fake":
        return CommandSpec(
            adapter=config.name,
            case_id=str(case.get("caseId") or ""),
            argv=[],
            cwd=workspace_dir,
            stdin_text=None,
            timeout_seconds=timeout_seconds,
            output_mode=config.output_mode,
            command_display=["<fake>"],
            synthetic_stdout=_fake_stdout(case, mode=config.mode),
        )
    if bool(config.extra.get("useOutputSchema")):
        output_schema_path = workspace_dir / "output_schema.json"
        if output_schema_path.exists():
            argv.extend(["--output-schema", str(output_schema_path)])
            command_display.extend(["--output-schema", "<OUTPUT_SCHEMA_FILE>"])
    if config.prompt_transport == "stdin":
        stdin_text = prompt_text
    elif config.prompt_transport == "argv":
        if len(prompt_text.encode("utf-8")) > config.max_arg_bytes:
            if not config.allow_prompt_file_fallback:
                raise ValueError(
                    "Prompt for adapter "
                    f"'{config.name}' exceeded maxArgBytes without file fallback."
                )
            prompt_path = workspace_dir / "prompt.txt"
            prompt_path.write_text(prompt_text)
            argv.append(str(prompt_path))
            command_display.append("<PROMPT_FILE>")
        else:
            argv.append(prompt_text)
            command_display.append("<PROMPT>")
    elif config.prompt_transport == "file":
        prompt_path = workspace_dir / "prompt.txt"
        prompt_path.write_text(prompt_text)
        argv = [str(prompt_path) if item == "{prompt_path}" else item for item in argv]
        command_display = ["<PROMPT_FILE>" if item == str(prompt_path) else item for item in argv]
    else:
        raise ValueError(f"Unsupported prompt transport '{config.prompt_transport}'.")
    return CommandSpec(
        adapter=config.name,
        case_id=str(case.get("caseId") or ""),
        argv=argv,
        cwd=workspace_dir,
        stdin_text=stdin_text,
        timeout_seconds=timeout_seconds,
        output_mode=config.output_mode,
        command_display=command_display,
        prompt_path=prompt_path,
    )


def started_at_now() -> str:
    return datetime.now(UTC).isoformat()
