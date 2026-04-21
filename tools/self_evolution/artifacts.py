from __future__ import annotations

import hashlib
import shutil
import subprocess
from dataclasses import dataclass
from datetime import UTC, datetime
from difflib import unified_diff
from pathlib import Path

from .targets import REPO_ROOT, EvolutionTarget, get_target


@dataclass(frozen=True)
class CandidateBundlePaths:
    candidate_dir: Path
    candidate_paths: dict[str, Path]
    relative_paths: dict[str, str]
    extra_relative_paths: list[str]


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def current_git_sha() -> str | None:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            check=True,
            capture_output=True,
            cwd=REPO_ROOT,
            text=True,
        )
    except (FileNotFoundError, subprocess.CalledProcessError):
        return None
    return result.stdout.strip() or None


def default_run_id() -> str:
    stamp = datetime.now(tz=UTC).strftime("%Y%m%dT%H%M%SZ")
    return f"evo_{stamp}"


def create_run_directory(out_root: Path, *, run_id: str | None = None) -> Path:
    out_root.mkdir(parents=True, exist_ok=True)
    chosen_run_id = run_id or default_run_id()
    run_dir = out_root / chosen_run_id
    if run_dir.exists():
        raise ValueError(f"Run directory already exists: {run_dir}")
    (run_dir / "candidates").mkdir(parents=True)
    return run_dir


def _search_roots(candidate_dir: Path) -> list[Path]:
    candidates_dir = candidate_dir / "candidates"
    roots: list[Path] = []
    if candidates_dir.is_dir():
        roots.append(candidates_dir)
    roots.append(candidate_dir)
    return roots


def _candidate_lookup_paths(root: Path, target: EvolutionTarget) -> list[Path]:
    return [root / target.baseline_relative_path, root / target.baseline_path.name]


def _dedupe_paths(paths: list[Path]) -> list[Path]:
    seen: set[Path] = set()
    deduped: list[Path] = []
    for path in paths:
        resolved = path.resolve()
        if resolved in seen:
            continue
        seen.add(resolved)
        deduped.append(path)
    return deduped


def _target_by_basename(target_names: tuple[str, ...]) -> dict[str, list[EvolutionTarget]]:
    by_basename: dict[str, list[EvolutionTarget]] = {}
    for target_name in target_names:
        target = get_target(target_name)
        by_basename.setdefault(target.baseline_path.name, []).append(target)
    return by_basename


def _normalized_candidate_relative_path(
    file_path: Path,
    *,
    candidate_root: Path,
    target_names: tuple[str, ...],
) -> str:
    target_by_basename = _target_by_basename(target_names)
    relative = file_path.relative_to(candidate_root)
    relative_text = str(relative)
    for target_name in target_names:
        target = get_target(target_name)
        if relative_text == target.baseline_relative_path:
            return target.baseline_relative_path
    basename_matches = target_by_basename.get(file_path.name, [])
    if len(basename_matches) == 1:
        return basename_matches[0].baseline_relative_path
    return relative_text


def load_candidate_bundle_paths(
    candidate_dir: Path,
    *,
    target_names: tuple[str, ...] | list[str],
) -> CandidateBundlePaths:
    selected_targets = tuple(target_names)
    candidate_paths: dict[str, Path] = {}
    relative_paths: dict[str, str] = {}

    for target_name in selected_targets:
        target = get_target(target_name)
        matches: list[Path] = []
        for root in _search_roots(candidate_dir):
            matches.extend(path for path in _candidate_lookup_paths(root, target) if path.is_file())
        matches = _dedupe_paths(matches)
        if len(matches) > 1:
            joined = ", ".join(str(path) for path in matches)
            raise ValueError(f"Multiple candidate files matched target '{target_name}': {joined}")
        if matches:
            candidate_paths[target_name] = matches[0]
            relative_paths[target_name] = target.baseline_relative_path

    extra_relative_paths: list[str] = []
    candidate_root = candidate_dir / "candidates"
    if candidate_root.is_dir():
        recognized = {path.resolve() for path in candidate_paths.values()}
        for path in sorted(candidate_root.rglob("*")):
            if not path.is_file() or path.resolve() in recognized:
                continue
            extra_relative_paths.append(
                _normalized_candidate_relative_path(
                    path,
                    candidate_root=candidate_root,
                    target_names=selected_targets,
                )
            )

    return CandidateBundlePaths(
        candidate_dir=candidate_dir,
        candidate_paths=candidate_paths,
        relative_paths=relative_paths,
        extra_relative_paths=extra_relative_paths,
    )


def stage_candidate_artifacts(
    *,
    target_names: tuple[str, ...] | list[str],
    candidate_paths: dict[str, Path],
    run_dir: Path,
) -> CandidateBundlePaths:
    selected_targets = tuple(target_names)
    staged_paths: dict[str, Path] = {}
    relative_paths: dict[str, str] = {}
    candidate_root = run_dir / "candidates"
    candidate_root.mkdir(parents=True, exist_ok=True)

    for target_name in selected_targets:
        source_path = candidate_paths.get(target_name)
        if source_path is None:
            continue
        target = get_target(target_name)
        staged_path = candidate_root / target.baseline_path.name
        shutil.copy2(source_path, staged_path)
        staged_paths[target_name] = staged_path
        relative_paths[target_name] = target.baseline_relative_path

    return CandidateBundlePaths(
        candidate_dir=run_dir,
        candidate_paths=staged_paths,
        relative_paths=relative_paths,
        extra_relative_paths=[],
    )


def build_diff_patch(
    *,
    target_names: tuple[str, ...] | list[str],
    candidate_paths: dict[str, Path],
) -> str:
    diff_chunks: list[str] = []
    for target_name in target_names:
        candidate_path = candidate_paths.get(target_name)
        if candidate_path is None:
            continue
        target = get_target(target_name)
        baseline_lines = target.baseline_path.read_text().splitlines(keepends=True)
        candidate_lines = candidate_path.read_text().splitlines(keepends=True)
        diff_chunks.extend(
            unified_diff(
                baseline_lines,
                candidate_lines,
                fromfile=target.baseline_relative_path,
                tofile=f"candidate/{target.baseline_relative_path}",
            )
        )
    return "".join(diff_chunks)


def candidate_hashes(
    *,
    target_names: tuple[str, ...] | list[str],
    candidate_paths: dict[str, Path],
) -> tuple[dict[str, str], dict[str, str]]:
    base_hashes: dict[str, str] = {}
    staged_hashes: dict[str, str] = {}
    for target_name in target_names:
        target = get_target(target_name)
        candidate_path = candidate_paths.get(target_name)
        if candidate_path is None:
            continue
        base_hashes[target.baseline_relative_path] = sha256_file(target.baseline_path)
        staged_hashes[target.baseline_relative_path] = sha256_file(candidate_path)
    return base_hashes, staged_hashes
