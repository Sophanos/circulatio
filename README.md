# Circulatio

Circulatio is a symbolic-memory backend for Hermes.

Every app captures. Almost none help you become.

Circulatio is a companion system for inner work. It holds your dreams, body states, reflections, and charged events — not as data to warehouse, but as living material for meaning.

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

### 60-second demo

In Hermes, first store a dream:

```text
I dreamed a black dog stood motionless at my front door.
```

Expected shape:
- Hermes stores the dream first
- the reply briefly acknowledges it
- no full interpretation is forced yet

Then ask for interpretation:

```text
Let's interpret the dream.
```

Expected shape:
- Circulatio starts a collaborative interpretation
- the first reply is usually one bounded question, not a full reading

### Ritual artifact dry run

Create a plan through Hermes or a test fixture, then render it locally with mock providers:

```bash
.venv/bin/python scripts/render_ritual_artifact.py \
  --plan artifacts/rituals/plans/{planId}.json \
  --out apps/hermes-rituals-web/public/artifacts/{artifactId} \
  --mock-providers \
  --dry-run
```

The Hermes Rituals app can load the resulting manifest at `/artifacts/{artifactId}`. The built-in fixture is available at `/artifacts/weekly-ritual-dry-run`. Scheduled cron must not run this renderer; it should create only `ritual_invitation` rhythmic briefs and wait for explicit user acceptance before planning.

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

The renderer also has opt-in Chutes profiles for image, music, video, and all surfaces. Those calls still require a plan that allows external providers plus an explicit positive budget flag; raw Circulatio source text is not sent to providers. Music and video additionally require `--allow-beta-music` or `--allow-beta-video`.

Example reply shape:

```text
The dream is saved, and I want to go into it together with you.

Which moment or image feels most alive to you right now?
```

---

Symbols are personal, yet they belong to something older than you. The snake in your cellar is yours, but it is also centuries of myth, literature, and human experience speaking through you. Circulatio traces these threads: your own recurring images, their echoes in culture and history, and the direction your soul is trying to take.

Journals store. Chatbots react. Circulatio creates meaning and continuity:

- **Capture without performing insight.** Drop a fragment when you're raw; return to it when you're ready.
- **It remembers the threads you would lose.** A dream in March, a body state in June — held until the pattern speaks.
- **You remain the author of your own symbols.** Nothing becomes "true" about you without your witness.
- **Your images become a language you recognize.** Not generic meanings. Your own recurring vocabulary, deepening over time.

It does not diagnose, gamify, or optimize.  
It holds, remembers, and helps patterns become visible.

<p align="center">
  <img src="docs/diagram.svg" alt="Circulatio diagram: material enters the vessel (dreams, body states, reflections, charged events), passes through capture / hold / interpret, and becomes visible as pattern, journeys, living myth, and analysis packets — guarded by grounding, evidence, hypotheses, approval, and offline evolution." width="100%" />
</p>

---

## Detailed Setup And Installation

### Prerequisites

