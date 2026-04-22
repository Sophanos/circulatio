from __future__ import annotations

import hashlib
import os
import signal
import subprocess
import time
from pathlib import Path

from .adapters import CommandSpec, RawCliRun, command_hash, started_at_now


def _sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _truncate_text(text: str, *, max_output_bytes: int | None) -> str:
    if max_output_bytes is None:
        return text
    encoded = text.encode("utf-8")
    if len(encoded) <= max_output_bytes:
        return text
    return encoded[:max_output_bytes].decode("utf-8", errors="ignore")


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)


def execute_command(
    command: CommandSpec,
    *,
    stdout_path: Path,
    stderr_path: Path,
    version: str | None,
    attempt: int = 1,
    max_output_bytes: int | None = None,
) -> RawCliRun:
    started_at = started_at_now()
    start = time.perf_counter()
    if command.synthetic_stdout is not None:
        stdout_text = command.synthetic_stdout
        stderr_text = command.synthetic_stderr
        _write_text(stdout_path, stdout_text)
        _write_text(stderr_path, stderr_text)
        duration_ms = int((time.perf_counter() - start) * 1000)
        return RawCliRun(
            adapter=command.adapter,
            case_id=command.case_id,
            attempt=attempt,
            command_display=command.command_display,
            command_hash=command_hash(command.command_display, stdin_text=command.stdin_text),
            cwd=str(command.cwd),
            started_at=started_at,
            duration_ms=duration_ms,
            exit_code=0,
            timed_out=False,
            stdout_path=str(stdout_path),
            stderr_path=str(stderr_path),
            stdout_sha256=_sha256_text(stdout_text),
            stderr_sha256=_sha256_text(stderr_text),
            version=version,
            error=None,
            adapter_status="ok",
            stdout_text=stdout_text,
            stderr_text=stderr_text,
        )

    process = subprocess.Popen(
        command.argv,
        cwd=str(command.cwd),
        stdin=subprocess.PIPE if command.stdin_text is not None else None,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        start_new_session=True,
    )
    stdout_text = ""
    stderr_text = ""
    timed_out = False
    error: str | None = None
    exit_code: int | None = None
    try:
        stdout_text, stderr_text = process.communicate(
            input=command.stdin_text,
            timeout=command.timeout_seconds,
        )
        exit_code = process.returncode
    except subprocess.TimeoutExpired as exc:
        timed_out = True
        stdout_text = exc.stdout or ""
        stderr_text = exc.stderr or ""
        error = f"Timed out after {command.timeout_seconds} seconds."
        try:
            os.killpg(process.pid, signal.SIGTERM)
        except OSError:
            pass
        try:
            stdout_kill, stderr_kill = process.communicate(timeout=5)
            stdout_text += stdout_kill or ""
            stderr_text += stderr_kill or ""
        except subprocess.TimeoutExpired:
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except OSError:
                pass
            stdout_kill, stderr_kill = process.communicate()
            stdout_text += stdout_kill or ""
            stderr_text += stderr_kill or ""
        exit_code = process.returncode
    except OSError as exc:
        error = str(exc)
    _write_text(stdout_path, stdout_text)
    _write_text(stderr_path, stderr_text)
    duration_ms = int((time.perf_counter() - start) * 1000)
    return RawCliRun(
        adapter=command.adapter,
        case_id=command.case_id,
        attempt=attempt,
        command_display=command.command_display,
        command_hash=command_hash(command.command_display, stdin_text=command.stdin_text),
        cwd=str(command.cwd),
        started_at=started_at,
        duration_ms=duration_ms,
        exit_code=exit_code,
        timed_out=timed_out,
        stdout_path=str(stdout_path),
        stderr_path=str(stderr_path),
        stdout_sha256=_sha256_text(stdout_text),
        stderr_sha256=_sha256_text(stderr_text),
        version=version,
        error=error,
        adapter_status="ok" if error is None and not timed_out else "failed",
        stdout_text=stdout_text,
        stderr_text=stderr_text,
    )
