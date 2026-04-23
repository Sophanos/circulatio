from __future__ import annotations

import os
import sys
import unittest
from datetime import UTC, datetime

sys.path.insert(0, os.path.abspath("src"))

from circulatio.domain.timestamps import (
    format_iso_datetime,
    parse_iso_datetime,
    try_parse_iso_datetime,
)


class TimestampHelpersTests(unittest.TestCase):
    def test_parse_iso_datetime_normalizes_zulu_time(self) -> None:
        parsed = parse_iso_datetime("2026-04-23T12:34:56Z")
        self.assertEqual(parsed, datetime(2026, 4, 23, 12, 34, 56, tzinfo=UTC))

    def test_parse_iso_datetime_accepts_space_separated_naive_timestamp(self) -> None:
        parsed = parse_iso_datetime("2026-04-23 12:34:56")
        self.assertEqual(parsed, datetime(2026, 4, 23, 12, 34, 56, tzinfo=UTC))

    def test_parse_iso_datetime_uses_default_for_missing_values(self) -> None:
        fallback = datetime(1970, 1, 1, tzinfo=UTC)
        self.assertEqual(parse_iso_datetime(None, default=fallback), fallback)

    def test_try_parse_iso_datetime_returns_none_for_invalid_value(self) -> None:
        self.assertIsNone(try_parse_iso_datetime("not-a-timestamp"))

    def test_format_iso_datetime_emits_z_suffix(self) -> None:
        formatted = format_iso_datetime(datetime(2026, 4, 23, 12, 34, 56, tzinfo=UTC))
        self.assertEqual(formatted, "2026-04-23T12:34:56Z")
