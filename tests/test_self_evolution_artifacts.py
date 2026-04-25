from __future__ import annotations

import os
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, os.path.abspath("src"))
sys.path.insert(0, os.path.abspath("."))

from tools.self_evolution.artifacts import (
    build_diff_patch,
    candidate_hashes,
    load_candidate_bundle_paths,
)
from tools.self_evolution.targets import get_target


class SelfEvolutionArtifactsTests(unittest.TestCase):
    def test_load_candidate_bundle_paths_resolves_candidates_dir(self) -> None:
        target = get_target("prompt_fragments")
        with tempfile.TemporaryDirectory() as tmp_dir:
            candidate_root = Path(tmp_dir) / "candidates"
            candidate_root.mkdir()
            candidate_file = candidate_root / "prompt_fragments.py"
            candidate_file.write_text(target.baseline_path.read_text())
            bundle = load_candidate_bundle_paths(Path(tmp_dir), target_names=["prompt_fragments"])
        self.assertIn("prompt_fragments", bundle.candidate_paths)
        self.assertEqual(bundle.relative_paths["prompt_fragments"], target.baseline_relative_path)
        self.assertEqual(bundle.extra_relative_paths, [])

    def test_build_diff_patch_and_hashes_track_candidate_artifact(self) -> None:
        target = get_target("prompt_fragments")
        with tempfile.TemporaryDirectory() as tmp_dir:
            candidate_path = Path(tmp_dir) / "prompt_fragments.py"
            candidate_path.write_text(target.baseline_path.read_text() + "\n# diff marker\n")
            diff_text = build_diff_patch(
                target_names=["prompt_fragments"],
                candidate_paths={"prompt_fragments": candidate_path},
            )
            base_hashes, staged_hashes = candidate_hashes(
                target_names=["prompt_fragments"],
                candidate_paths={"prompt_fragments": candidate_path},
            )
        self.assertIn(target.baseline_relative_path, diff_text)
        self.assertIn(f"candidate/{target.baseline_relative_path}", diff_text)
        self.assertIn(target.baseline_relative_path, base_hashes)
        self.assertIn(target.baseline_relative_path, staged_hashes)
        self.assertNotEqual(
            base_hashes[target.baseline_relative_path], staged_hashes[target.baseline_relative_path]
        )


if __name__ == "__main__":
    unittest.main()
