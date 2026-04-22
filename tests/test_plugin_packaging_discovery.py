from __future__ import annotations

import importlib.metadata as metadata
import importlib.resources as resources
import os
import sys
import unittest
from pathlib import Path

sys.path.insert(0, os.path.abspath("src"))

from circulatio.hermes.boot_validation import validate_plugin_assets, validate_plugin_distribution
from circulatio_hermes_plugin.schemas import TOOL_SCHEMAS


class PluginPackagingDiscoveryTests(unittest.TestCase):
    def test_packaged_assets_are_available_via_importlib_resources(self) -> None:
        plugin_yaml = resources.files("circulatio_hermes_plugin").joinpath("plugin.yaml")
        skill_file = resources.files("circulatio_hermes_plugin").joinpath(
            "skills",
            "circulation",
            "SKILL.md",
        )
        self.assertTrue(plugin_yaml.is_file())
        self.assertTrue(skill_file.is_file())
        report = validate_plugin_assets()
        self.assertEqual(report["status"], "ok")

    def test_distribution_entry_point_is_valid_when_metadata_is_available(self) -> None:
        try:
            metadata.distribution("circulatio")
        except metadata.PackageNotFoundError:
            report = validate_plugin_distribution(strict_installed=False)
            self.assertEqual(report["status"], "warning")
            self.assertEqual(report["checks"][0]["status"], "warning")
            return

        report = validate_plugin_distribution(strict_installed=True)
        self.assertEqual(report["status"], "ok")
        self.assertEqual(
            report["checks"][0]["details"]["entryPoint"],
            "circulatio_hermes_plugin",
        )
        self.assertIsNone(report["checks"][0]["details"]["entryPointAttr"])
        self.assertTrue(report["checks"][0]["details"]["hasRegister"])

    def test_plugin_manifest_tool_list_matches_registered_schemas(self) -> None:
        plugin_yaml = (
            resources.files("circulatio_hermes_plugin").joinpath("plugin.yaml").read_text()
        )
        lines = plugin_yaml.splitlines()
        tools: list[str] = []
        commands: list[str] = []
        current_section: str | None = None
        for line in lines:
            if line.startswith("provides_tools:"):
                current_section = "tools"
                continue
            if line.startswith("provides_commands:"):
                current_section = "commands"
                continue
            if not line.startswith("  - "):
                if line and not line.startswith(" "):
                    current_section = None
                continue
            item = line[4:].strip()
            if current_section == "tools":
                tools.append(item)
            elif current_section == "commands":
                commands.append(item)

        self.assertEqual({schema["name"] for schema in TOOL_SCHEMAS}, set(tools))
        self.assertEqual(commands, ["circulation"])

    def test_wrapper_plugin_manifest_matches_packaged_plugin_manifest(self) -> None:
        repo_root = Path(__file__).resolve().parents[1]
        packaged_manifest = (
            resources.files("circulatio_hermes_plugin").joinpath("plugin.yaml").read_text()
        )
        wrapper_manifest = (repo_root / "hermes_plugin" / "circulatio" / "plugin.yaml").read_text()
        self.assertEqual(packaged_manifest, wrapper_manifest)

    def test_shadow_build_files_match_src_when_present(self) -> None:
        repo_root = Path(__file__).resolve().parents[1]
        shadow_paths = [
            Path("circulatio/core/circulatio_core.py"),
            Path("circulatio/core/practice_engine.py"),
            Path("circulatio/core/interpretation_mapping.py"),
            Path("circulatio/llm/hermes_model_adapter.py"),
            Path("circulatio/llm/prompt_builder.py"),
            Path("circulatio/llm/prompt_fragments.py"),
            Path("circulatio_hermes_plugin/skills/circulation/SKILL.md"),
        ]
        for relative_path in shadow_paths:
            src_path = repo_root / "src" / relative_path
            build_path = repo_root / "build" / "lib" / relative_path
            if not build_path.is_file():
                continue
            self.assertEqual(
                src_path.read_text(),
                build_path.read_text(),
                f"Stale build artifact drifted from src: {build_path}",
            )


if __name__ == "__main__":
    unittest.main()
