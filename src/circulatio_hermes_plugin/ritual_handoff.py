from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import webbrowser
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import cast

from circulatio.hermes.agent_bridge_contracts import BridgeResponseEnvelope
from tools.ritual_renderer.renderer import (
    MANIFEST_SCHEMA_VERSION,
    RENDERER_VERSION,
    artifact_id_for_plan,
)


@dataclass(frozen=True)
class HermesRitualHandoffConfig:
    repo_root: Path
    renderer_script: Path
    plan_store_root: Path
    artifact_public_root: Path
    base_url: str
    mode: str
    open_local_default: bool
    renderer_timeout_seconds: int

    @classmethod
    def from_env(cls) -> HermesRitualHandoffConfig:
        repo_root = Path(
            os.environ.get("CIRCULATIO_REPO_ROOT")
            or Path(__file__).resolve().parents[2]
        ).resolve()
        renderer_script = Path(
            os.environ.get("CIRCULATIO_RENDERER_SCRIPT")
            or repo_root / "scripts" / "render_ritual_artifact.py"
        ).resolve()
        plan_store_root = Path(
            os.environ.get("CIRCULATIO_RITUAL_PLAN_ROOT")
            or repo_root / "artifacts" / "rituals" / "plans"
        ).resolve()
        artifact_public_root = Path(
            os.environ.get("CIRCULATIO_RITUAL_ARTIFACT_ROOT")
            or repo_root / "apps" / "hermes-rituals-web" / "public" / "artifacts"
        ).resolve()
        timeout_raw = os.environ.get("CIRCULATIO_RITUAL_RENDER_TIMEOUT_SECONDS", "60")
        try:
            timeout = max(int(timeout_raw), 1)
        except ValueError:
            timeout = 60
        mode = os.environ.get("CIRCULATIO_RITUAL_HANDOFF_MODE", "render_static")
        if mode not in {"render_static", "plan_only"}:
            mode = "render_static"
        return cls(
            repo_root=repo_root,
            renderer_script=renderer_script,
            plan_store_root=plan_store_root,
            artifact_public_root=artifact_public_root,
            base_url=os.environ.get("CIRCULATIO_RITUALS_BASE_URL", "http://localhost:3000").rstrip("/"),
            mode=mode,
            open_local_default=os.environ.get("CIRCULATIO_RITUAL_OPEN") == "1",
            renderer_timeout_seconds=timeout,
        )


