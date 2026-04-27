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
- Did completion sync call only `circulatio_record_ritual_completion`?
- Did Chutes/token/budget/video gates avoid unintended provider calls?
- Did each artifact expose the expected manifest, captions, breath, meditation, media, and completion fields?

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

`tool_calls.json` redacts user-authored text fields. Provider tokens are never written.

## Scorecard

The report groups checks into:

- `proactivity`: consent, cadence, invite-before-plan, no background render
- `ritual_quality`: source refs, intent, ritual sections, captions
- `media`: real media or expected fallback, waveform readiness, transcript sections
- `ui`: photo, breath, meditation, body completion, console/network contract
- `negative_cases`: no consent, skipped invitation, missing token, zero budget, video blocked

Skipped browser/media checks mean the default mock run did not produce that live asset. They should be promoted to pass/fail by running live providers or adding a browser driver over the generated report bundle.
