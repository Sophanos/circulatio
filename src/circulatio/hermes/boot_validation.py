from __future__ import annotations

import importlib
from importlib import metadata, resources
from pathlib import Path
from typing import Literal, NotRequired, TypedDict

from .runtime import CirculatioRuntime

BootCheckStatus = Literal["ok", "warning", "error"]

_EXPECTED_ENTRY_POINT = "circulatio_hermes_plugin"
_EXPECTED_ENTRY_POINT_MODULE = "circulatio_hermes_plugin"
_ASSET_PATHS = {
    "plugin.yaml": ("circulatio_hermes_plugin", "plugin.yaml"),
    "skills/circulation/SKILL.md": (
        "circulatio_hermes_plugin",
        "skills",
        "circulation",
        "SKILL.md",
    ),
}


class PluginBootError(RuntimeError):
    """Raised when packaged plugin assets required for Hermes boot are missing."""


class BootCheck(TypedDict, total=False):
    name: str
    status: BootCheckStatus
    message: str
    details: NotRequired[dict[str, object]]


class BootValidationReport(TypedDict):
    status: BootCheckStatus
    profile: str
    checks: list[BootCheck]


def validate_plugin_distribution(*, strict_installed: bool) -> BootValidationReport:
    checks: list[BootCheck] = []
    try:
        distribution = metadata.distribution("circulatio")
    except metadata.PackageNotFoundError:
        status: BootCheckStatus = "error" if strict_installed else "warning"
        checks.append(
            {
                "name": "distribution",
                "status": status,
                "message": "Installed distribution metadata for circulatio is unavailable.",
            }
        )
        return _report(profile="installed-distribution", checks=checks)

    matching = [
        entry_point
        for entry_point in distribution.entry_points
        if entry_point.group == "hermes_agent.plugins" and entry_point.name == "circulatio"
    ]
    if not matching:
        checks.append(
            {
                "name": "entry-point",
                "status": "error",
                "message": "No circulatio entry point was found in hermes_agent.plugins.",
            }
        )
        return _report(profile="installed-distribution", checks=checks)

    entry_point = matching[0]
    try:
        loaded_target = entry_point.load()
        plugin_module = importlib.import_module("circulatio_hermes_plugin")
    except Exception as exc:
        checks.append(
            {
                "name": "entry-point-load",
                "status": "error",
                "message": "The installed circulatio entry point could not be loaded.",
                "details": {"exception": f"{type(exc).__name__}: {exc}"},
            }
        )
        return _report(profile="installed-distribution", checks=checks)

    status: BootCheckStatus = "ok"
    message = "The installed circulatio entry point resolves to the circulatio_hermes_plugin module."
    if (
        entry_point.value != _EXPECTED_ENTRY_POINT
        or entry_point.module != _EXPECTED_ENTRY_POINT_MODULE
        or entry_point.attr is not None
        or loaded_target is not plugin_module
        or not hasattr(plugin_module, "register")
    ):
        status = "error"
        message = (
            "The installed circulatio entry point does not resolve to "
            "the circulatio_hermes_plugin module."
        )
    checks.append(
        {
            "name": "entry-point",
            "status": status,
            "message": message,
            "details": {
                "distribution": distribution.metadata.get("Name", "circulatio"),
                "entryPoint": entry_point.value,
                "entryPointModule": entry_point.module,
                "entryPointAttr": entry_point.attr,
                "hasRegister": hasattr(plugin_module, "register"),
            },
        }
    )
    return _report(profile="installed-distribution", checks=checks)


def validate_plugin_assets() -> BootValidationReport:
    plugin_dir = Path(importlib.import_module("circulatio_hermes_plugin").__file__).resolve().parent
    checks: list[BootCheck] = []
    for label, path_parts in _ASSET_PATHS.items():
        package = path_parts[0]
        resource = resources.files(package)
        for segment in path_parts[1:]:
            resource = resource.joinpath(segment)
        package_ok = resource.is_file()
        concrete_ok = (plugin_dir / Path(*path_parts[1:])).is_file()
        status: BootCheckStatus = "ok" if package_ok and concrete_ok else "error"
        message = f"Validated packaged asset {label}."
        if status != "ok":
            message = f"Required packaged asset {label} is missing."
        checks.append(
            {
                "name": f"asset:{label}",
                "status": status,
                "message": message,
                "details": {
                    "packageResource": package_ok,
                    "filesystemPath": str(plugin_dir / Path(*path_parts[1:])),
                    "filesystemPresent": concrete_ok,
                },
            }
        )
    return _report(profile="plugin-assets", checks=checks)


def validate_runtime_storage(runtime: CirculatioRuntime) -> BootValidationReport:
    checks: list[BootCheck] = []
    repository = runtime.repository
    idempotency_store = runtime.idempotency_store
    repo_db_path = getattr(repository, "db_path", None)
    if repo_db_path is not None:
        repo_health = getattr(repository, "storage_health", lambda: {})()
        checks.append(
            {
                "name": "repository-storage",
                "status": "ok",
                "message": "Repository storage is available.",
                "details": {
                    "dbPath": str(repo_db_path),
                    "health": repo_health,
                    "parentWritable": Path(repo_db_path).parent.exists()
                    and Path(repo_db_path).parent.is_dir(),
                },
            }
        )
    idem_db_path = getattr(idempotency_store, "db_path", None)
    if idem_db_path is not None:
        checks.append(
            {
                "name": "idempotency-storage",
                "status": "ok",
                "message": "Idempotency storage is available.",
                "details": {"dbPath": str(idem_db_path)},
            }
        )
    return _report(profile="runtime-storage", checks=checks)


def raise_for_invalid_plugin_assets() -> None:
    report = validate_plugin_assets()
    failing = next((check for check in report["checks"] if check["status"] == "error"), None)
    if failing is None:
        return
    raise PluginBootError(failing["message"])


def _report(*, profile: str, checks: list[BootCheck]) -> BootValidationReport:
    status: BootCheckStatus = "ok"
    if any(check["status"] == "error" for check in checks):
        status = "error"
    elif any(check["status"] == "warning" for check in checks):
        status = "warning"
    return {"status": status, "profile": profile, "checks": checks}
