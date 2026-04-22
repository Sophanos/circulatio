from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path


@dataclass(frozen=True)
class AdapterConfig:
    name: str
    binary: str
    enabled_by_default: bool
    prompt_transport: str
    command: list[str]
    output_mode: str
    timeout_seconds: int
    version_command: list[str]
    max_arg_bytes: int = 16_384
    allow_prompt_file_fallback: bool = False
    mode: str = "success"
    extra: dict[str, object] = field(default_factory=dict)

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


def _load_yaml_like(path: Path) -> dict[str, object]:
    if not path.exists():
        return {}
    text = path.read_text().strip()
    if not text:
        return {}
    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        try:
            import yaml  # type: ignore
        except ImportError as exc:  # pragma: no cover - optional dependency path
            raise ValueError(
                f"{path} must be JSON-compatible YAML unless PyYAML is installed."
            ) from exc
        payload = yaml.safe_load(text)
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must decode to an object.")
    return {str(key): value for key, value in payload.items()}


def _deep_merge(base: dict[str, object], override: dict[str, object]) -> dict[str, object]:
    merged = dict(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = _deep_merge(
                {str(inner_key): inner_value for inner_key, inner_value in merged[key].items()},
                {str(inner_key): inner_value for inner_key, inner_value in value.items()},
            )
        else:
            merged[key] = value
    return merged


def _normalize_adapter(name: str, payload: dict[str, object]) -> AdapterConfig:
    return AdapterConfig(
        name=name,
        binary=str(payload.get("binary") or ""),
        enabled_by_default=bool(payload.get("enabledByDefault")),
        prompt_transport=str(payload.get("promptTransport") or "stdin"),
        command=[str(item) for item in list(payload.get("command") or [])],
        output_mode=str(payload.get("outputMode") or "text"),
        timeout_seconds=int(payload.get("timeoutSeconds") or 240),
        version_command=[str(item) for item in list(payload.get("versionCommand") or [])],
        max_arg_bytes=int(payload.get("maxArgBytes") or 16_384),
        allow_prompt_file_fallback=bool(payload.get("allowPromptFileFallback")),
        mode=str(payload.get("mode") or "success"),
        extra={
            str(key): value
            for key, value in payload.items()
            if key
            not in {
                "binary",
                "enabledByDefault",
                "promptTransport",
                "command",
                "outputMode",
                "timeoutSeconds",
                "versionCommand",
                "maxArgBytes",
                "allowPromptFileFallback",
                "mode",
            }
        },
    )


def load_adapter_configs(override_path: Path | None = None) -> dict[str, AdapterConfig]:
    default_path = Path(__file__).with_name("adapters.default.yaml")
    local_path = override_path or Path(__file__).with_name("adapters.local.yaml")
    default_payload = _load_yaml_like(default_path)
    local_payload = _load_yaml_like(local_path) if local_path.exists() else {}
    merged_payload = _deep_merge(default_payload, local_payload)
    adapters = merged_payload.get("adapters")
    if not isinstance(adapters, dict):
        raise ValueError("Adapter config must contain an 'adapters' mapping.")
    return {
        str(name): _normalize_adapter(
            str(name), {str(key): value for key, value in payload.items()}
        )
        for name, payload in adapters.items()
        if isinstance(payload, dict)
    }


def redact_adapter_config(config: AdapterConfig) -> dict[str, object]:
    redacted = config.as_dict()
    if redacted.get("command"):
        redacted["command"] = [str(item) for item in redacted["command"]]
    if redacted.get("version_command"):
        redacted["version_command"] = [str(item) for item in redacted["version_command"]]
    return redacted
