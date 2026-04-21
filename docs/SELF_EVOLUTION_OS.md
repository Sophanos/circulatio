# Evolution OS

Circulatio's Evolution OS is an offline development layer for improving method artifacts without changing live runtime behavior mid-conversation.

It exists to generate, evaluate, package, and review candidate edits to:

- `src/circulatio/llm/prompt_fragments.py`
- `src/circulatio_hermes_plugin/skills/circulation/SKILL.md`
- descriptive text in `src/circulatio_hermes_plugin/schemas.py`

It does not modify user state, prompt state in production, or deterministic runtime guardrails.

## Scope

### Mutable Targets

- `prompt_fragments`
  Why: method-policy text already lives in prompt fragments and is evaluated through `prompt_builder.py`.
- `skill`
  Why: Hermes routing behavior is largely defined by the Circulatio host skill contract.
- `tool_descriptions`
  Why: tool descriptions influence host tool selection without changing parameter contracts.

### Review-Only Reference Artifacts

- `docs/RUNBOOK.md`
- `docs/ENGINEERING_GUIDE.md`
- `docs/INTERPRETATION_ENGINE_SPEC.md`

These documents may inform candidate rationale, but the optimizer does not rewrite them in phase 1.

### Immutable Guardrails

The optimizer must never mutate or bypass:

- `src/circulatio/core/safety_gate.py`
- `src/circulatio/core/method_state_policy.py`
- `src/circulatio/core/interpretation_mapping.py`
- `src/circulatio/application/circulatio_service.py`
- persistence schemas or repository write semantics
- approval-gated write logic
- consent enforcement
- evidence integrity checks
- live prompt state

## Architecture

The offline layer lives under `tools/self_evolution/`.

- `targets.py`
  Registry for optimizable artifacts, mutation scope, ownership, and immutable dependencies.
- `dataset_builder.py`
  Loads schemaVersion 1 and schemaVersion 2 JSONL eval cases and normalizes split / severity / gate metadata.
- `constraints.py`
  Enforces hard constraints such as required prompt fragment functions, skill size, tool-description limits, candidate-path validity, and immutable bundle boundaries.
- `fitness.py`
  Scores deterministic prompt, skill, and tool-description cases while preserving split, severity, and gate metadata.
- `evaluator.py`
  Runs baseline or candidate evaluations, computes regression status, and supports candidate-bundle evaluation.
- `artifacts.py`
  Handles candidate bundle discovery, staging, hashing, git provenance, and diff generation.
- `llm_client.py`
  Shared structured-JSON client for offline generation, execution evals, and advisory judging.
- `cache.py`
  Run-local cache for repeated LLM calls.
- `traces.py`
  Sanitized execution, generation, judge, and run-event trace sinks.
- `materializers.py`
  Target-specific candidate materializers that constrain automatic edits to trusted baseline structures.
- `generation.py`
  Reflective candidate generation over prompt fragments, skill sections, and tool descriptions.
- `execution.py`
  Execution-backed harnesses for prompt behavior, skill routing, and tool selection.
- `judge.py`
  Advisory LLM-as-judge scoring. Judge output informs ranking but never overrides hard gates.
- `selection.py`
  Candidate scorecards plus Pareto-style frontier selection.
- `review.py`
  Produces `report.json`, `report.md`, `diff.patch`, `manifest.json`, traces, frontier artifacts, and reviewer-facing summaries.
- `optimizer.py`
  Orchestrates offline candidate strategies. `manual` stages human-supplied artifacts; `reflection` and `pareto_reflection` now generate and rank candidates offline.

## Candidate Lifecycle

```text
baseline artifact(s)
  -> dataset selection
  -> candidate generation or manual staging
  -> deterministic gates
  -> execution-backed evaluation
  -> advisory judge scoring
  -> frontier / best-candidate selection
  -> holdout stage (when holdout cases exist)
  -> review package
  -> human review
  -> normal merge path
```

The output is a reviewable filesystem artifact bundle, not a runtime mutation. Automatic search never hot-swaps runtime prompts, never calls into a `CirculatioService` mutation API, and never writes production state.

## Run Artifacts

Manual and future generated runs are written under:

