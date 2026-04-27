#!/usr/bin/env python3
from __future__ import annotations

import asyncio
import json
import os
import sys
from typing import Any

from circulatio_hermes_plugin.tools import record_ritual_completion_tool


def _read_payload() -> dict[str, object]:
    try:
        payload = json.load(sys.stdin)
    except json.JSONDecodeError as exc:
        raise SystemExit(f"Invalid JSON payload: {exc}") from exc
    if not isinstance(payload, dict):
        raise SystemExit("Completion payload must be a JSON object.")
    return payload


async def _main() -> None:
    payload = _read_payload()
    profile = os.environ.get("CIRCULATIO_PROFILE") or os.environ.get("HERMES_PROFILE") or "default"
    result = await record_ritual_completion_tool(
        payload,
        platform="hermes_rituals_web",
        source_platform="hermes_rituals_web",
        profile=profile,
    )
    parsed: Any = json.loads(result)
    sys.stdout.write(json.dumps(parsed, sort_keys=True, ensure_ascii=False))


if __name__ == "__main__":
    asyncio.run(_main())
