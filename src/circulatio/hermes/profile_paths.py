from __future__ import annotations

import os
from pathlib import Path


def get_hermes_home() -> Path:
    """Resolve the active Hermes home with a safe local fallback.

    Prefer explicit environment overrides so tests and profile-specific runs can
    isolate Circulatio storage without patching Hermes internals.
    """

    raw_home = os.environ.get("HERMES_HOME")
    if raw_home:
        return Path(raw_home).expanduser()
    try:
        from hermes_constants import get_hermes_home as hermes_home_resolver

        return Path(hermes_home_resolver())
    except Exception:
        return Path.home() / ".hermes"


def ensure_hermes_home() -> Path:
    home = get_hermes_home()
    home.mkdir(parents=True, exist_ok=True)
    return home


def get_circulatio_db_path(
    filename: str = "circulatio.db", *, hermes_home: Path | None = None
) -> Path:
    home = hermes_home
    if home is None:
        home = ensure_hermes_home()
    else:
        home.mkdir(parents=True, exist_ok=True)
    return home / filename
