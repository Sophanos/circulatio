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
    parser.add_argument(
        "--provider-profile",
        default="mock",
        choices=[
            "mock",
            "chutes_speech",
            "chutes_audio",
            "chutes_image",
            "chutes_music",
            "chutes_video",
            "chutes_all",
        ],
        help="Optional renderer provider profile.",
    )
    parser.add_argument(
        "--chutes-token-env",
        default="CHUTES_API_TOKEN",
        help="Environment variable containing the Chutes API token.",
    )
    parser.add_argument(
        "--transcribe-captions",
        action="store_true",
        help="Regenerate captions from rendered speech using the selected transcription provider.",
    )
    parser.add_argument(
        "--transcription-provider",
        default="fallback",
        choices=["fallback", "chutes", "openai"],
        help="Caption transcription provider. Fallback keeps voiceScript-derived captions.",
    )
    parser.add_argument(
        "--openai-api-key-env",
        default="OPENAI_API_KEY",
        help="Environment variable containing the OpenAI API key for transcription.",
    )
    parser.add_argument(
        "--openai-transcription-model",
        default="whisper-1",
        help="OpenAI transcription model. Defaults to whisper-1 for timed caption output.",
    )
    parser.add_argument(
        "--openai-transcription-response-format",
        default="verbose_json",
        help="OpenAI transcription response format. Defaults to verbose_json for segments.",
    )
    parser.add_argument(
        "--request-timeout-seconds",
        type=int,
        default=180,
        help="Timeout for provider requests.",
    )
    parser.add_argument(
        "--max-cost-usd",
        type=float,
        default=0,
        help="Required positive budget guard for external providers.",
    )
    parser.add_argument(
        "--video-image",
        default="",
        help="Path, data URL, or base64 image payload for Chutes image-to-video.",
    )
    parser.add_argument(
        "--music-steps",
        type=int,
        default=32,
        help="Chutes Diffrhythm generation steps.",
    )
    parser.add_argument(
        "--music-duration-seconds",
        type=int,
        default=0,
        help="Chutes DiffRhythm music duration in seconds. Uses the plan value when omitted.",
    )
    parser.add_argument(
        "--allow-beta-music",
        action="store_true",
        help="Allow beta/developer music provider calls when all other gates pass.",
    )
    parser.add_argument(
        "--allow-beta-video",
        action="store_true",
        help="Allow beta/developer video provider calls when all other gates pass.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    surfaces = [item.strip() for item in args.surfaces.split(",") if item.strip()]
    transcription_provider = args.transcription_provider
    if transcription_provider == "fallback" and args.transcribe_captions:
        transcription_provider = "chutes"
    options: RitualRenderOptions = {
        "mockProviders": bool(args.mock_providers),
        "dryRun": bool(args.dry_run),
        "providerProfile": args.provider_profile,
        "chutesTokenEnv": args.chutes_token_env,
        "openaiApiKeyEnv": args.openai_api_key_env,
        "transcribeCaptions": bool(args.transcribe_captions),
        "transcriptionProvider": transcription_provider,
        "openaiTranscriptionModel": args.openai_transcription_model,
        "openaiTranscriptionResponseFormat": args.openai_transcription_response_format,
        "requestTimeoutSeconds": int(args.request_timeout_seconds),
        "maxCostUsd": float(args.max_cost_usd),
        "videoImage": args.video_image,
        "musicSteps": int(args.music_steps),
        "musicDurationSeconds": int(args.music_duration_seconds),
        "allowBetaMusic": bool(args.allow_beta_music),
        "allowBetaVideo": bool(args.allow_beta_video),
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
