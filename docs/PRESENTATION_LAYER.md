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
- techniqueName?
- preferenceSource:
    explicit_user_preference
    host_prompted_preference
    host_default
    llm_suggested
- visualForm: orb | wave | mandala | horizon
- syncMarkers[]
```

`pattern` is the normalized breathing shape used by the runtime. `techniqueName` is the user-facing or host-requested technique label when one is explicitly wanted, including named forms such as prana-derived breathing or other custom practices. If the technique matters, the host should either carry the user's explicit preference or ask. Circulatio may suggest a fit, but the host owns whether to surface that suggestion, ask a clarifying question, or fall back to a neutral steadying pattern.

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

## Tool Calling Contract (planned)

Embodied presentation should arrive through **explicit host bridge/tool calls**, not through a generic "make media" ingress.

Hermes, OpenClaw, or another host adapter decides:
- whether a moment should become a ritual, broadcast, or cinema rendering
- whether Circulatio should write the narrative fully, minimally, or not at all
- whether the host should ask the user about breathing technique or carry forward an explicit preference

Circulatio returns a typed plan. The host renders it or asks follow-up questions when needed.

### Ritual Planning Tool (planned)

```text
circulatio.presentation.plan_ritual

input
- sourceRefs[]
- ritualIntent:
    hold_container
    guided_ritual
    breath_container
    image_return
    active_imagination_container
- narrativeMode:
    full_guided
    sparse_guided
    breath_only
    user_script
    hybrid
- authorshipMode:
    circulatio_written
    host_written
    user_supplied
    host_plus_circulatio
- requestedLenses[]:
    breath
    photo
    cinema
- scriptSeed?
- breathRequest?
- privacyClass
- safetyContext
- deliveryPolicy
```

Notes:
- `narrativeMode=breath_only` means the host wants a reduced ritual container centered on breath timing, minimal captioning, and little or no narrative script.
- `authorshipMode=host_written` or `user_supplied` means the host can pass its own words through `scriptSeed`; Circulatio should normalize structure, pacing, contraindications, and provenance rather than replacing the text blindly.
- `requestedLenses[]` expresses the host rendering options, not a backend obligation to generate all media immediately.

### Breath Request Shape (planned)

```text
breathRequest
- techniqueName?
- inhaleSeconds?
- holdSeconds?
- exhaleSeconds?
- restSeconds?
- cycles?
- preferenceSource:
    explicit_user_preference
    host_prompted_preference
    host_default
    llm_suggested
- allowClarifyingQuestion: boolean
```

Rules:
- If the user explicitly asks for a named breathing technique, preserve that request as input rather than silently normalizing it away.
- If the host needs a technique choice and none is present, the host may ask the user directly.
- If no preference is present and no question is asked, the safe fallback is a neutral steadying pattern rather than a strong named technique.

### Ritual Planning Result (planned)

```text
RitualPresentationPlan
- artifact: PresentationArtifact
- voiceScript?
- speechMarkupPlan?
- breathCycle?
- mediaSpecs[]
- interactionSpec?
- openQuestions[]?
- withheldReason?
```

The host can then:
- render the full ritual as audio + stage + captions
- reduce it to a breath-only container
- keep it as a photo-first ritual with sparse speech
- later attach cinema or generated video assets without changing the symbolic source plan

### Routing Boundary

This should follow the same explicit-routing rule used elsewhere in Circulatio:

```text
Hermes/OpenClaw/host decides presentation is needed
→ explicit bridge/tool call (`circulatio.presentation.plan_ritual`)
→ Circulatio returns typed ritual presentation plan
→ host renders, asks clarification, or defers
```

This connector is additive and explicit. It is not a hidden universal ingress, not a frontend-code generator, and not a license for the backend to decide on its own that every held note should become a ritual.

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
