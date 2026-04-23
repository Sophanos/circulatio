from __future__ import annotations

from datetime import UTC, datetime


def format_iso_datetime(value: datetime) -> str:
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")


def try_parse_iso_datetime(
    value: object,
    *,
    allow_space_separator: bool = True,
) -> datetime | None:
    text = str(value or "").strip()
    if not text:
        return None
    normalized = text
    if normalized.endswith("Z"):
        normalized = normalized[:-1] + "+00:00"
    elif allow_space_separator and len(normalized) == 19 and "T" not in normalized:
        normalized = normalized.replace(" ", "T") + "+00:00"
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def parse_iso_datetime(
    value: object | None,
    *,
    default: datetime | None = None,
    allow_space_separator: bool = True,
) -> datetime:
    parsed = try_parse_iso_datetime(
        value,
        allow_space_separator=allow_space_separator,
    )
    if parsed is not None:
        return parsed
    if default is not None:
        return default
    raise ValueError(f"Invalid ISO timestamp: {value!r}")
