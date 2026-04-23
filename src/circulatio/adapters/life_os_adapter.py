from __future__ import annotations

import logging
import sqlite3
from datetime import UTC, datetime
from pathlib import Path
from typing import Protocol

from ..domain.normalization import compact_life_context_snapshot
from ..domain.timestamps import format_iso_datetime, parse_iso_datetime
from ..domain.types import Id, LifeContextSnapshot
from ..hermes.profile_paths import get_hermes_home
from ..llm.ports import CirculatioLlmPort

LOGGER = logging.getLogger(__name__)


class LifeOsReferenceAdapter(Protocol):
    async def get_life_context_snapshot(
        self,
        *,
        user_id: Id,
        window_start: str,
        window_end: str,
    ) -> LifeContextSnapshot: ...


class HermesProfileLifeOsReferenceAdapter:
    """Build compact life context from the active Hermes profile.

    This adapter reads Hermes's existing durable state rather than relying on
    demo fixtures. When an LLM port is available it uses that port to compress
    the collected state into Circulatio's bounded LifeContextSnapshot schema.
    """

    def __init__(
        self,
        *,
        llm: CirculatioLlmPort | None = None,
        hermes_home: Path | None = None,
        max_messages: int = 24,
        max_memory_entries: int = 12,
    ) -> None:
        self._llm = llm
        self._hermes_home = hermes_home or get_hermes_home()
        self._max_messages = max_messages
        self._max_memory_entries = max_memory_entries

    async def get_life_context_snapshot(
        self,
        *,
        user_id: Id,
        window_start: str,
        window_end: str,
    ) -> LifeContextSnapshot:
        try:
            raw_context = self._collect_raw_context(
                user_id=user_id,
                window_start=window_start,
                window_end=window_end,
            )
        except Exception:
            LOGGER.warning(
                (
                    "Circulatio could not collect Hermes life context; "
                    "using empty fallback snapshot."
                ),
                exc_info=True,
            )
            return self._fallback_snapshot(
                window_start=window_start,
                window_end=window_end,
                raw_context={},
            )
        if self._llm is not None:
            try:
                snapshot = await self._llm.summarize_life_context(
                    user_id=user_id,
                    window_start=window_start,
                    window_end=window_end,
                    raw_context=raw_context,
                )
                compact = compact_life_context_snapshot(snapshot)
                if compact is not None:
                    return compact
            except Exception:
                LOGGER.warning(
                    (
                        "Circulatio life-context LLM compression failed; "
                        "using deterministic fallback."
                    ),
                    exc_info=True,
                )
        return self._fallback_snapshot(
            window_start=window_start,
            window_end=window_end,
            raw_context=raw_context,
        )

    def _collect_raw_context(
        self,
        *,
        user_id: Id,
        window_start: str,
        window_end: str,
    ) -> dict[str, object]:
        messages = self._load_recent_messages(
            window_start=window_start,
            window_end=window_end,
        )
        return {
            "userId": user_id,
            "windowStart": window_start,
            "windowEnd": window_end,
            "userMessages": messages,
            "memoryEntries": self._read_memory_entries("MEMORY.md"),
            "userEntries": self._read_memory_entries("USER.md"),
            "soulEntries": self._read_plain_lines(self._hermes_home / "SOUL.md"),
        }

    def _load_recent_messages(
        self,
        *,
        window_start: str,
        window_end: str,
    ) -> list[dict[str, object]]:
        db_path = self._hermes_home / "state.db"
        if not db_path.exists():
            return []
        start_ts = self._iso_to_timestamp(window_start)
        end_ts = self._iso_to_timestamp(window_end)
        try:
            with sqlite3.connect(db_path) as connection:
                connection.row_factory = sqlite3.Row
                rows = connection.execute(
                    """
                    SELECT m.id, m.session_id, m.role, m.content, m.timestamp, s.source
                    FROM messages AS m
                    JOIN sessions AS s ON s.id = m.session_id
                    WHERE m.timestamp BETWEEN ? AND ?
                      AND m.content IS NOT NULL
                      AND TRIM(m.content) != ''
                      AND m.role IN ('user', 'assistant')
                    ORDER BY m.timestamp DESC
                    LIMIT ?
                    """,
                    (start_ts, end_ts, self._max_messages),
                ).fetchall()
        except sqlite3.Error:
            LOGGER.warning(
                "Circulatio could not read Hermes state.db for life context.",
                exc_info=True,
            )
            return []
        messages: list[dict[str, object]] = []
        for row in rows:
            try:
                messages.append(
                    {
                        "id": f"hermes_message_{row['id']}",
                        "sessionId": row["session_id"],
                        "source": row["source"],
                        "role": row["role"],
                        "content": row["content"],
                        "timestamp": self._timestamp_to_iso(float(row["timestamp"])),
                    }
                )
            except (TypeError, ValueError):
                LOGGER.warning(
                    "Circulatio skipped a Hermes message with an invalid timestamp.",
                    exc_info=True,
                )
        return messages

    def _read_memory_entries(self, filename: str) -> list[str]:
        memory_path = self._hermes_home / "memories" / filename
        if not memory_path.exists():
            return []
        try:
            text = memory_path.read_text(encoding="utf-8").strip()
        except (FileNotFoundError, PermissionError, UnicodeDecodeError, OSError):
            LOGGER.warning(
                "Circulatio could not read Hermes memory file %s.",
                filename,
                exc_info=True,
            )
            return []
        if not text:
            return []
        return [entry.strip() for entry in text.split("\n§\n") if entry.strip()][
            : self._max_memory_entries
        ]

    def _read_plain_lines(self, path: Path) -> list[str]:
        if not path.exists():
            return []
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except (FileNotFoundError, PermissionError, UnicodeDecodeError, OSError):
            LOGGER.warning(
                "Circulatio could not read Hermes profile file %s.",
                path.name,
                exc_info=True,
            )
            return []
        return [line.strip() for line in lines if line.strip()][: self._max_memory_entries]

    def _fallback_snapshot(
        self,
        *,
        window_start: str,
        window_end: str,
        raw_context: dict[str, object],
    ) -> LifeContextSnapshot:
        user_messages = [
            item
            for item in raw_context.get("userMessages", [])
            if isinstance(item, dict) and item.get("role") == "user"
        ]
        event_refs = [
            {
                "id": item["id"],
                "date": item["timestamp"],
                "summary": str(item["content"])[:180],
            }
            for item in user_messages[:3]
        ]
        snapshot: LifeContextSnapshot = {
            "windowStart": window_start,
            "windowEnd": window_end,
            "source": "hermes-life-os",
        }
        if event_refs:
            snapshot["lifeEventRefs"] = event_refs
            snapshot["focusSummary"] = (
                f"Derived from {len(user_messages)} recent Hermes user message(s)."
            )
        memory_entries = [
            *[str(item) for item in raw_context.get("userEntries", [])[:2]],
            *[str(item) for item in raw_context.get("memoryEntries", [])[:2]],
        ]
        if memory_entries:
            snapshot["notableChanges"] = memory_entries[:5]
        return compact_life_context_snapshot(snapshot) or snapshot

    def _iso_to_timestamp(self, value: str) -> float:
        return parse_iso_datetime(value).timestamp()

    def _timestamp_to_iso(self, value: float) -> str:
        return format_iso_datetime(datetime.fromtimestamp(value, tz=UTC))
