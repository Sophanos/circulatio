from __future__ import annotations

import os
from pathlib import Path


def token_from_env_or_file(env_name: str, *, cwd: Path | None = None) -> str:
    clean_name = env_name.strip()
    if not clean_name:
        return ""
    existing = os.environ.get(clean_name, "").strip()
    if existing:
        return existing
    for env_path in _candidate_env_files(cwd or Path.cwd()):
        value = _read_env_value(env_path, clean_name)
        if value:
            return value
    return ""


def _candidate_env_files(start: Path) -> list[Path]:
    candidates: list[Path] = []
    for root in _candidate_roots(start.resolve()):
        env_path = root / ".env"
        if env_path not in candidates:
            candidates.append(env_path)
    return candidates


def _candidate_roots(start: Path) -> list[Path]:
    roots = [start, *start.parents]
    module_root = Path(__file__).resolve()
    roots.extend(module_root.parents)
    return roots


def _read_env_value(env_path: Path, env_name: str) -> str:
    try:
        lines = env_path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return ""
    for line in lines:
        parsed = _parse_env_line(line)
        if parsed is None:
            continue
        key, value = parsed
        if key == env_name:
            return value.strip()
    return ""


def _parse_env_line(line: str) -> tuple[str, str] | None:
    stripped = line.strip()
    if not stripped or stripped.startswith("#") or "=" not in stripped:
        return None
    if stripped.startswith("export "):
        stripped = stripped[len("export ") :].lstrip()
    key, raw_value = stripped.split("=", 1)
    key = key.strip()
    if not key:
        return None
    value = raw_value.strip()
    if value.startswith('"') and value.endswith('"') and len(value) >= 2:
        value = value[1:-1]
    elif value.startswith("'") and value.endswith("'") and len(value) >= 2:
        value = value[1:-1]
    else:
        value = value.split(" #", 1)[0].strip()
    return key, value


__all__ = ["token_from_env_or_file"]