class HermesRitualArtifactHandoff:
    def __init__(self, config: HermesRitualHandoffConfig | None = None) -> None:
        self._config = config or HermesRitualHandoffConfig.from_env()

    def render_from_bridge_response(
        self,
        response: BridgeResponseEnvelope,
        *,
        open_local: bool = False,
    ) -> dict[str, object]:
        if self._config.mode == "plan_only":
            return {"status": "skipped", "warnings": []}
        result = response.get("result")
        if response.get("status") != "ok" or not isinstance(result, dict):
            return {"status": "skipped", "warnings": []}
        plan = result.get("plan")
        if not isinstance(plan, dict):
            return {"status": "skipped", "warnings": []}

        try:
            return self._render(
                response=response,
                result=result,
                plan=cast(dict[str, object], plan),
                open_local=open_local or self._config.open_local_default,
            )
        except subprocess.TimeoutExpired:
            return self._failure(retryable=True)
        except (OSError, subprocess.CalledProcessError) as exc:
            return self._failure(retryable=True, detail=str(exc))
        except ValueError as exc:
            return self._failure(retryable=False, detail=str(exc))

    def _render(
        self,
        *,
        response: BridgeResponseEnvelope,
        result: dict[str, object],
        plan: dict[str, object],
        open_local: bool,
    ) -> dict[str, object]:
        plan_id = str(plan.get("id") or result.get("planId") or "").strip()
        if not plan_id:
            raise ValueError("Ritual plan id is required for local handoff.")
        artifact_id = artifact_id_for_plan(plan)
        public_base = f"/artifacts/{artifact_id}"
        route = f"/artifacts/{artifact_id}"
        url = f"{self._config.base_url}{route}"
        plan_path = self._persist_plan(response=response, result=result, plan=plan, plan_id=plan_id)
        final_dir = self._config.artifact_public_root / artifact_id
        final_manifest = final_dir / "manifest.json"
        if final_manifest.exists() and self._manifest_valid(final_manifest, artifact_id, plan_id):
            return self._success(
                artifact_id=artifact_id,
                url=url,
                route=route,
                public_base=public_base,
                plan_path=plan_path,
                manifest_path=final_manifest,
                opened=self._open_if_requested(url, open_local),
            )

        request_short = str(response.get("requestId") or "request")[-12:].replace(os.sep, "_")
        staging_dir = self._config.artifact_public_root / f".tmp-{artifact_id}-{request_short}"
        shutil.rmtree(staging_dir, ignore_errors=True)
        staging_dir.parent.mkdir(parents=True, exist_ok=True)
        self._run_renderer(plan_path=plan_path, out_dir=staging_dir, public_base=public_base)
        staging_manifest = staging_dir / "manifest.json"
        if not self._manifest_valid(staging_manifest, artifact_id, plan_id):
            shutil.rmtree(staging_dir, ignore_errors=True)
            raise ValueError("Rendered ritual artifact manifest failed validation.")

        if final_manifest.exists() and self._manifest_valid(final_manifest, artifact_id, plan_id):
            shutil.rmtree(staging_dir, ignore_errors=True)
        else:
            if final_dir.exists():
                backup = final_dir.with_name(f"{final_dir.name}.bak-{request_short}")
                shutil.rmtree(backup, ignore_errors=True)
                final_dir.replace(backup)
            staging_dir.replace(final_dir)

        return self._success(
            artifact_id=artifact_id,
            url=url,
            route=route,
            public_base=public_base,
            plan_path=plan_path,
            manifest_path=final_manifest,
            opened=self._open_if_requested(url, open_local),
        )

    def _persist_plan(
        self,
        *,
        response: BridgeResponseEnvelope,
        result: dict[str, object],
        plan: dict[str, object],
        plan_id: str,
    ) -> Path:
        self._config.plan_store_root.mkdir(parents=True, exist_ok=True)
        plan_path = self._config.plan_store_root / f"{plan_id}.json"
        payload = {
            "schemaVersion": "circulatio.presentation.handoff_plan.v1",
            "createdAt": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
            "source": "hermes_plugin_local_handoff",
            "requestId": response.get("requestId"),
            "idempotencyKey": response.get("idempotencyKey"),
            "plan": plan,
            "renderRequest": result.get("renderRequest"),
            "costEstimate": result.get("costEstimate"),
            "warnings": result.get("warnings", []),
        }
        tmp_path = plan_path.with_suffix(plan_path.suffix + ".tmp")
        tmp_path.write_text(
            json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        with tmp_path.open("r+b") as handle:
            handle.flush()
            os.fsync(handle.fileno())
        tmp_path.replace(plan_path)
        return plan_path

    def _run_renderer(self, *, plan_path: Path, out_dir: Path, public_base: str) -> None:
        if not self._config.renderer_script.exists():
            renderer_path = self._display_path(self._config.renderer_script)
            raise OSError(f"Renderer script not found: {renderer_path}")
        subprocess.run(
            [
                sys.executable,
                str(self._config.renderer_script),
                "--plan",
                str(plan_path),
                "--out",
                str(out_dir),
                "--mock-providers",
                "--dry-run",
                "--public-base",
                public_base,
            ],
            cwd=self._config.repo_root,
            check=True,
            capture_output=True,
            text=True,
            timeout=self._config.renderer_timeout_seconds,
        )

    def _manifest_valid(self, manifest_path: Path, artifact_id: str, plan_id: str) -> bool:
        if not manifest_path.exists():
            return False
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return False
        surfaces = manifest.get("surfaces") if isinstance(manifest, dict) else None
        captions = surfaces.get("captions") if isinstance(surfaces, dict) else None
        caption_segments = captions.get("segments") if isinstance(captions, dict) else None
        captions_file = manifest_path.with_name("captions.vtt")
        return (
            manifest.get("schemaVersion") == MANIFEST_SCHEMA_VERSION
            and manifest.get("artifactId") == artifact_id
            and manifest.get("planId") == plan_id
            and (bool(caption_segments) or captions_file.exists())
        )

    def _success(
        self,
        *,
        artifact_id: str,
        url: str,
        route: str,
        public_base: str,
        plan_path: Path,
        manifest_path: Path,
        opened: tuple[bool, list[str]],
    ) -> dict[str, object]:
        did_open, warnings = opened
        return {
            "status": "ok",
            "warnings": warnings,
            "artifactUrl": url,
            "artifact": {
                "artifactId": artifact_id,
                "url": url,
                "route": route,
                "publicBasePath": public_base,
                "planPath": self._display_path(plan_path),
                "manifestPath": self._display_path(manifest_path),
                "rendererVersion": RENDERER_VERSION,
                "mode": "dry_run_manifest",
                "providers": ["mock"],
                "opened": did_open,
            },
        }

    def _failure(self, *, retryable: bool, detail: str | None = None) -> dict[str, object]:
        artifact = {"status": "render_failed", "mode": "dry_run_manifest", "providers": ["mock"]}
        if detail:
            artifact["detail"] = detail
        return {
            "status": "render_failed",
            "retryable": retryable,
            "warnings": ["ritual_handoff_render_failed"],
            "artifact": artifact,
        }

    def _open_if_requested(self, url: str, open_local: bool) -> tuple[bool, list[str]]:
        if not open_local:
            return False, []
        if not (url.startswith("http://localhost") or url.startswith("http://127.0.0.1")):
            return False, ["ritual_handoff_open_skipped_non_local_url"]
        try:
            return bool(webbrowser.open(url, new=2)), []
        except Exception:
            return False, ["ritual_handoff_open_failed"]

    def _display_path(self, path: Path) -> str:
        return os.path.relpath(path, self._config.repo_root)
