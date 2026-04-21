from __future__ import annotations

import importlib.metadata as metadata
import importlib.resources as resources
import os
import sys
import unittest

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
        self.assertEqual(report["checks"][0]["details"]["entryPoint"], "circulatio_hermes_plugin")

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


if __name__ == "__main__":
    unittest.main()
