from __future__ import annotations

import asyncio
import json
from copy import deepcopy
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Literal, Protocol, TypedDict

from ..domain.errors import ProfileStorageCorruptionError
from ..hermes.profile_paths import get_circulatio_db_path
from ..repositories.sqlite_utils import (
    create_sqlite_connection,
    sqlite_transaction,
    table_has_column,
)
from .agent_bridge_contracts import BridgeResponseEnvelope


@dataclass
class StoredBridgeResponse:
    request_hash: str
    status: Literal["started", "completed", "failed"]
    response: BridgeResponseEnvelope | None = None
    created_at: str | None = None
    updated_at: str | None = None


class IdempotencyBeginResult(TypedDict, total=False):
    status: Literal["started", "replay", "conflict", "in_flight", "stale_started"]
    stored: StoredBridgeResponse


class IdempotencyStore(Protocol):
    async def get(self, key: str) -> StoredBridgeResponse | None: ...

    async def begin(self, key: str, request_hash: str) -> IdempotencyBeginResult: ...

    async def complete(self, key: str, response: BridgeResponseEnvelope) -> None: ...

    async def fail(self, key: str, error: BridgeResponseEnvelope) -> None: ...

    def close(self) -> None: ...


class InMemoryIdempotencyStore:
    def __init__(self, *, started_ttl_seconds: int = 900) -> None:
        self._items: dict[str, StoredBridgeResponse] = {}
        self._lock = asyncio.Lock()
        self._started_ttl = started_ttl_seconds

    async def get(self, key: str) -> StoredBridgeResponse | None:
        async with self._lock:
            stored = self._items.get(key)
            return deepcopy(stored) if stored is not None else None

    async def begin(self, key: str, request_hash: str) -> IdempotencyBeginResult:
        async with self._lock:
            stored = self._items.get(key)
            now = _now_iso()
            if stored is None:
                self._items[key] = StoredBridgeResponse(
                    request_hash=request_hash,
                    status="started",
                    created_at=now,
                    updated_at=now,
                )
                return {"status": "started"}
            if stored.request_hash != request_hash:
                return {"status": "conflict", "stored": deepcopy(stored)}
            if stored.status == "started":
                if _is_stale(stored.updated_at, ttl_seconds=self._started_ttl):
                    return {"status": "stale_started", "stored": deepcopy(stored)}
                return {"status": "in_flight", "stored": deepcopy(stored)}
            return {"status": "replay", "stored": deepcopy(stored)}

    async def complete(self, key: str, response: BridgeResponseEnvelope) -> None:
        async with self._lock:
            stored = self._items.get(key)
            if stored is None:
                raise KeyError(f"Unknown idempotency key: {key}")
            stored.status = "completed"
            stored.response = deepcopy(response)
            stored.updated_at = _now_iso()

    async def fail(self, key: str, error: BridgeResponseEnvelope) -> None:
        async with self._lock:
            stored = self._items.get(key)
            if stored is None:
                raise KeyError(f"Unknown idempotency key: {key}")
            stored.status = "failed"
            stored.response = deepcopy(error)
            stored.updated_at = _now_iso()

    def close(self) -> None:
        return None


