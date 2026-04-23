# Circulatio Architecture
## What We Are Building, Why, and How It Scales

> **Circulatio is an individuation backend that creates symbolic continuity across time.**

It is not a wellness tracker, a chatbot, or a database. It is a **longitudinal hermeneutic continuity substrate**: a system that holds unconscious material, lets it ripen, and only then helps relate to it through a disciplined method — without flattening it into instant answers.

This document is the canonical framing. For user outcomes and use cases, see [`ROADMAP.md`](ROADMAP.md). For implementation details, see [`ENGINEERING_GUIDE.md`](ENGINEERING_GUIDE.md). For the Jungian method specification, see [`INTERPRETATION_ENGINE_SPEC.md`](INTERPRETATION_ENGINE_SPEC.md).

---

## Three Names for the Same Organism

| Register | Name | When to use it |
|----------|------|----------------|
| Poetic | **Soul OS for soul-making** | When you want to remember what this is in service of |
| Product | **Individuation OS** | When describing it to someone who might use it |
| Technical | **Longitudinal hermeneutic continuity substrate** | When you need to explain why this is not a vector DB, a graph engine, or a chatbot wrapper |

The technical name is the most precise. Circulatio is not defined by any single technology layer — memory, graph, LLM, or agent. It is defined by the **relationship between those layers**: a reproducible method that persists across time.

---

## The Eight-Layer Organism

Circulatio is not a pipeline. It is an organism with distinct organs, each with its own function and ethic:

```
                    CIRCOLATIO

   life material
   dreams | body | conflict | symbols | thresholds
                         |
                         v
                  [1] CAPTURE
          store with provenance and privacy
                         |
                         v
                    [2] HOLD
        do not force meaning before ripeness
                         |
                         v
                 [3] CONTINUITY
       recurrence, links, graph, temporal memory
                         |
                         v
                   [4] METHOD
   Jungian / somatic / cultural / reflective lenses
                         |
                         v
                 [5] BOUNDARIES
    consent | safety | approval | evidence integrity
                         |
                         v
                  [6] DIALOGUE
    one question, one pattern, one practice at a time
                         |
                         v
                 [7] INTEGRATION
         approved durable meaning and shifts
                         |
                         v
                [8] INDIVIDUATION
   a more conscious relationship to inner life
```

**How to read this:**
- **Capture** and **Hold** are ethical acts, not technical ones. The system stores material without demanding meaning. This is the "hold first" principle.
- **Continuity** is the technical differentiator. Memory kernel, graph engine, and temporal indexing make recurrence visible across weeks and months.
- **Method** is the disciplined procedure: context → amplification → compensation → assimilation. Today this is Jungian depth hermeneutics. Tomorrow it could host other approaches.
- **Boundaries** are not features. They are guardrails: safety before depth, consent before durable writes, evidence before claims.
- **Dialogue** and **Integration** happen only when the prior layers are present. The system does not interpret alone; it interprets *with* the user, and durable meaning is approval-gated.
- **Individuation** is the outcome: not optimization, not happiness, but a more conscious relationship with one's own inner life.

---

## The Builder / Psyche Split

Circulatio has two bodies: the live psyche layer and the builder layer beside it.

```
     ┌─────────────────────────────────────┐
     │         LIVE PSYCHE LAYER           │
     │  (runtime — never mutated blindly)  │
     │                                     │
     │  capture → hold → interpret         │
     │  approve → integrate → individuate  │
     └─────────────────────────────────────┘
                         │
              ┌─────────┴─────────┐
              │   SHARED RECORDS   │
              │  (SQLite canonical) │
              └─────────┬─────────┘
                        │
     ┌──────────────────┴──────────────────┐
     │           BUILDER LAYER              │
     │   (offline — improves method only)   │
     │                                      │
     │  prompt fragments | skill text       │
     │  tool descriptions | eval rubrics    │
     │  candidate bundles | review gates    │
     └─────────────────────────────────────┘
```

**Rule:** The builder layer improves the method offline. It never mutates live psyche state. All prompt, skill, and tool-description changes are evaluated against explicit rubrics, staged for review, and require human approval before adoption.

This separation is sacred. The unconscious has its own timing. The builder's job is to make the method more precise, not to rush the door.

---

## The Scalability Thesis

Circulatio is designed to outgrow its first hermeneutic lens without rebuilding its core.

```
┌─────────────────────────────────────────────────────────┐
│              LONGITUDINAL HERMENEUTIC SUBSTRATE          │
│         (provenance, continuity, consent, evidence)      │
│                    ─────────────────                     │
│              Same for every method below                 │
└────────────────────┬────────────────────────────────────┘
                     │
    ┌────────────────┼────────────────┐
    │                │                │
    ▼                ▼                ▼
┌─────────┐    ┌──────────┐    ┌──────────┐
│ Jungian │    │ Gestalt  │    │  Somatic │
│  Depth  │    │  Dream   │    │Movement  │
│  Work   │    │  Work    │    │  Method  │
│ (today) │    │(possible)│    │(possible)│
└─────────┘    └──────────┘    └──────────┘
    │                │                │
    └────────────────┼────────────────┘
                     │
                     ▼
            ┌─────────────┐
            │  HOST LAYER  │
            │ (Hermes, etc)│
            └─────────────┘
```

