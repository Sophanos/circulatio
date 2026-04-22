# Circulatio

Every app captures. Almost none help you become.

Circulatio is a companion system for inner work. It holds your dreams, body states, reflections, and charged events — not as data to warehouse, but as living material for meaning.

Symbols are personal, yet they belong to something older than you. The snake in your cellar is yours, but it is also centuries of myth, literature, and human experience speaking through you. Circulatio traces these threads: your own recurring images, their echoes in culture and history, and the direction your soul is trying to take.

**Hold first, interpret later, approve before writing symbolic memory.**

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

## Quickstart

```bash
git clone https://github.com/Sophanos/circulatio.git
cd circulatio
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
python -m pytest tests/
```

**Already installed?**
```bash
pip install -e ".[dev]" --upgrade
```

**Evaluate method quality:**
```bash
.venv/bin/python scripts/evaluate_circulatio_method.py --strict
```

---

## First workflow

Store material without interpreting it yet:

```bash
/circulation dream "I walked through a house and found a snake in the cellar."
```

Ask for interpretation when you are ready:

```bash
/circulation reflect "A snake image kept returning after the conflict."
```

Review what Circulatio proposes before it becomes memory:

```bash
/circulation approve last p1
/circulation reject last p1 --reason "do not save this"
```

Explore longer-term patterns:

```bash
/circulation discovery --query "snake and chest tension" --limit 4
/circulation review threshold
/circulation review week
```

---

## Architecture

Circulatio is a durable backend for symbolic memory. It can embed in a host agent today (Hermes) and adapt to other hosts later. See [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) for the full system stack, scalability thesis, and builder-psyche separation.

The host handles routing, sessions, and scheduling. Circulatio handles:
- **Memory kernel** — typed, privacy-classed, provenance-bound
- **Graph engine** — derived symbol-to-symbol projections, no external graph DB
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
| **Evening** | You ask: *"What is alive today?"* It weaves the morning's tension into the recurring water symbol, offers a cultural parallel as invitation, and asks a gentle question. |
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
