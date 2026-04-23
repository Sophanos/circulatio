# Hermes Real Host Harness Dataset

This dataset family drives the real Hermes-to-Circulatio host harness in
`scripts/evaluate_hermes_real_host.py`.

It is intentionally small and execution-first:

- every case is meant to run through the actual `hermes chat` CLI
- tool-call evidence comes from `-v -Q`
- visible-host behavior is scored from the rendered reply, not from backend mocks

## Purpose

Use this dataset family to catch:

- wrong host routing
- missing tool calls
- host-side interpretation leaks
- raw tool / JSON / id leaks in visible chat
- retry loops after method-state stop signals
- read-surface regressions
- timeouts on real host surfaces such as `journey_page`

## Files

- `schema/host_case.schema.json`: human-facing schema reference
- `baseline.jsonl`: representative routing and multi-turn anchored-flow checks
- `redteam.jsonl`: explicit leak and retry-loop probes
- `typology_journeys.jsonl`: story-based typology QA suite with resumable
  turn-by-turn cases

## Run

Dry-run the selected cases:

```bash
python3 scripts/evaluate_hermes_real_host.py --dry-run
```

Run the default baseline:

```bash
python3 scripts/evaluate_hermes_real_host.py --strict
```

Run the redteam probes only:

```bash
python3 scripts/evaluate_hermes_real_host.py \
  --dataset tests/evals/hermes_real_host/redteam.jsonl \
  --strict
```

Write reports:

```bash
python3 scripts/evaluate_hermes_real_host.py \
  --report-json artifacts/hermes_real_host/report.json \
  --report-md artifacts/hermes_real_host/report.md \
  --trace-jsonl artifacts/hermes_real_host/trace.jsonl
```

## Scope

This harness is not backend truth and not a replacement for:

- `scripts/hermes_host_smoke.py`
- `tests/test_hermes_host_smoke.py`
- bridge validation tests
- service-layer tests

It is the operator-grade conversational complement to those layers.

## Notes

- Keep prompts synthetic or operator-authored. Do not paste private user sessions into JSONL.
- Prefer stable expectations: required tools, forbidden tools, leak bans, and bounded reply shape.
- Legacy multi-turn cases still use `turns` + `sessionLabel`.
- Flat story-turn cases can resume by earlier `caseId` via `resumeFromCaseId`.
