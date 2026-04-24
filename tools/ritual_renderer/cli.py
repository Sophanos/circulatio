from __future__ import annotations

import argparse
import json
from pathlib import Path

from .contracts import RitualRenderOptions
from .renderer import render_plan_file


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Render a Circulatio ritual plan to a static manifest."
    )
    parser.add_argument("--plan", required=True, help="Path to PresentationRitualPlan JSON.")
    parser.add_argument(
        "--out",
        required=True,
        help="Output directory for manifest.json and assets.",
    )
    parser.add_argument(
        "--mock-providers",
        action="store_true",
        help="Use deterministic mock providers only.",
    )
    parser.add_argument("--dry-run", action="store_true", help="Do not call external providers.")
    parser.add_argument(
        "--surfaces",
        default="",
        help="Optional comma-separated surface allowlist for later provider profiles.",
    )
    parser.add_argument(
        "--public-base",
        default="",
        help="Public URL base for generated artifact assets.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    surfaces = [item.strip() for item in args.surfaces.split(",") if item.strip()]
    options: RitualRenderOptions = {
        "mockProviders": bool(args.mock_providers),
        "dryRun": bool(args.dry_run),
    }
    if surfaces:
        options["surfaces"] = surfaces
    if args.public_base:
        options["publicBasePath"] = args.public_base
    manifest = render_plan_file(plan_path=args.plan, out_dir=args.out, options=options)
    print(
        json.dumps(
            {
                "artifactId": manifest["artifactId"],
                "manifest": str(Path(args.out) / "manifest.json"),
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
