# Journey CLI

Journey CLI is a local evaluator, not a proactive runtime.

It has two modes:

- comparative CLI evals for host/tool-routing behavior over synthetic journey cases
- ritual journey evals for real-life ritual simulation, provider gates, artifact reports, and playback contract checks

Hermes-agent remains the real proactive runtime. Circulatio remains memory, planning, and completion. The renderer owns media generation. Hermes Rituals remains the playback vessel.

## Ritual Eval JTBD

When we change ritual, media, or completion code, Journey CLI should answer:

- Did Hermes-style behavior invite before planning?
- Did consent block scheduled proactive ritual invitations?
- Did skipped invitations avoid planning and rendering?
- Did accepted invitations call `circulatio_plan_ritual` only after acceptance?
- Did completion sync call only `circulatio_record_ritual_completion`, including no-note, body-state, reflection, and practice-feedback variants?
- Did companion and live-guidance flows avoid durable writes unless an explicit action is approved?
- Did Chutes/token/budget/video gates avoid unintended provider calls?
- Did each artifact expose the expected manifest, captions, breath, meditation, media, and completion fields?

## Ritual Coverage

Journey CLI is the local proof harness for the Hermes Rituals path. Current coverage includes:

- `user message + memory context -> circulatio_plan_ritual` tool-choice cases for selective surfaces.
- `ritual_invitation -> accept -> plan -> render -> artifact report` as an acceptance-gated path.
- Negative scheduled cases: skipped, dismissed, decline, expired, or no-consent invitations must not plan or render.
- Surface-selection cases: breath only, breath plus music, music without narration, full voice/music/image, image return, and cinema requested.
- Browser artifact checks for real playback: narration metadata, music channel, captions, breath pacer, image/photo lens, cinema when enabled, completion POST, companion rail, and no-camera live continuation.
- Provider distinction in reports: mock render, live provider smoke, and browser playback success are separate result categories.
- Chutes Whisper is not a required pass condition. Fallback captions are the baseline; official OpenAI transcription is optional provider-backed caption refinement.

## Run

Default ritual eval uses mock/dry-run accepted renders and still exercises negative Chutes/video gates:

```bash
.venv/bin/python scripts/evaluate_journey_cli.py --ritual-eval --strict
```

Optional HTTP checks assume Hermes Rituals is serving the same artifact root:

```bash
.venv/bin/python scripts/evaluate_journey_cli.py \
  --ritual-eval \
  --ritual-http-check \
  --ritual-base-url http://localhost:3000 \
  --strict
```

Provider-backed accepted renders stay explicit:

```bash
CHUTES_API_TOKEN=... \
.venv/bin/python scripts/evaluate_journey_cli.py \
  --ritual-eval \
  --ritual-live-providers \
  --ritual-provider-profile chutes_all \
  --ritual-max-cost-usd 2.0 \
  --strict
```

Provider-backed music is separately gated:

```bash
CHUTES_API_TOKEN=... \
.venv/bin/python scripts/evaluate_journey_cli.py \
  --ritual-eval \
  --ritual-live-providers \
  --ritual-provider-profile chutes_all \
  --ritual-include-music \
  --ritual-allow-beta-music \
  --ritual-max-cost-usd 2.0 \
  --strict
```

OpenAI transcription uses the official API key from the process environment or an ignored repo-local `.env`, and never accepts a literal key in eval data or render policy:

```bash
CHUTES_API_TOKEN=... OPENAI_API_KEY=... \
.venv/bin/python scripts/evaluate_journey_cli.py \
  --ritual-eval \
  --ritual-live-providers \
  --ritual-provider-profile chutes_all \
  --ritual-transcription-provider openai \
  --ritual-openai-api-key-env OPENAI_API_KEY \
  --ritual-openai-transcription-model whisper-1 \
  --ritual-max-cost-usd 2.0 \
  --strict
```

Video remains beta-gated. Only request it when the plan policy, provider profile, budget, token, `videoAllowed`, and `allowBetaVideo` all pass:

```bash
CHUTES_API_TOKEN=... \
.venv/bin/python scripts/evaluate_journey_cli.py \
  --ritual-eval \
  --ritual-live-providers \
  --ritual-provider-profile chutes_all \
  --ritual-include-video \
  --ritual-allow-beta-video \
  --ritual-max-cost-usd 2.0 \
  --strict
```

## Output

Each ritual eval writes:

```text
artifacts/journey_cli_eval/runs/{runId}/
  report.json
  report.md
  timeline.json
  tool_calls.json
  browser_checks.json
  artifacts_checked.json
  screenshots/
```

`tool_calls.json` redacts user-authored text fields. Provider tokens are never written. Reports include selected tool sequence, requested surfaces, render policy, artifact URL, manifest surfaces, and browser check result so `browser_checks.json` and `artifacts_checked.json` can be treated as pass/fail artifacts.

## Scorecard

The report groups checks into:

- `proactivity`: consent, cadence, invite-before-plan, no background render
- `ritual_quality`: source refs, intent, ritual sections, captions
- `media`: real media or expected fallback, waveform readiness, music loop/sync, cinema readiness, transcript sections
- `ui`: photo, breath, meditation, body completion, console/network contract
- `negative_cases`: no consent, skipped invitation, missing token, zero budget, video blocked

Skipped browser/media checks mean the default mock run did not produce that live asset. In provider-backed mode, missing requested live media is a failure, not a pass. Browser-driver checks should turn `browser_checks.json` and `artifacts_checked.json` into actionable pass/fail outputs.
