# Journey CLI Evals

This dataset family defines synthetic journey and JTBD cases for the repo-local Journey CLI
comparison harness.

## Purpose

Use these cases to compare external local coding CLIs such as `kimi`, `codex`, and `opencode`
against the Hermes routing contract for Circulatio. The harness can also run an opt-in `hermes`
adapter as a lightweight host probe.

The same CLI now has a separate `--ritual-eval` mode for long-form ritual simulation and artifact
audits. That mode does not consume these JSONL cases; it writes a run report under
`artifacts/journey_cli_eval/runs/{runId}/` and is documented in `docs/JOURNEY_CLI.md`.

It is local-only, opt-in, not backend truth, not runtime infrastructure, and not a replacement for
Hermes host smoke.

Files:

- `schema/journey_case.schema.json`: machine-readable case schema
- `baseline.jsonl`: core routing and read-boundary cases
- `compound.jsonl`: multi-turn and holdout-style stories
- `redteam.jsonl`: hostile or drift-catching boundary cases

## Schema Notes

- `schemaVersion` is fixed at `1` for this dataset family.
- Top-level fields are closed so case authors use shared vocabulary instead of silent one-off
  fields.
- `historySeed` is intentionally open so synthetic setup detail can evolve without changing the
  routing contract.
- `turns[].expected` separates host route, surface, write-budget, and reply-style checks.

## Triage Mapping

The Journey CLI harness emits suggestions, not truth:

- store-first or lookup-before-repeat failures: usually `skill` datasets such as
  `execution_skill_routing.jsonl`
- wrong explicit tool choice: usually `tool_descriptions` datasets such as
  `execution_tool_choice.jsonl` or `tool_description_routing.jsonl`
- pacing, consent, or symbolic-intensity drift after the route: usually `prompt_fragments`
  datasets such as `grounding_pacing.jsonl`, `consent_boundary.jsonl`,
  `execution_prompt_behavior.jsonl`, or `typology_restraint.jsonl`
- read-mostly write leaks or persistence mistakes: backend service tests
- malformed Hermes-facing envelopes: bridge tests
- true host/plugin load failures: `scripts/hermes_host_smoke.py`

## Running

```bash
.venv/bin/python -m unittest tests.test_journey_cli_eval
.venv/bin/python scripts/evaluate_journey_cli.py --adapter fake --strict
```

Examples:

```bash
.venv/bin/python scripts/evaluate_journey_cli.py --adapter codex --case embodied_recurrence_001 --require-adapters
.venv/bin/python scripts/evaluate_journey_cli.py --adapter hermes --case embodied_recurrence_001 --require-adapters
.venv/bin/python scripts/evaluate_journey_cli.py --adapter all --split dev --write-baseline artifacts/journey_cli_eval/baselines/dev.summary.json
```

## Data Hygiene

- Keep cases synthetic. Do not place private user material or copied production conversations in
  these JSONL files.
- Treat these cases as contract fixtures. If a story belongs to backend or bridge truth, mirror it
  in dedicated tests instead of only expanding the CLI dataset.
