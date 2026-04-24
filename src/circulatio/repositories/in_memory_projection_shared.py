from __future__ import annotations

from datetime import UTC, datetime

from ..domain.ids import now_iso
from ..domain.memory import MemoryImportance
from ..domain.practices import PracticeSessionRecord


def _material_summary_text(record: dict[str, object]) -> str:
    if record.get("summary"):
        return _truncate(str(record["summary"]), 180)
    if record.get("title"):
        return _truncate(str(record["title"]), 180)
    tags = [str(item).strip() for item in record.get("tags", []) if str(item).strip()]
    if tags:
        return _truncate("Tags: " + ", ".join(tags[:6]), 180)
    material_type = str(record.get("materialType", "material"))
    if material_type == "charged_event":
        return "Charged event recorded."
    return f"{material_type.replace('_', ' ')} recorded."


def _importance(
    *,
    score: float,
    reasons: list[str],
    recurrence_count: int | None = None,
    user_confirmed: bool | None = None,
    last_seen: str | None = None,
) -> MemoryImportance:
    result: MemoryImportance = {"score": max(0.0, min(1.0, score)), "reasons": reasons}
    if recurrence_count is not None:
        result["recurrenceCount"] = recurrence_count
    if user_confirmed is not None:
        result["userConfirmed"] = user_confirmed
    if last_seen is not None:
        result["lastSeen"] = last_seen
    return result


def _parse_datetime(value: str | None) -> datetime:
    if not value:
        return datetime.fromtimestamp(0, tz=UTC)
    candidate = value.strip()
    if candidate.endswith("Z"):
        candidate = candidate[:-1] + "+00:00"
    parsed = datetime.fromisoformat(candidate)
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def _is_within_window(value: datetime, start: datetime, end: datetime) -> bool:
    return start <= value <= end


def _is_within_optional_window(value: datetime, start: str | None, end: str | None) -> bool:
    if start and value < _parse_datetime(start):
        return False
    if end and value > _parse_datetime(end):
        return False
    return True


def _material_timestamp(record: dict[str, object]) -> datetime:
    return _parse_datetime(
        str(
            record.get("materialDate")
            or record.get("updatedAt")
            or record.get("createdAt")
            or now_iso()
        )
    )


def _practice_timestamp(record: PracticeSessionRecord) -> datetime:
    return _parse_datetime(
        record.get("completedAt") or record.get("updatedAt") or record.get("createdAt") or now_iso()
    )


def _expand_symbolic_keywords(values: list[object]) -> list[str]:
    """Flatten input values into lowercase tokens. No deterministic synonym expansion."""
    keywords: list[str] = []
    for value in values:
        for token in _tokenize(value):
            if token not in keywords:
                keywords.append(token)
    return keywords


def _tokenize(value: object) -> list[str]:
    text = str(value or "").strip().lower()
    if not text:
        return []
    return [
        token
        for token in text.replace("/", " ").replace("_", " ").replace(",", " ").split()
        if token
    ]


def _first_or_none(values: list[object]) -> str | None:
    if not values:
        return None
    first = values[0]
    return str(first) if first is not None else None


def _truncate(value: object, limit: int) -> str:
    text = str(value or "").strip()
    if len(text) <= limit:
        return text
    return text[: limit - 3].rstrip() + "..."
