#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import pty
import re
import select
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
WRAPPER_PLUGIN_DIR = REPO_ROOT / "hermes_plugin" / "circulatio"
DEFAULT_NOTE_TEXT = "I keep thinking about her when I do my wash."
DEFAULT_LABEL = "Laundry return"
DEFAULT_UPDATED_LABEL = "Laundry return thread"
ANSI_RE = re.compile(r"\x1b(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])")
MATERIAL_ID_RE = re.compile(r"materialId=([A-Za-z0-9_]+)")
JOURNEY_ID_RE = re.compile(r"Journey id:\s*([A-Za-z0-9_]+)")


class SmokeSkip(RuntimeError):
    pass


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Run an external Hermes-host smoke path against a temporary Hermes home using "
            "the Circulatio plugin installed in the active Hermes environment."
        )
    )
    parser.add_argument(
        "--hermes-bin",
        default=os.environ.get("CIRCULATIO_HERMES_BIN") or shutil.which("hermes"),
        help="Hermes CLI binary to execute.",
    )
    parser.add_argument(
        "--source-hermes-home",
        default=(
            os.environ.get("CIRCULATIO_HERMES_SOURCE_HOME")
            or os.environ.get("HERMES_HOME")
            or str(Path.home() / ".hermes")
        ),
        help="Existing Hermes home to copy config.yaml and .env from.",
    )
    parser.add_argument(
        "--note-text",
        default=DEFAULT_NOTE_TEXT,
        help="Reflection text to store through Hermes tool routing.",
    )
    parser.add_argument(
        "--label",
        default=DEFAULT_LABEL,
        help="Journey label to create in the smoke flow.",
    )
    parser.add_argument(
        "--updated-label",
        default=DEFAULT_UPDATED_LABEL,
        help="Journey label to use after the update step.",
    )
    parser.add_argument(
        "--require-host",
        action="store_true",
        help="Fail instead of skipping when Hermes host prerequisites are unavailable.",
    )
    parser.add_argument(
        "--keep-temp",
        action="store_true",
        help="Keep the temporary Hermes home directory.",
    )
    return parser.parse_args()


def sanitize_output(text: str) -> str:
    text = ANSI_RE.sub("", text)
    text = text.replace("\r", "\n").replace("\x00", "")
    text = text.replace("\u001b[2004h", "").replace("\u001b[2004l", "")
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def copy_if_present(source: Path, target: Path) -> None:
    if source.exists():
        shutil.copy2(source, target)


def stage_wrapper_plugin(hermes_home: Path) -> Path:
    plugins_dir = hermes_home / "plugins"
    plugins_dir.mkdir(parents=True, exist_ok=True)
    target = plugins_dir / "circulatio"
    shutil.copytree(WRAPPER_PLUGIN_DIR, target)
    return target


def build_env(*, hermes_home: Path) -> dict[str, str]:
    env = os.environ.copy()
    env["HERMES_HOME"] = str(hermes_home)
    env["TERM"] = env.get("TERM", "dumb")
    env["NO_COLOR"] = "1"
    env["COLUMNS"] = env.get("COLUMNS", "120")
    env["LINES"] = env.get("LINES", "40")
    return env


def run_process(
    cmd: list[str],
    *,
    env: dict[str, str],
    timeout: int,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        cmd,
        cwd=REPO_ROOT,
        env=env,
        capture_output=True,
        text=True,
        timeout=timeout,
    )


def enable_plugin(
    *,
    hermes_bin: str,
    env: dict[str, str],
    plugin_name: str,
) -> str:
    result = run_process(
        [hermes_bin, "plugins", "enable", plugin_name],
        env=env,
        timeout=60,
    )
    output = sanitize_output(f"{result.stdout}\n{result.stderr}")
    if result.returncode != 0:
        if "not installed or bundled" in output:
            raise SmokeSkip(
                "Circulatio is not installed in the Hermes environment used by the hermes "
                "binary. Install it there first, then rerun the smoke harness."
            )
        raise RuntimeError(
            f"Hermes could not enable the {plugin_name} plugin in the temporary profile.\n{output}"
        )
    return output


def require_hermes_binary(raw_path: str | None) -> str:
    if raw_path and shutil.which(raw_path):
        return shutil.which(raw_path) or raw_path
    if raw_path and Path(raw_path).exists():
        return raw_path
    raise SmokeSkip(
        "Hermes CLI was not found. Install Hermes locally or pass --hermes-bin /path/to/hermes."
    )