class SQLiteIdempotencyStore:
    def __init__(
        self,
        db_path: str | Path | None = None,
        *,
        started_ttl_seconds: int = 900,
    ) -> None:
        self._db_path = Path(db_path) if db_path is not None else get_circulatio_db_path()
        self._connection = create_sqlite_connection(self._db_path)
        self._lock = asyncio.Lock()
        self._started_ttl = started_ttl_seconds
        self._initialize_schema()

    @property
    def db_path(self) -> Path:
        return self._db_path

    def close(self) -> None:
        connection = getattr(self, "_connection", None)
        if connection is None:
            return
        try:
            connection.close()
        finally:
            self._connection = None

    async def get(self, key: str) -> StoredBridgeResponse | None:
        async with self._lock:
            row = self._connection.execute(
                """
                SELECT request_hash, status, response_json, created_at, updated_at
                FROM circulatio_idempotency
                WHERE idempotency_key = ?
                """,
                (key,),
            ).fetchone()
            return self._stored_from_row(row)

    async def begin(self, key: str, request_hash: str) -> IdempotencyBeginResult:
        async with self._lock:
            with sqlite_transaction(
                self._connection,
                db_path=self._db_path,
                action=f"begin idempotent request {key}",
                immediate=True,
            ):
                row = self._connection.execute(
                    """
                    SELECT request_hash, status, response_json, created_at, updated_at
                    FROM circulatio_idempotency
                    WHERE idempotency_key = ?
                    """,
                    (key,),
                ).fetchone()
                stored = self._stored_from_row(row)
                if stored is None:
                    self._connection.execute(
                        """
                        INSERT INTO circulatio_idempotency(
                            idempotency_key,
                            request_hash,
                            status,
                            created_at,
                            updated_at
                        )
                        VALUES (?, ?, 'started', datetime('now'), datetime('now'))
                        """,
                        (key, request_hash),
                    )
                    return {"status": "started"}
                if stored.request_hash != request_hash:
                    return {"status": "conflict", "stored": stored}
                if stored.status == "started":
                    if _is_stale(stored.updated_at, ttl_seconds=self._started_ttl):
                        return {"status": "stale_started", "stored": stored}
                    return {"status": "in_flight", "stored": stored}
                return {"status": "replay", "stored": stored}

    async def complete(self, key: str, response: BridgeResponseEnvelope) -> None:
        await self._store_response(key, status="completed", response=response)

    async def fail(self, key: str, error: BridgeResponseEnvelope) -> None:
        await self._store_response(key, status="failed", response=error)

    def _initialize_schema(self) -> None:
        with sqlite_transaction(
            self._connection,
            db_path=self._db_path,
            action="initialize idempotency storage",
            immediate=True,
        ):
            self._connection.execute(
                """
                CREATE TABLE IF NOT EXISTS circulatio_idempotency (
                    idempotency_key TEXT PRIMARY KEY,
                    request_hash TEXT NOT NULL,
                    status TEXT NOT NULL,
                    response_json TEXT,
                    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
                )
                """
            )
            if not table_has_column(self._connection, "circulatio_idempotency", "created_at"):
                self._connection.execute(
                    "ALTER TABLE circulatio_idempotency ADD COLUMN created_at TEXT"
                )
                self._connection.execute(
                    """
                    UPDATE circulatio_idempotency
                    SET created_at = COALESCE(created_at, updated_at, datetime('now'))
                    WHERE created_at IS NULL OR TRIM(created_at) = ''
                    """
                )

    async def _store_response(
        self,
        key: str,
        *,
        status: Literal["completed", "failed"],
        response: BridgeResponseEnvelope,
    ) -> None:
        payload = json.dumps(response, sort_keys=True, separators=(",", ":"), default=str)
        async with self._lock:
            with sqlite_transaction(
                self._connection,
                db_path=self._db_path,
                action=f"store idempotent response {key}",
                immediate=True,
            ):
                cursor = self._connection.execute(
                    """
                    UPDATE circulatio_idempotency
                    SET status = ?, response_json = ?, updated_at = datetime('now')
                    WHERE idempotency_key = ?
                    """,
                    (status, payload, key),
                )
                if cursor.rowcount == 0:
                    raise KeyError(f"Unknown idempotency key: {key}")

    def _stored_from_row(self, row) -> StoredBridgeResponse | None:
        if row is None:
            return None
        response: BridgeResponseEnvelope | None = None
        if row["response_json"]:
            try:
                parsed = json.loads(row["response_json"])
            except json.JSONDecodeError as exc:
                raise ProfileStorageCorruptionError(
                    "Circulatio idempotency storage contains an unreadable cached response."
                ) from exc
            response = deepcopy(parsed)
        return StoredBridgeResponse(
            request_hash=str(row["request_hash"]),
            status=str(row["status"]),
            response=response,
            created_at=str(row["created_at"]) if row["created_at"] is not None else None,
            updated_at=str(row["updated_at"]) if row["updated_at"] is not None else None,
        )


def _now_iso() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def _is_stale(timestamp: str | None, *, ttl_seconds: int) -> bool:
    if not timestamp:
        return False
    parsed = _parse_timestamp(timestamp)
    if parsed is None:
        return False
    return datetime.now(UTC) - parsed > timedelta(seconds=ttl_seconds)


def _parse_timestamp(value: str) -> datetime | None:
    normalized = value.strip()
    if not normalized:
        return None
    if normalized.endswith("Z"):
        normalized = normalized[:-1] + "+00:00"
    elif len(normalized) == 19 and "T" not in normalized:
        normalized = normalized.replace(" ", "T") + "+00:00"
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)
