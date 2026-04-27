# Circulatio

Circulatio is a symbolic-memory and ritual-planning backend for Hermes.

Every app captures. Almost none help you become.

Circulatio holds dreams, body states, reflections, charged events, practices, journeys, and living symbols as material for individuation. It does not rush every note into a clever interpretation. It remembers, waits, surfaces patterns, and when the moment is right, can help Hermes turn symbolic material into a guided ritual.

It is not a wellness tracker, productivity OS, therapy simulator, or frontend app. Hermes owns routing, session orchestration, scheduling, consent UX, and delivery. Circulatio owns durable symbolic memory, evidence-backed interpretation, ritual plans, invitation payloads, and completion records.

---

## Current Capabilities

- **Hold-first capture** - store dreams, reflections, body states, symbolic events, and relational scenes without forcing interpretation.
- **Depth interpretation** - LLM-first, evidence-backed interpretation with safety gates, approval flows, and user confirmation.
- **Continuity memory** - native context, graph projections, memory kernel, symbol histories, journeys, reviews, and living myth surfaces.
- **Proactive runtime** - `alive_today`, rhythmic briefs, journey pages, weekly reviews, and consent-bound ritual invitations.
- **Ritual planning** - Hermes can call one `circulatio_plan_ritual` tool and receive a typed `PresentationRitualPlan` for text, voice script, captions, breath, meditation, image, audio, or cinema surfaces.
- **Ritual artifacts** - the repo-local renderer turns a plan into a static manifest for Hermes Rituals playback.
- **Ritual completion sync** - Hermes/frontend can record idempotent completion events, optional literal reflections, and explicit practice feedback without triggering interpretation.
- **Provider gates** - external speech/image/music/video rendering is renderer-owned, opt-in, budget-gated, and beta-gated for music/video.

---

## Quickstart

### Install

```bash
git clone https://github.com/Sophanos/circulatio.git
cd circulatio

# Install into Hermes's own interpreter
~/.hermes/hermes-agent/venv/bin/python3 -m pip install -e "$PWD"

# Canonical plugin path
mkdir -p ~/.hermes/plugins
ln -sfn "$PWD/src/circulatio_hermes_plugin" ~/.hermes/plugins/circulatio

hermes plugins enable circulatio
hermes plugins list
```

### Verify

```text
/plugins
/circulation journey list
```

Expected:
- `/plugins` shows `circulatio`
- `/circulation journey list` does not say `Unknown command`

### Smoke Test

In Hermes, store a dream or charged fragment:

```text
I dreamed a black dog stood motionless at my front door.
```

Expected shape:
- Hermes stores the material first.
- Circulatio acknowledges the record.
- No full interpretation is forced.

Then ask for meaning only when you want meaning:

```text
Let's stay with the black dog dream. What feels important here?
```

Expected shape:
- Circulatio uses the stored material and available context.
- It starts with containment and evidence, not a symbol-dictionary answer.
- It may ask one bounded question before making stronger claims.

### Ritual Smoke Test

Ask Hermes for a ritual from existing Circulatio material:

```text
Make a short breath-and-meditation ritual from what has been alive this week.
```

Expected shape:
- Hermes calls `circulatio_plan_ritual`.
- Circulatio returns a read-only `PresentationRitualPlan`.
- Hermes may render it into an artifact URL for Hermes Rituals playback.

Scheduled ritual surfacing stays invitation-only. Cron may create a consent-bound `ritual_invitation`, but planning and rendering wait for explicit user acceptance.

---

## Rituals And Media

Create a plan through Hermes or a test fixture, then render it locally with mock providers:

```bash
.venv/bin/python scripts/render_ritual_artifact.py \
  --plan artifacts/rituals/plans/{planId}.json \
  --out apps/hermes-rituals-web/public/artifacts/{artifactId} \
  --mock-providers \
  --dry-run
```