```text
artifacts/self_evolution/runs/<run_id>/
  manifest.json
  candidate_manifest.json
  report.json
  report.md
  diff.patch
  rationale.md
  sanitized_traces.jsonl
  candidate_index.json
  frontier.json
  generation_trace.jsonl
  execution_traces.jsonl
  judge_scores.jsonl
  run_events.jsonl
  branch_plan.md
  apply_candidate_branch.sh
  suggested_eval_cases.jsonl
  candidates/
    <candidate_id>/...
```

Trace artifacts are sanitized by default. They are review aids, not a production telemetry stream.

## Dataset Model

The evaluator supports two dataset shapes.

### schemaVersion 1

Legacy cases may omit `schemaVersion`, `split`, `severity`, `targetKinds`, and `gateType`.

Defaults:

- `schemaVersion = 1`
- `split = dev`
- `severity = blocking`
- `gateType = deterministic`

### schemaVersion 2

New cases may declare:

- `schemaVersion`
- `targetKinds`
- `split`
- `severity`
- `gateType`
- existing deterministic prompt / skill / tool-description checks

### schemaVersion 3

Execution-backed and judge-aware cases may additionally declare:

- `execution`
  Structured execution-harness config such as `mode`, `userTurn`, `expectationHints`, and token budget.
- `judge`
  Optional advisory rubric config such as `mode`, `rubric`, and token budget.

Older case shapes remain valid. Unknown fields are preserved so the evaluator can attach richer behavior metadata without breaking legacy fixtures.

Supported split values:

- `train`
- `dev`
- `holdout`
- `redteam`
- `regression`

Supported severity values:

- `blocking`
- `major`
- `minor`

Supported gate types:

- `constraint`
- `deterministic`
- `execution`
- `judge`

## Promotion Rules

A candidate is reviewable only if:

- it stays within the closed mutation boundary
- no immutable artifacts appear in the bundle
- constraint findings are empty
- blocking failures are zero
- overall regressions are absent when compared with baseline
- human review accepts the package
- normal repo tests still pass

Passing eval does not auto-merge anything.

Current manifest states:

- `generated`
- `deterministic_passed`
- `holdout_passed`
- `failed`
- later human workflow states such as `approved_for_pr` or `rejected` remain review-side decisions, not automatic transitions

## Privacy

Reports and traces must not include:

- raw `InteractionFeedbackRecord.note` text from real user data
- raw personal material from live profiles
- unsanitized execution traces

The repo fixtures are synthetic and should stay that way.

## Prompt Injection Boundary

Prompt-fragment evaluation no longer monkeypatches `prompt_builder.prompt_fragments` globally. Prompt builders accept an explicit fragment provider for offline evaluation, which keeps runtime behavior unchanged while making multi-candidate execution safer.

## CLI

Baseline evaluation:

```bash
.venv/bin/python scripts/evaluate_circulatio_method.py --strict
```

Candidate bundle evaluation with optional execution and judge overlays:

```bash
.venv/bin/python scripts/evaluate_circulatio_method.py \
  --target prompt_fragments \
  --candidate-dir artifacts/self_evolution/runs/example_bundle \
  --execution \
  --judge \
  --fail-on-regression \
  --strict
```

Manual candidate staging:

If no `--split` filter is provided, the manual optimizer evaluates `dev`, `redteam`, and `regression` first, then runs `holdout` as a separate promotion stage when holdout fixtures exist for the selected targets.

```bash
.venv/bin/python scripts/evolve_circulatio_method.py \
  --target prompt_fragments \
  --strategy manual \
  --prompt-fragments /tmp/prompt_fragments.py \
  --strict
```

Automatic reflective search:

```bash
.venv/bin/python scripts/evolve_circulatio_method.py \
  --target prompt_fragments \
  --strategy pareto_reflection \
  --iterations 2 \
  --population-size 3 \
  --execution \
  --judge \
  --strict
```

## Reviewer Checklist

- Confirm the changed file set stays inside the allowed targets.
- Confirm the review package includes manifest, report, rationale, and diff.
- Confirm red-team, consent, evidence, and approval-boundary cases still pass.
- Confirm no host-layer interpretation was introduced into Hermes-facing artifacts.
- Confirm merge still goes through the normal repository workflow.
