from __future__ import annotations

import json
import shutil
import tempfile
from dataclasses import dataclass
from pathlib import Path

from .output_schema import OUTPUT_SCHEMA


@dataclass
class WorkspaceBundle:
    root: Path
    case_packet_path: Path
    prompt_path: Path
    output_schema_path: Path
    references_dir: Path
    before_manifest: dict[str, dict[str, object]]


def _sha256_file(path: Path) -> str:
    import hashlib

    return hashlib.sha256(path.read_bytes()).hexdigest()


def compute_workspace_manifest(root: Path) -> dict[str, dict[str, object]]:
    manifest: dict[str, dict[str, object]] = {}
    if not root.exists():
        return manifest
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        stat = path.stat()
        manifest[str(path.relative_to(root))] = {
            "path": str(path.relative_to(root)),
            "size": stat.st_size,
            "sha256": _sha256_file(path),
            "mtime": stat.st_mtime,
        }
    return manifest


def diff_manifests(
    before: dict[str, dict[str, object]],
    after: dict[str, dict[str, object]],
) -> list[dict[str, object]]:
    changes: list[dict[str, object]] = []
    for path in sorted(set(before) | set(after)):
        if path not in before:
            changes.append({"path": path, "status": "added", **after[path]})
        elif path not in after:
            changes.append({"path": path, "status": "deleted", **before[path]})
        elif before[path]["sha256"] != after[path]["sha256"]:
            changes.append({"path": path, "status": "modified", **after[path]})
    return changes


def create_workspace(
    *,
    run_id: str,
    adapter: str,
    case: dict[str, object],
    prompt_text: str,
    case_packet: dict[str, object],
    references: dict[str, str],
) -> WorkspaceBundle:
    temp_root = Path(tempfile.gettempdir()) / f"circulatio-journey-cli-{run_id}" / adapter
    workspace_root = temp_root / str(case.get("caseId") or "case")
    if workspace_root.exists():
        shutil.rmtree(workspace_root)
    references_dir = workspace_root / "references"
    references_dir.mkdir(parents=True, exist_ok=True)
    case_packet_path = workspace_root / "case_packet.json"
    case_packet_path.write_text(json.dumps(case_packet, indent=2, sort_keys=True))
    prompt_path = workspace_root / "prompt.txt"
    prompt_path.write_text(prompt_text)
    output_schema_path = workspace_root / "output_schema.json"
    output_schema_path.write_text(json.dumps(OUTPUT_SCHEMA, indent=2, sort_keys=True))
    for name, text in references.items():
        (references_dir / name).write_text(text)
    before_manifest = compute_workspace_manifest(workspace_root)
    return WorkspaceBundle(
        root=workspace_root,
        case_packet_path=case_packet_path,
        prompt_path=prompt_path,
        output_schema_path=output_schema_path,
        references_dir=references_dir,
        before_manifest=before_manifest,
    )