The Hermes Rituals app can load the resulting manifest at `/artifacts/{artifactId}`. The built-in fixture is available at `/artifacts/weekly-ritual-dry-run`.

Mock and dry-run artifacts are valid contract tests, but they are not proof of generated media. A dry-run manifest may have `surfaces.audio.provider == "mock"`, no `audio.src`, `image.enabled == false`, and only fallback captions. Provider-backed artifacts should include concrete public files such as `audio.wav`, `image.png`, `captions.vtt`, and `manifest.json` under `apps/hermes-rituals-web/public/artifacts/{artifactId}/`.

Completion is explicit and idempotent. The frontend validates the artifact and idempotency key, Hermes forwards the completion event, and Circulatio stores a `RitualCompletionEvent`. Optional reflections are stored literally only when user-authored. Completion does not trigger interpretation.

Chutes provider rendering is available from the renderer only. Keep the API token in your shell or an ignored local env file, then request the provider profile explicitly:

```bash
export CHUTES_API_TOKEN=...
.venv/bin/python scripts/render_ritual_artifact.py \
  --plan artifacts/rituals/plans/{planId}.json \
  --out apps/hermes-rituals-web/public/artifacts/{artifactId} \
  --provider-profile chutes_speech \
  --surfaces audio,captions \
  --transcribe-captions \
  --max-cost-usd 0.05
```

The renderer also has opt-in Chutes profiles for image, music, and video. `chutes_all` currently means the safe live bundle: audio, captions, and image. Music and video are separate beta surfaces and require `--allow-beta-music` or `--allow-beta-video`. All provider calls require a plan that allows external providers plus an explicit positive budget flag. Raw Circulatio source text is not sent to providers.

Frontend playback is manifest-driven. `RitualPlayer` uses real `artifact.audioUrl` before any silent fallback, waits for audio metadata before replacing planned duration with actual media duration, decodes the audio file into waveform peaks, keeps scrub/progress aligned to the same clock, and opens image-backed artifacts on the Photo lens. Captions remain required even when Whisper fails; fallback segments still drive transcript sections and `captions.vtt`.

