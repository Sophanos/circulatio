from __future__ import annotations

from importlib import import_module
from typing import Any

__all__ = ["CirculatioService"]


def __getattr__(name: str) -> Any:
    if name != "CirculatioService":
        raise AttributeError(f"module 'circulatio.application' has no attribute {name!r}")
    value = getattr(import_module("circulatio.application.circulatio_service"), name)
    globals()[name] = value
    return value