- Python 3.11+
- [Hermes](https://github.com/hermes-ai/hermes) installed and on your `PATH` (`which hermes` should return a path)

### Step 1 — Clone the repo

```bash
git clone https://github.com/Sophanos/circulatio.git
cd circulatio
```

From here on, `$CIRCULATIO_PATH` means the absolute path to this directory (e.g. `/Users/you/projects/circulatio` or `/home/you/circulatio`).

### Step 2 — Install Circulatio into Hermes's Python environment

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

### Step 3 — Symlink the plugin manifest

Hermes discovers plugins by looking for a directory containing a `plugin.yaml` file inside `~/.hermes/plugins/`.

```bash
mkdir -p ~/.hermes/plugins
ln -sfn "$CIRCULATIO_PATH/src/circulatio_hermes_plugin" ~/.hermes/plugins/circulatio
```

**What this does:** creates a symlink pointing Hermes to the packaged plugin manifest (`src/circulatio_hermes_plugin/plugin.yaml`) that declares which tools and commands Circulatio provides.

> **Why two steps?** `pip install -e` makes the Python code importable; the symlink tells Hermes "there is a plugin here and here is its manifest." Both are required.

### Step 4 — Enable the plugin

```bash
hermes plugins enable circulatio
hermes plugins list
```

### Step 5 — Verify

Start a new Hermes session, then run:

```text
/plugins
/circulation journey list
```

Expected:
- `/plugins` shows `circulatio`
- `/circulation journey list` does not say `Unknown command`

---

### Troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| `which hermes` returns nothing | Hermes is not installed or not on your `PATH` | Install Hermes first |
| `Plugin 'circulatio' is not installed or bundled.` | You installed Circulatio into the wrong Python environment | Use the interpreter shown by `head -n 1 "$(which hermes)"` |
| `plugin.yaml not found` or plugin fails to load | The symlink points to the wrong directory | Make sure the symlink target is `$CIRCULATIO_PATH/src/circulatio_hermes_plugin` (the directory that contains `plugin.yaml`) |
| Permission denied on `~/.hermes/plugins` | The directory does not exist or has wrong permissions | Run `mkdir -p ~/.hermes/plugins` and check ownership |

---

## Architecture

Circulatio is a durable backend for symbolic memory. It can embed in a host agent today (Hermes) and adapt to other hosts later. See [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) for the full system stack, scalability thesis, and builder-psyche separation.

The host handles routing, sessions, and scheduling. Circulatio handles:
- **Memory kernel** — typed, privacy-classed, provenance-bound
- **Graph engine** — derived symbol-to-symbol projections (2 hops supported), no external graph DB
- **Context derivation** — native life-context built from your own records
- **LLM-first interpretation** — structured depth output with safety backstops
- **Approval flows** — symbolic writes are proposals until you accept them
- **Proactive runtime** — `alive_today`, rhythmic briefs, journey pages, and weekly reviews
- **Read surfaces** — discovery, journey pages, threshold reviews, living myth reviews, and bounded analysis packets
- **Practice lifecycle** — recommendations, follow-ups, and integration, held lightly

It can run in-memory for testing or with a SQLite-backed profile runtime for durable local use.

---

## The Daily Rhythm

| Time | Experience |
|------|------------|
| **Morning** | A brief pattern surfacing — *"You dreamed of water three times this month. Yesterday you noted chest tension before a meeting. Want a 3-minute body check-in?"* You choose. No guilt. |
| **Day** | Drop a fragment: a dream, a body sensation, a strange coincidence, a mood shift. Circulatio stores it. It **holds** without pressing. |
| **Evening** | You ask: *"What's showing up?"* It weaves the morning's tension into the recurring water symbol, offers a cultural parallel as invitation, and asks a gentle question. |
| **Weekly** | A deeper synthesis: what recurred, what shifted, what was avoided, what new symbol emerged, what goal tension is visible. You read it like a journal you did not write alone. |

---

## How It Interprets

Circulatio does not guess meanings from a symbol dictionary. It follows a hermeneutic method rooted in Jung, Marie-Louise von Franz, and Robert A. Johnson:

- **Context before claim.** No full interpretation without your narrative, attitude, and recent life context.
- **Subjective level by default.** Dream figures are treated as features of your own personality; objective readings only with your confirmation.
- **Series over snapshots.** A single dream is a snapshot; a series is a conversation.
- **Containment before depth.** Grounding is assessed before shadow or archetypal language is offered.

See [`docs/INTERPRETATION_ENGINE_SPEC.md`](docs/INTERPRETATION_ENGINE_SPEC.md) for the full method.

---

## The Bottom Line

Circulatio is not a wellness tracker, productivity OS, or therapy simulator. It is a **symbolic memory system for people doing inner work**.

What it holds to:

- **You are the source of insight.** Circulatio is the mirror that remembers.
- **Pattern over interpretation.** A held recurrence is more powerful than a clever reading.
- **Body is symbol.** Somatic events are as meaningful as dreams.
- **Culture is amplification, not explanation.** Mythic parallels are resonance, not proof.
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
| [`SELF_EVOLUTION_OS.md`](docs/SELF_EVOLUTION_OS.md) | Learn how the method evolves offline |

The method quality command in Quickstart runs against explicit rubrics defined in the offline Evolution OS. It does not mutate live state.