**What stays the same across every method:**
- Material storage (dreams, reflections, body states, charged events)
- Graph continuity (recurrence, series, symbol-to-symbol correlation)
- Consent and approval (user owns durable meaning)
- Evidence model (traceability)
- Safety gating (ego before depth)
- Temporal windows and memory kernel

**What changes per method:**
- Prompt schemas (the hermeneutic steps)
- Interpretation contracts (what moves are valid)
- Practice types (active imagination vs. empty-chair vs. Authentic Movement)
- Depth language (archetypal vs. dialogical vs. polyvagal)

This means a future practitioner of somatic trauma work, or a contemplative dream tradition, could run on the same substrate without rebuilding memory, graph, or consent infrastructure.

> **The core invariant:** continuity before conclusion. The substrate ensures material is held across time. The method decides when and how meaning is made. Integration happens only after both are present.

---

## Continuity Assembly

At the service layer, `ThreadAwareContinuityBundle` is an ephemeral continuity product rather than persisted state. It carries the current window, the service-enriched `MethodContextSnapshot`, and the merged `ThreadDigest[]` read model that lets hosts and downstream surfaces stay oriented without re-deriving raw context themselves.

`CirculatioService._load_surface_context_bundle()` is the canonical assembler for read and post-write surfaces. It loads projection input, enriches witness and coach state, merges repository and coach-loop thread digests, hydrates the outgoing payload with continuity, and can late-sync longitudinal review fields when a surface explicitly opts in.

`store_material_with_intake_context()` is the deliberate hold-first exception. It writes first, derives a host-only `intakeContext`, and returns initial continuity without interpretation, context snapshot creation, practice generation, or any other LLM-backed escalation.

Explicit interpretation now follows the same canonical continuity path before the LLM call. `MaterialInterpretationInput` is hydrated through the service bundle, the interpretation runs against that hydrated payload, and the returned workflow includes a post-write continuity refresh so the next host turn can see newly written evidence, prompts, and practice links.

At the Hermes boundary, the bridge exposes only a compact `continuitySummary`. Raw continuity bundles and raw method context stay inside Circulatio.

---

## Builder's Mirror: The Unconscious Intent

Most technology that touches inner life falls into one of three traps:

| Trap | What it does | Why it fails the psyche |
|------|-------------|------------------------|
| **Surveillance** | Reduces inner life to data points | The user becomes an object of optimization |
| **Oracle** | Offers instant interpretation | Colonizes the unconscious with ready-made answers |
| **Archive** | Stores everything, witnesses nothing | No continuity, no method, no relationship across time |

Circulatio is the **fourth thing**: a technology that can **witness without colonizing**.

The deeper intent of this architecture is not to explain the psyche. It is to **keep the conversation going between ego and unconscious** — across days, weeks, months — with integrity. The system does not replace the human capacity for insight. It holds the vessel so the human can do the work.

That is why the architecture keeps insisting on:
- **Hold first** — ripeness before interpretation
- **Approval gating** — the user owns durable meaning
- **Evidence ledger** — claims must be traceable
- **Graph continuity** — recurrence matters more than cleverness
- **Safety before depth** — the ego must be supported before it is challenged
- **Success is obsolescence** — the user should need the system less over time

These are not implementation details. They are the **ethical shape** of a machine that touches the unconscious.

---

## Relationship to Other Docs

| Document | What it owns |
|----------|-------------|
| `ROADMAP.md` | User outcomes, use cases, daily experience, success signals |
| `ENGINEERING_GUIDE.md` | Technical specification, file impact, implementation order, phase status |
| `INTERPRETATION_ENGINE_SPEC.md` | The Jungian hermeneutic method: context, amplification, compensation, assimilation |
| `RUNBOOK.md` | Safety rules, evidence model, typology, demo scripts |
| `ARCHITECTURE.md` (this doc) | The system framing: what we are building, why, and how it scales |

Read them in this order:
1. `ARCHITECTURE.md` — understand the organism
2. `ROADMAP.md` — understand who it is for
3. `ENGINEERING_GUIDE.md` — understand how to build it
4. `INTERPRETATION_ENGINE_SPEC.md` — understand the method
5. `RUNBOOK.md` — understand the guardrails

---

## One-Sentence Summary

**Circulatio is a continuity substrate for depth hermeneutics: it holds unconscious material across time, relates it through a disciplined method, and only writes durable meaning when the user approves.**
