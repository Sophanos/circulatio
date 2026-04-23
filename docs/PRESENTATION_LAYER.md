# Presentation Layer
## Embodied Presentation Contract (Deferred)

> **Status:** Deferred. The core backend/runtime through Phase 9 is implemented. This document captures the backend contract for a future embodied presentation layer. No `presentation.py`, TTS adapters, or web app exist in this repo yet.

Circulatio should evolve from a text interpretation backend into a **symbolic backend that emits embodied, voice-aware, breath-aware, interaction-ready presentation plans**. Hosts render them; Circulatio does not own frontend code.

The product-facing frame is **Hermes Rituals**:
- **Rituals** — guided sessions and symbolic containers
- **Broadcasts** — serialized or periodic companion voice
- **Cinema** — audiovisual renderings of the same symbolic material

These are not separate intelligence systems. They are different host renderings of shared derived context.

---

## Core Rule

Circulatio emits **typed presentation plans**. Hosts render them.

Circulatio produces:
- text
- voice script
- speech markup plan
- breath / animation spec
- association interaction spec
- delivery policy

Hosts render:
- audio
- animation
- interactive cards
- subtitles
- video compositions
- notifications
- dashboard surfaces

Current backend implication:
- Coach-facing runtime surfaces can now emit typed `resourceInvitation` payloads from `coachState`, but those invitations stay curated, provenance-bound, and host-rendered. They are not arbitrary media lookup or recommendation flows.

---

## Backend Contracts

### PresentationArtifact (planned)

```text
PresentationArtifact
- id
- userId
- sourceType:
    ritual_session
    interpretation
    practice
    rhythmic_brief
    journey_broadcast
    weekly_review
    alive_today
    threshold_invitation
    cinema_render
- text
- voiceScript?
- speechMarkup?
- mediaSpecs[]
- interactionSpec?
- deliveryPolicy
- privacyClass
- createdAt
```

### VoiceScript (planned)

```text
VoiceScript
- segments[]
- tone: steady | gentle | clear | warm | holding | neutral
- pace: normal | measured | slow
- pausePolicy
- silenceMarkers[]
- contraindications[]
```

The LLM should not emit raw SSML as canonical output. It should emit structured voice intent. Deterministic code can then render safe SSML or plain-text pause instructions.

### BreathCycleSpec (planned)

```text
BreathCycleSpec
- inhaleSeconds
- holdSeconds
- exhaleSeconds
- restSeconds
- cycles
- pattern: steadying | lengthened_exhale | box_breath | orienting
- visualForm: orb | wave | mandala | horizon
- syncMarkers[]
```

### AssociationProtocol (planned)

```text
AssociationProtocol
- protocolType:
    personal_symbol_association
    dream_image_association
    opposition_association
    numinous_image_association
    threshold_association
- stimuli[]
- captureReactionTime: boolean
- captureBodyResponse: boolean
- reproductionRound: boolean
- maxStimuli
- safetyBoundary
```

Allowed deterministic observations:
- response skipped
- response delayed
- user marked charged
- repeated association returned
- body sensation reported

Not allowed deterministically:
- this proves a complex
- this reveals trauma
- this is mother archetype
- this means repression

---

## Naming Principles

### Product-facing

Prefer:
- Hermes Rituals, rituals, broadcasts, cinema, journeycast, dream cinema, myth weather
- spoken rhythmic invitation, breath container, somatic visual guide, association circle
- active imagination container, rhythmic invitation, mythic state mirror, rhythm keeper

Avoid:
- multimodal output, content verticals, podcast feature, video mode
- wellness animation, word-association test, guided meditation product, proactive notification

### Engineering-facing

Prefer:
- `PresentationArtifact`, `VoiceScript`, `SpeechMarkupPlan`, `VoiceDeliveryPlan`
- `SomaticAnimationSpec`, `BreathCycleSpec`, `AssociationProtocol`
- `AssociationSessionRecord`, `AssociationResponseRecord`, `RhythmicPresentationPlan`
- `InvitationDeliveryPolicy`

Avoid:
- `WellnessAnimation`, `MeditationPlayer`, `WordAssociationTest`, `SelfScoreDashboard`, `TherapyMode`

---

## Roadmap Placement

Recommended sequence:
- Phase 6: Practice Engine & Adaptation Learning ✅
- Phase 7: Rhythmic Companion Runtime ✅
- Phase 7.5: Embodied Presentation Contract (this document)
- Phase 8: Teleological Individuation Layer ✅
- Phase 9: Living Myth & Integration Layer ✅
- Phase 10: Embodied Companion Runtime (future host/runtime work)

Why:
- Phase 7.5 adds typed presentation contracts without committing to any host runtime.
- Phases 8 and 9 provide deeper symbolic content.
- Phase 10 adds actual TTS adapters, local audio generation, breath sync, MCP rendering, or standalone host rendering.

---

## Final Boundary

Circulatio should evolve from:

```text
text interpretation backend
```

to:

```text
symbolic backend that emits embodied, voice-aware, breath-aware, interaction-ready presentation plans
```

but not into:
- frontend app
- notification engine
- therapy simulator
- guided meditation product
- clinical test platform

The best summary is:

> Circulatio remains backend-pure, LLM-first, consent-bound, and evidence-bound. Through Hermes Rituals, it learns when a moment should become a guided ritual, a companion broadcast, a cinematic rendering, be spoken plainly, breathed with, held in silence, or explored through association.