def query_store_material(
    *,
    hermes_bin: str,
    env: dict[str, str],
    note_text: str,
) -> str:
    prompt = (
        "Call the circulatio_store_reflection tool to store this note without "
        f"interpreting it: {note_text} After the tool call, respond with only "
        "materialId=<id>."
    )
    result = run_process(
        [
            hermes_bin,
            "chat",
            "-q",
            prompt,
            "-Q",
            "-t",
            "circulatio",
            "--max-turns",
            "6",
        ],
        env=env,
        timeout=180,
    )
    output = sanitize_output(f"{result.stdout}\n{result.stderr}")
    if result.returncode != 0 and "configured yet" in output:
        raise SmokeSkip(
            "Hermes provider configuration is unavailable in the temporary profile. "
            "Ensure the source Hermes home has a working config.yaml/.env."
        )
    if result.returncode != 0 and "API call failed" in output:
        raise SmokeSkip(
            "Hermes could not complete the host-routed reflection store call. "
            "A working model/provider configuration is required for the true host smoke."
        )
    match = MATERIAL_ID_RE.search(output)
    if result.returncode != 0 or match is None:
        raise RuntimeError(
            "Hermes did not complete the reflection store step successfully.\n"
            f"{output}"
        )
    return match.group(1)


def run_slash_command(
    *,
    hermes_bin: str,
    env: dict[str, str],
    command: str,
    expected_substrings: list[str],
    timeout: int,
) -> str:
    master_fd, slave_fd = pty.openpty()
    process = subprocess.Popen(
        [hermes_bin, "chat", "-Q", "--max-turns", "1"],
        cwd=REPO_ROOT,
        env=env,
        stdin=slave_fd,
        stdout=slave_fd,
        stderr=slave_fd,
        close_fds=True,
    )
    os.close(slave_fd)
    try:
        _read_until(master_fd, expected_substrings=["❯"], timeout=20)
        os.write(master_fd, (command + "\r").encode("utf-8"))
        output = _read_until(master_fd, expected_substrings=expected_substrings, timeout=timeout)
        tail = _read_until_quiet(master_fd, quiet_seconds=1.0, timeout=5)
        return sanitize_output("\n".join(part for part in (output, tail) if part))
    finally:
        try:
            process.terminate()
        except OSError:
            pass
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=5)
        os.close(master_fd)


def _read_until(
    master_fd: int,
    *,
    expected_substrings: list[str],
    timeout: int,
) -> str:
    chunks: list[str] = []
    deadline = time.time() + timeout
    while time.time() < deadline:
        ready, _, _ = select.select([master_fd], [], [], 0.25)
        if not ready:
            continue
        chunk = os.read(master_fd, 4096)
        if not chunk:
            break
        chunks.append(chunk.decode("utf-8", errors="replace"))
        cleaned = sanitize_output("".join(chunks))
        if all(item in cleaned for item in expected_substrings):
            return cleaned
    cleaned = sanitize_output("".join(chunks))
    expected = ", ".join(expected_substrings)
    raise RuntimeError(
        f"Timed out waiting for Hermes output containing: {expected}\n{cleaned[-4000:]}"
    )


def _read_until_quiet(
    master_fd: int,
    *,
    quiet_seconds: float,
    timeout: int,
) -> str:
    chunks: list[str] = []
    deadline = time.time() + timeout
    quiet_deadline: float | None = None
    while time.time() < deadline:
        ready, _, _ = select.select([master_fd], [], [], 0.25)
        if ready:
            chunk = os.read(master_fd, 4096)
            if not chunk:
                break
            chunks.append(chunk.decode("utf-8", errors="replace"))
            quiet_deadline = time.time() + quiet_seconds
            continue
        if quiet_deadline is not None and time.time() >= quiet_deadline:
            break
    return sanitize_output("".join(chunks))


def extract_journey_id(output: str) -> str:
    match = JOURNEY_ID_RE.search(output)
    if match is None:
        raise RuntimeError(f"Could not extract Journey id from output.\n{output}")
    return match.group(1)


