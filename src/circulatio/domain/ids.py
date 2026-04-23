from __future__ import annotations

import random
import string
import time
import unicodedata
from datetime import UTC, datetime

from .timestamps import format_iso_datetime


def create_id(prefix: str) -> str:
    random_part = "".join(random.choices(string.ascii_lowercase + string.digits, k=8))
    time_part = format(int(time.time() * 1000), "x")
    return f"{prefix}_{time_part}_{random_part}"


def now_iso() -> str:
    return format_iso_datetime(datetime.now(UTC))


def normalize_claim_key(hypothesis_type: str, claim: str) -> str:
    raw = unicodedata.normalize("NFKD", f"{hypothesis_type}:{claim}")
    filtered: list[str] = []
    previous_was_space = False
    for char in raw.lower():
        if char.isalnum() or char in {":", "_", "-"}:
            filtered.append(char)
            previous_was_space = False
            continue
        if not previous_was_space:
            filtered.append(" ")
            previous_was_space = True
    return " ".join("".join(filtered).split())
