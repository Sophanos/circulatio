from __future__ import annotations

import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from ..domain.errors import PersistenceError, ProfileStorageCorruptionError


def create_sqlite_connection(db_path: str | Path) -> sqlite3.Connection:
    path = Path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        connection = sqlite3.connect(
            path,
            check_same_thread=False,
            timeout=30,
            isolation_level=None,
        )
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA journal_mode=WAL")
        connection.execute("PRAGMA busy_timeout=30000")
        connection.execute("PRAGMA foreign_keys=ON")
        return connection
    except (sqlite3.Error, OSError) as exc:
        raise storage_error_from_exception(exc, db_path=path, action="open SQLite storage") from exc


def table_exists(connection: sqlite3.Connection, table_name: str) -> bool:
    row = connection.execute(
        "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ?",
        (table_name,),
    ).fetchone()
    return row is not None


def table_has_column(connection: sqlite3.Connection, table_name: str, column_name: str) -> bool:
    try:
        rows = connection.execute(f"PRAGMA table_info({table_name})").fetchall()
    except sqlite3.Error:
        return False
    return any(str(row["name"]) == column_name for row in rows)


@contextmanager
def sqlite_transaction(
    connection: sqlite3.Connection,
    *,
    db_path: str | Path,
    action: str,
    immediate: bool = False,
) -> Iterator[None]:
    begin_sql = "BEGIN IMMEDIATE" if immediate else "BEGIN"
    try:
        connection.execute(begin_sql)
        yield
    except Exception as exc:
        try:
            connection.execute("ROLLBACK")
        except sqlite3.Error:
            pass
        if isinstance(exc, PersistenceError):
            raise
        if isinstance(exc, (sqlite3.Error, OSError)):
            raise storage_error_from_exception(exc, db_path=db_path, action=action) from exc
        raise
    else:
        try:
            connection.execute("COMMIT")
        except (sqlite3.Error, OSError) as exc:
            try:
                connection.execute("ROLLBACK")
            except sqlite3.Error:
                pass
            raise storage_error_from_exception(exc, db_path=db_path, action=action) from exc


def storage_error_from_exception(
    exc: Exception,
    *,
    db_path: str | Path,
    action: str,
) -> PersistenceError:
    path = Path(db_path)
    message = str(exc).strip() or type(exc).__name__
    lowered = message.lower()
    if any(
        token in lowered
        for token in (
            "malformed",
            "not a database",
            "database disk image is malformed",
        )
    ):
        return ProfileStorageCorruptionError(f"Failed to {action} at {path}: storage is corrupt.")
    retryable = any(
        token in lowered
        for token in (
            "database is locked",
            "database table is locked",
            "database schema is locked",
            "busy",
            "temporarily unavailable",
            "unable to open database file",
        )
    )
    if isinstance(exc, PermissionError):
        retryable = False
    return PersistenceError(
        f"Failed to {action} at {path}: {message}",
        retryable=retryable,
    )