def main() -> int:
    args = parse_args()
    temp_home_path = Path(tempfile.mkdtemp(prefix="circulatio-hermes-home-"))
    try:
        hermes_bin = require_hermes_binary(args.hermes_bin)
        source_home = Path(args.source_hermes_home).expanduser()
        staged_plugin_dir = stage_wrapper_plugin(temp_home_path)
        copy_if_present(source_home / "config.yaml", temp_home_path / "config.yaml")
        copy_if_present(source_home / ".env", temp_home_path / ".env")
        env = build_env(hermes_home=temp_home_path)
        enable_plugin(hermes_bin=hermes_bin, env=env, plugin_name="circulatio")

        plugins_output = run_slash_command(
            hermes_bin=hermes_bin,
            env=env,
            command="/plugins",
            expected_substrings=["circulatio"],
            timeout=30,
        )

        slash_list_output = run_slash_command(
            hermes_bin=hermes_bin,
            env=env,
            command="/circulation journey list",
            expected_substrings=["No journeys matched."],
            timeout=30,
        )
        material_id = query_store_material(
            hermes_bin=hermes_bin,
            env=env,
            note_text=args.note_text,
        )
        create_output = run_slash_command(
            hermes_bin=hermes_bin,
            env=env,
            command=(
                f'/circulation journey create --label "{args.label}" '
                f'--question "Why does this return in ordinary rhythm?" '
                f"--material-id {material_id}"
            ),
            expected_substrings=["Journey id:", f"Journey: {args.label} (active)"],
            timeout=30,
        )
        journey_id = extract_journey_id(create_output)

        get_output = run_slash_command(
            hermes_bin=hermes_bin,
            env=env,
            command=f'/circulation journey get --label "{args.label}"',
            expected_substrings=[f"Journey id: {journey_id}"],
            timeout=30,
        )
        update_output = run_slash_command(
            hermes_bin=hermes_bin,
            env=env,
            command=(
                f'/circulation journey update --label "{args.label}" '
                f'--new-label "{args.updated_label}" '
                f'--question "What keeps looping back here?"'
            ),
            expected_substrings=[
                f"Journey: {args.updated_label} (active)",
                "Question: What keeps looping back here?",
            ],
            timeout=30,
        )
        list_output = run_slash_command(
            hermes_bin=hermes_bin,
            env=env,
            command="/circulation journey list --status active",
            expected_substrings=[f"{args.updated_label} (active) [{journey_id}]"],
            timeout=30,
        )
        page_output = run_slash_command(
            hermes_bin=hermes_bin,
            env=env,
            command="/circulation journey",
            expected_substrings=["Journey page", "Alive today:"],
            timeout=180,
        )
        pause_output = run_slash_command(
            hermes_bin=hermes_bin,
            env=env,
            command=f'/circulation journey pause --label "{args.updated_label}"',
            expected_substrings=[f"Journey: {args.updated_label} (paused)"],
            timeout=30,
        )
        resume_output = run_slash_command(
            hermes_bin=hermes_bin,
            env=env,
            command=f'/circulation journey resume --label "{args.updated_label}"',
            expected_substrings=[f"Journey: {args.updated_label} (active)"],
            timeout=30,
        )
        persisted_output = run_slash_command(
            hermes_bin=hermes_bin,
            env=env,
            command=f"/circulation journey get {journey_id}",
            expected_substrings=[
                f"Journey id: {journey_id}",
                f"Journey: {args.updated_label} (active)",
            ],
            timeout=30,
        )

        print("PASS: external Hermes host smoke succeeded.")
        print(f"Hermes binary: {hermes_bin}")
        print(f"Temporary Hermes home: {temp_home_path}")
        print(f"Staged wrapper plugin: {staged_plugin_dir}")
        print(f"Material id: {material_id}")
        print(f"Journey id: {journey_id}")
        print("Verified:")
        print("- plugin is discoverable, enabled, and loaded in a real Hermes session")
        print("- host-routed reflection storage succeeds")
        print("- /circulation journey list|create|get|update|pause|resume works")
        print("- journey state persists across separate Hermes invocations")
        print("- /circulation journey renders the journey page surface")

        _ = (
            plugins_output,
            slash_list_output,
            get_output,
            update_output,
            list_output,
            page_output,
            pause_output,
            resume_output,
            persisted_output,
        )
        return 0
    except SmokeSkip as exc:
        message = f"SKIPPED: {exc}"
        if args.require_host:
            print(message, file=sys.stderr)
            return 1
        print(message)
        return 0
    except Exception as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        if args.keep_temp:
            print(f"Temporary Hermes home: {temp_home_path}", file=sys.stderr)
        return 1
    finally:
        if not args.keep_temp:
            shutil.rmtree(temp_home_path, ignore_errors=True)


if __name__ == "__main__":
    raise SystemExit(main())