For provider-backed multimedia, use a paid Chutes account. As of April 25, 2026, Chutes lists a Plus plan at `$10/month`; check [chutes.ai/pricing](https://chutes.ai/pricing) before relying on a specific price, quota, or model surface.

---

## Why This Exists

Symbols are personal, yet they belong to something older than you. The snake in your cellar is yours, but it is also centuries of myth, literature, and human experience speaking through you. Circulatio traces these threads: your own recurring images, their echoes in culture and history, and the direction your soul is trying to take.

Journals store. Chatbots react. Circulatio creates meaning and continuity:

- **Capture without performing insight.** Drop a fragment when you are raw; return to it when you are ready.
- **It remembers the threads you would lose.** A dream in March, a body state in June - held until the pattern speaks.
- **You remain the author of your own symbols.** Nothing becomes true about you without your witness.
- **Your images become a language you recognize.** Not generic meanings. Your own recurring vocabulary, deepening over time.
- **Ritual becomes a container, not content output.** A ritual is planned from existing symbolic context, rendered by the host, and completed only when you explicitly act.

It does not diagnose, gamify, or optimize.
It holds, remembers, and helps patterns become visible.

<p align="center">
  <img src="docs/diagram.svg" alt="Circulatio diagram: material enters the vessel (dreams, body states, reflections, charged events), passes through capture / hold / interpret, and becomes visible as pattern, journeys, living myth, rituals, and analysis packets - guarded by grounding, evidence, hypotheses, approval, and offline evolution." width="100%" />
</p>

---

## Detailed Setup And Installation

### Prerequisites

- Python 3.11+
- [Hermes](https://github.com/hermes-ai/hermes) installed and on your `PATH` (`which hermes` should return a path)

### Step 1 - Clone the repo

```bash
git clone https://github.com/Sophanos/circulatio.git
cd circulatio
```

From here on, `$CIRCULATIO_PATH` means the absolute path to this directory, for example `/Users/you/projects/circulatio` or `/home/you/circulatio`.

### Step 2 - Install Circulatio into Hermes's Python environment

Circulatio must be installed into the **same virtual environment that Hermes runs in**, not a separate one.

```bash
# Confirm where Hermes lives
which hermes
head -n 1 "$(which hermes)"

# Make sure Hermes's venv has pip
~/.hermes/hermes-agent/venv/bin/python3 -m ensurepip --upgrade

# Install Circulatio (replace $CIRCULATIO_PATH with the actual path)
~/.hermes/hermes-agent/venv/bin/python3 -m pip install -e "$CIRCULATIO_PATH"
```

**What this does:** installs the `circulatio` library and the `circulatio_hermes_plugin` Python package into Hermes's interpreter so the tools and commands can be imported at runtime.

### Step 3 - Symlink the plugin manifest

Hermes discovers plugins by looking for a directory containing a `plugin.yaml` file inside `~/.hermes/plugins/`.

```bash
mkdir -p ~/.hermes/plugins
ln -sfn "$CIRCULATIO_PATH/src/circulatio_hermes_plugin" ~/.hermes/plugins/circulatio
```

**What this does:** creates a symlink pointing Hermes to the packaged plugin manifest (`src/circulatio_hermes_plugin/plugin.yaml`) that declares which tools and commands Circulatio provides.

> **Why two steps?** `pip install -e` makes the Python code importable; the symlink tells Hermes "there is a plugin here and here is its manifest." Both are required.

### Step 4 - Enable the plugin

```bash
hermes plugins enable circulatio
hermes plugins list
```

### Step 5 - Verify

Start a new Hermes session, then run:

```text
/plugins
/circulation journey list
```

Expected:
- `/plugins` shows `circulatio`
- `/circulation journey list` does not say `Unknown command`

---

## Troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| `which hermes` returns nothing | Hermes is not installed or not on your `PATH` | Install Hermes first |
| `Plugin 'circulatio' is not installed or bundled.` | You installed Circulatio into the wrong Python environment | Use the interpreter shown by `head -n 1 "$(which hermes)"` |
| `plugin.yaml not found` or plugin fails to load | The symlink points to the wrong directory | Make sure the symlink target is `$CIRCULATIO_PATH/src/circulatio_hermes_plugin` |
| Permission denied on `~/.hermes/plugins` | The directory does not exist or has wrong permissions | Run `mkdir -p ~/.hermes/plugins` and check ownership |

---

## Architecture

Circulatio is a durable backend for symbolic memory and ritual planning. It can embed in a host agent today through Hermes and adapt to other hosts later. See [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) for the full system stack, scalability thesis, and builder-psyche separation.

The host handles routing, sessions, consent UX, scheduling, delivery, and external presentation. Circulatio handles:

- **Memory kernel** - typed, privacy-classed, provenance-bound records
- **Graph engine** - derived symbol-to-symbol projections, no external graph DB
- **Context derivation** - native life-context built from your own records
- **LLM-first interpretation** - structured depth output with safety backstops
- **Approval flows** - symbolic writes are proposals until you accept them
- **Proactive runtime** - `alive_today`, rhythmic briefs, journey pages, weekly reviews, and ritual invitations
- **Ritual planning** - read-only `PresentationRitualPlan` generation from existing source refs
- **Ritual completion** - idempotent `RitualCompletionEvent` storage, literal-only reflection handling, and explicit practice feedback
- **Read surfaces** - discovery, journey pages, threshold reviews, living myth reviews, and bounded analysis packets
- **Practice lifecycle** - recommendations, follow-ups, and integration, held lightly

It can run in-memory for testing or with a SQLite-backed profile runtime for durable local use. The graph and memory kernel are derived projections; SQLite remains canonical storage.

### Runtime Boundaries

- Hermes decides when Circulatio is relevant and which tool to call.
- Circulatio stores and interprets symbolic state; it does not route the whole conversation.
- Ritual planning is read-only over existing source context.
- Scheduled rituals start as invitations, never background media generation.
- The renderer and Hermes Rituals frontend own playback, media files, provider calls, and completion UX.

---

## The Daily Rhythm

| Time | Experience |
|------|------------|
| **Morning** | A brief pattern surfacing: *"You dreamed of water three times this month. Yesterday you noted chest tension before a meeting. Want a 3-minute body check-in?"* You choose. No guilt. |
| **Day** | Drop a fragment: a dream, a body sensation, a strange coincidence, a mood shift. Circulatio stores it. It **holds** without pressing. |
| **Evening** | You ask: *"What's showing up?"* It weaves the morning's tension into the recurring water symbol, offers a cultural parallel as invitation, and asks a gentle question. |
| **Weekly** | A deeper synthesis: what recurred, what shifted, what was avoided, what new symbol emerged, what goal tension is visible. You may receive a ritual invitation, but planning waits for your acceptance. |
| **After a ritual** | Completion is recorded idempotently. A reflection is stored only if you write it. Completion does not trigger interpretation. |

---

## How It Interprets

Circulatio does not guess meanings from a symbol dictionary. It follows a hermeneutic method rooted in Jung, Marie-Louise von Franz, and Robert A. Johnson:

- **Context before claim.** No full interpretation without your narrative, attitude, and recent life context.
- **Subjective level by default.** Dream figures are treated as features of your own personality; objective readings only with your confirmation.
- **Series over snapshots.** A single dream is a snapshot; a series is a conversation.
- **Containment before depth.** Grounding is assessed before shadow or archetypal language is offered.
- **Ritual after source.** Rituals are compiled from accepted source context; they do not invent a new interpretation path.

See [`docs/INTERPRETATION_ENGINE_SPEC.md`](docs/INTERPRETATION_ENGINE_SPEC.md) for the full method.

---

## The Bottom Line

Circulatio is not a wellness tracker, productivity OS, therapy simulator, or media generator. It is a **symbolic memory system for people doing inner work**.

What it holds to:

- **You are the source of insight.** Circulatio is the mirror that remembers.
- **Pattern over interpretation.** A held recurrence is more powerful than a clever reading.
- **Body is symbol.** Somatic events are as meaningful as dreams.
- **Culture is amplification, not explanation.** Mythic parallels are resonance, not proof.
- **Ritual is consent-bound.** Scheduled surfaces invite; accepted planning begins only after you choose it.
- **Shadow work requires consent.** Offered, never imposed.
- **The unconscious has its own timing.** Do not rush the door. Keep the key present.
- **The goal is individuation, not optimization.** More conscious conflict is better than unconscious harmony.
- **Success is obsolescence.** You should need Circulatio less over time, because you become your own witness.

If you want an AI that optimizes your day, look elsewhere.  
If you want a companion that remembers what you forget and sees what you cannot yet hold alone, you are in the right place.

---

## Further Reading

| Document | Read this to... |
|----------|----------------|
| [`ARCHITECTURE.md`](docs/ARCHITECTURE.md) | Understand the system stack and scalability thesis |
| [`ROADMAP.md`](docs/ROADMAP.md) | See user outcomes, use cases, and development phases |
| [`ENGINEERING_GUIDE.md`](docs/ENGINEERING_GUIDE.md) | Build or contribute to the codebase |
| [`INTERPRETATION_ENGINE_SPEC.md`](docs/INTERPRETATION_ENGINE_SPEC.md) | Understand the Jungian hermeneutic method |
| [`PRESENTATION_LAYER.md`](docs/PRESENTATION_LAYER.md) | Understand ritual plans, artifacts, invitations, completion, and renderer boundaries |
| [`SELF_EVOLUTION_OS.md`](docs/SELF_EVOLUTION_OS.md) | Learn how the method evolves offline |
