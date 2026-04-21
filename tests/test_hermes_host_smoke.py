from __future__ import annotations

import os
import subprocess
import sys
import unittest
from pathlib import Path


class HermesHostSmokeHarnessTests(unittest.TestCase):
    def test_external_hermes_host_smoke_harness_opt_in(self) -> None:
        if os.environ.get("CIRCULATIO_REAL_HERMES_HOST") != "1":
            self.skipTest(
                "Set CIRCULATIO_REAL_HERMES_HOST=1 to run the external Hermes-host smoke harness."
            )
        repo_root = Path(__file__).resolve().parents[1]
        result = subprocess.run(
            [
                sys.executable,
                str(repo_root / "scripts" / "hermes_host_smoke.py"),
                "--require-host",
            ],
            cwd=repo_root,
            capture_output=True,
            text=True,
            timeout=300,
        )
        output = f"{result.stdout}\n{result.stderr}"
        self.assertEqual(result.returncode, 0, output)
        self.assertIn("PASS: external Hermes host smoke succeeded.", output)


if __name__ == "__main__":
    unittest.main()
