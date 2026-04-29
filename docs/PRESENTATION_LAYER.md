# Presentation Layer
## Embodied Presentation Contract

> **Status:** Phase 1 plan-only ritual delivery is implemented for local/static playback. Phase 2 scheduled ritual invitations are implemented as consent-bound `ritual_invitation` rhythmic briefs with safe acceptance payloads. Phase 3 local completion sync is implemented as an idempotent persistence operation, and the Hermes Rituals completion route now falls back to the repo-local Circulatio bridge when no external completion URL is configured. The renderer emits completion manifest fields, typed top-level ritual `sections`, and provider gates for audio, image, music, and cinema/video. Kokoro speech, DiffRhythm music, and WAN image-to-video provider contracts have been live-smoke-tested through Chutes; provider-backed rendering remains renderer-owned, explicit, budget-gated, and beta-gated for music/video. Chutes Whisper remains unreliable, so fallback caption segments remain canonical; renderer-owned official OpenAI transcription is available only when `transcriptionProvider=openai`, `providerAllowlist` includes `openai`, and the server environment supplies `OPENAI_API_KEY`. Hermes Rituals keeps the existing player UI while using real audio duration, decoded waveform peaks, scrub-linked waveform progress, generated images, typed sections, recommended lenses, explicit body capture, and no-op session events for future Hermes subscription. Circulatio still does not own frontend rendering, cron, consent prompting, delivery, tool routing, or external media calls.

Circulatio should evolve from a text interpretation backend into a **symbolic backend that emits embodied, voice-aware, breath-aware, interaction-ready presentation plans**. Hosts render them; Circulatio does not own frontend code.

The product-facing frame is **Hermes Rituals**:
- **Rituals** - guided sessions and symbolic containers
- **Broadcasts** - serialized or periodic companion voice
- **Cinema** - audiovisual renderings of the same symbolic material
- **Breath surface** - simple respiratory pacing for inhale, hold, exhale, and rest
- **Meditation surface** - non-respiratory settling for coherence, attention, and symbolic containment

These are not separate intelligence systems and not separate backend tool calls. They are different host renderings of shared derived context, enabled by arguments on one presentation-planning call.

For live camera/body-reading guidance, see `EMBODIED_GUIDANCE_SURFACE.md`. That future surface is Hermes/host-owned and sensor-aware; it must stay separate from this read-only presentation planner.

---

## Layered Ritual System Map

The ritual experience is a stack of connected layers. Each layer has a narrow job so the whole path can become elastic without turning Circulatio into a router or media runtime.

```text
Layer 0  Circulatio memory/context
         dreams, body states, events, symbols, journeys, alive-today summaries

Layer 1  Hermes-agent routing
         user message + memory context -> one explicit tool choice

Layer 2  Ritual invitation
         scheduled or manual invitation only; no planning or rendering before acceptance

Layer 3  Accepted ritual plan
         circulatio_plan_ritual -> PresentationRitualPlan + allowed render surfaces

Layer 4  Renderer handoff
         mock/static by default; Chutes/OpenAI only with provider, token, budget, and gates

Layer 5  Artifact manifest
         sections, captions, narration, music, breath, meditation, image, cinema, completion fields

Layer 6  Hermes Rituals playback
         one artifact player with lenses/channels, not separate product silos

Layer 7  Completion sync
         explicit completion/reflection/body/practice feedback only; no hidden interpretation

Layer 8  Future live guidance
         guidanceSessionId + Hermes-agent companion + optional sensor/coach tracks
```

The E2E seams now have explicit tests and eval cases rather than being left to the symbolic compiler:

- Hermes-agent routing evals cover `dream + body state -> breath + music`, `only breath`, `music but no narration`, full voice/music/image, cinema, scheduled cron, acceptance, decline, and completion.
- Scheduled `ritual_invitation -> user acceptance -> circulatio_plan_ritual -> renderer -> artifact URL` is represented as an acceptance-gated path; decline stays response-only.
- Browser playback E2E covers narration, ambient music, captions, breath pacer, cinema, completion sync, and narrow breath+music artifacts.
- Journey CLI reports now expose selected tool sequence, requested surfaces, render policy, artifact URL, manifest surfaces, and browser check result.
- Whisper through Chutes remains unresolved; fallback captions are canonical and official OpenAI transcription is optional provider-backed caption refinement.

Hermes-agent may decide to deploy only the surfaces the user/context calls for. Examples:

```text
settle the body now      -> breath + optional sparse captions, no narration, no music
spoken meditation        -> audio at slow speed + captions + meditation field
breath with ambient bed  -> breath + music, no narration unless explicitly useful
dream integration ritual -> audio + captions + breath/meditation + optional music/image
cinematic artifact       -> image/cinema only when explicitly requested and beta gates pass
```

`text` remains plan metadata and fallback content. It should not force a visible text-heavy experience when Hermes chose breath, music, or meditation as the active surface.

---

## Bridge To Embodied Guidance

Embodied presentation should become the stable base that live body guidance can attach to later.

Implemented now in the presentation layer:
- artifact playback is timeline-aware through typed manifest sections, captions, current time, and completion state;
- `deriveRitualExperienceFrame` derives phase, active section, recommended lens, effective lens, available tracks, body prompt mode, and allowed explicit writes;
- manual lens switching remains available while section `preferredLens` supplies the default foreground surface;
- captions attach to sections by time overlap but no longer define canonical structure when sections are present;
- completion capture is available at closing/completion as an explicit user action through the Body lens or rail, including no-note completion, body state, literal words, and practice feedback;
- host-side ritual session events exist as a local no-op contract for future Hermes subscription;
- artifact completion remains idempotent and separate from practice, active imagination, and camera telemetry.

Implemented as the first embodied-guidance bridge:
- `/live/{guidanceSessionId}` opens a no-camera-first guidance shell attached to an artifact context;
- the shell supports breath, meditation, image, movement, and companion-cue focus modes;
- camera preflight is explicit and camera permission is requested only after user action;
- the companion remains a bounded track inside the live shell.

Do later in the embodied guidance surface:
- add camera/body signals as a sensor track;
- add reference-video comparison as a media track extension;
- attach production Hermes-agent live coaching to `guidanceSessionId`;
- use Coach OS `coachState` for live cue selection;
- persist only explicit body states, practice outcomes, reflections, or active imagination material.

The clean connection is:

```text
PresentationArtifact
-> timeline/media/lens orchestration
-> optional body response at closing
-> optional launch into guidanceSessionId
-> Embodied Guidance adds sensor + coach tracks
```

The ritual planner must not know about webcam frames, pose landmarks, live coaching, or training loops. It should only produce stable presentation sections and safe artifact metadata that a host can later use as context.

Current gap: the connected playback model is implemented in the Hermes Rituals web app and renderer manifest path, but production host orchestration for Hermes-agent subscription is not wired yet. The event contract is intentionally local/no-op until the guidance layer has a consentful `guidanceSessionId` and explicit write tools.

---

## Ownership Boundary

### Circulatio owns

- Durable individuation records
- Source context derivation
- Typed ritual plans
- Ritual invitation domain records
- Completion domain records
- Evidence-backed synthesis and interpretation when explicitly requested
- Practice, review, body-state, goal, symbol, and pattern persistence

### Hermes owns

- Natural-language intent recognition
- Consent checks and consent UX
- Cron and proactive scheduling
- Tool selection and routing
- Manual acceptance of invitations
- Delivery surfaces and notification timing
- Returning artifact URLs to the user

### Renderer owns

- Provider calls
- Provider cache
- Rendering manifests
- Static artifacts
- Fallback captions
- Budget gates
- Raw-material provider guards
- Video and music provider gates

### Frontend owns

- Artifact playback
- Completion capture
- Completion route validation before host forwarding
- Stable completion IDs
- User-authored reflection submission
- Explicit practice feedback UI

Circulatio is the backend symbolic contract. Hermes decides when the contract should be invoked. The renderer turns a plan into files. The frontend plays the files and captures user action.

---

## Core Rules

Circulatio emits **typed presentation plans**. Hosts render them.

Circulatio produces:
- text
- voice script
- speech markup plan
- breath, meditation, and animation specs
- association interaction specs
- delivery policy
- source references
- ritual invitation summaries
- ritual completion events

Hosts and renderers produce:
- audio
- animation
- interactive cards
- subtitles
- video compositions
- breath pacers
- meditation fields
- notifications
- dashboard surfaces
- artifact URLs

Hard boundaries:
- No scheduled planning.
- No scheduled rendering.
- No raw material text to external providers.
- No hidden interpretation during storage, planning, rendering, acceptance, or completion.
- No automatic practice router beyond the minimal safety fallback floor.
- No video by default.
- No music by default.
- No provider-backed render path without explicit provider, budget, and product gates.

Current backend implication:
- Coach-facing runtime surfaces can emit typed `resourceInvitation` payloads from `coachState`, but those invitations stay curated, provenance-bound, and host-rendered. They are not arbitrary media lookup or recommendation flows.
- Ritual planning is a read-only presentation compiler over existing Circulatio surfaces. It creates no material, no interpretation run, no weekly review record, no practice session, and no media blob.
- Weekly scheduled ritual invitations are proactive briefs. They are not ritual plans and not artifact render requests.

---

## Phase 1 Local Artifact Flow

```text
Hermes chat/tool call
-> circulatio_plan_ritual
-> plugin normalizes requestedSurfaces
-> circulatio.presentation.plan_ritual
-> PresentationRitualPlan JSON
-> plugin persists artifacts/rituals/plans/{planId}.json
-> plugin invokes scripts/render_ritual_artifact.py --mock-providers --dry-run --public-base /artifacts/{artifactId}
-> apps/hermes-rituals-web/public/artifacts/{artifactId}/manifest.json
-> plugin returns http://localhost:3000/artifacts/{artifactId}
-> optional local browser open
```

This is a local host handoff, not Circulatio core persistence and not provider-backed rendering. The plugin writes local handoff files and static artifacts for development; Circulatio core still only compiles the typed plan.

Phase 1 enabled surfaces are text, `voiceScript`-as-plan, captions, breath, and meditation. Audio is mock/placeholder by default. Chutes provider-backed speech, image, music, and video are available only when the renderer is called with:
- an explicit `--provider-profile chutes_*`
- a positive `--max-cost-usd`
- an API token in `CHUTES_API_TOKEN` or the configured token env var
- a plan that does not disable external providers
- a renderer-side product gate that allows the requested surface

Caption transcription is separate from speech synthesis. Fallback captions from `voiceScript.segments` are always valid. Official OpenAI transcription may refine timed captions only when `transcriptionProvider=openai`, `providerAllowlist` contains `openai`, and the configured key env var, normally `OPENAI_API_KEY`, is present in the process environment or ignored repo-local `.env`. Literal API keys must never be placed in render policies, manifests, plans, eval data, or logs.

Circulatio still emits plans only. It does not call Chutes or OpenAI, does not store media blobs, and does not manage artifact cache.

### Stabilization notes

These constraints remain active across the local artifact flow:

1. Completion UI and routes record only explicit completion, body-state, reflection, or practice-feedback payloads; they must not imply interpretation.
2. Fallback captions must remain first-class artifact output.
3. Music and video must remain behind stricter product gates.
4. OpenAI transcription is optional and failure-tolerant; it must never block artifact validity.
5. Implementation statuses in this document and linked docs must stay current.

### Hermes-Controlled Photo + Podcast Artifact Flow

Status: initial local handoff implementation on top of the existing Phase 1 artifact flow. This is a targeted integration, not a Circulatio provider refactor. Circulatio still emits a read-only `PresentationRitualPlan`; Hermes/plugin carries provider intent and local handoff policy; the renderer owns Chutes calls; Hermes Rituals loads the resulting manifest at `/artifacts/{artifactId}`.

Target behavior:

```text
Hermes user intent
-> circulatio_plan_ritual
-> plan with audio + captions + symbolic image surfaces
-> handoff persists plan
-> handoff invokes renderer with Chutes flags only when strict gates pass
-> renderer calls Kokoro speech and Z-Image; captions use fallback segments or optional OpenAI transcription when gated
-> renderer writes manifest.json, captions.vtt, audio, and image assets
-> handoff returns artifactUrl + artifact metadata + warnings
-> Hermes Rituals plays generated audio and displays image/captions
```

The first pass stays on `/artifacts/{artifactId}`. The `/broadcasts/{artifactId}` route remains mock-artifact based and should not be used for local manifest playback until it learns to load manifests.

Hermes request shape for this flow:

```ts
{
  ritualIntent: "journey_broadcast" | "weekly_integration",
  narrativeMode: "full_guided" | "sparse_guided",
  requestedSurfaces: {
    audio: { enabled: true, tone: "steady", pace: "measured" },
    captions: { enabled: true, format: "webvtt" },
    image: {
      enabled: true,
      styleIntent: "symbolic_non_literal",
      allowExternalGeneration: true
    },
    breath: { enabled: false },
    meditation: { enabled: false },
    cinema: { enabled: false }
  },
  renderPolicy: {
    mode: "render_static",
    defaultDurationSeconds: 150,
    maxDurationSeconds: 180,
    externalProvidersAllowed: true,
    videoAllowed: false,
    providerAllowlist: ["mock", "chutes", "openai"],
    maxCost: { currency: "USD", amount: 0.05 },

    // Handoff-only plugin policy for this phase.
    providerProfile: "chutes_all",
    surfaces: ["audio", "captions", "image"],
    transcribeCaptions: true,
    transcriptionProvider: "openai",
    openaiApiKeyEnv: "OPENAI_API_KEY",
    openaiTranscriptionModel: "whisper-1",
    openaiTranscriptionResponseFormat: "verbose_json",
    requestTimeoutSeconds: 180,

    sourceDataPolicy: {
      allowRawMaterialTextInPlan: false,
      allowRawMaterialTextToProviders: false,
      providerPromptPolicy: "derived_user_facing_only"
    }
  }
}
```

`providerProfile`, `surfaces`, `transcribeCaptions`, `transcriptionProvider`, `openaiApiKeyEnv`, `openaiTranscriptionModel`, `openaiTranscriptionResponseFormat`, `requestTimeoutSeconds`, and token-env names are handoff-only plugin fields, not formal Circulatio domain fields. `circulatio_plan_ritual` passes the original `renderPolicy` into `HermesRitualArtifactHandoff`; Circulatio core remains provider-agnostic.

Internal handoff extraction uses this shape:

```text
HermesHandoffRenderOptions
- providerProfile
- surfaces
- maxCostUsd
- transcribeCaptions
- requestTimeoutSeconds
- chutesTokenEnv
- transcriptionProvider
- openaiApiKeyEnv
- openaiTranscriptionModel
- openaiTranscriptionResponseFormat
- providerBacked
- warnings
```

Provider-backed rendering is allowed only when all gates pass:

1. `renderPolicy.mode == "render_static"`.
2. `externalProvidersAllowed == true`.
3. `providerAllowlist` includes `chutes`.
4. `providerProfile` starts with `chutes_`.
5. `maxCostUsd` or `maxCost.amount` is greater than zero.
6. `CHUTES_API_TOKEN`, or the configured token env var, exists before renderer launch.
7. Requested surfaces intersect `result.renderRequest.allowedSurfaces`.
8. Selected surfaces are limited to `audio`, `captions`, and `image`.
9. The plan allows external providers and includes `no_raw_material_to_external_provider`.
10. If `transcriptionProvider=openai`, `providerAllowlist` must include `openai`, the configured `openaiApiKeyEnv` must exist, and failure must fall back to plan-derived captions.

Safe surface selection:

```text
requested = renderPolicy.surfaces if present else ["audio", "captions", "image"]
allowed = result.renderRequest.allowedSurfaces
selected = requested intersection allowed intersection {"audio", "captions", "image"}
```

Even with `providerProfile == "chutes_all"`, the handoff passes explicit `--surfaces audio,captions,image`. It must not rely on profile defaults for product safety. The current safe `chutes_all` bundle is audio, captions, and image; music and cinema stay separate beta surfaces and require explicit beta flags. The handoff never passes `--allow-beta-music` or `--allow-beta-video` for this flow.

Default renderer command remains:

```text
scripts/render_ritual_artifact.py \
  --plan {planPath} \
  --out {stagingDir} \
  --mock-providers \
  --dry-run \
  --public-base /artifacts/{artifactId}
```

Provider-backed command becomes:

```text
scripts/render_ritual_artifact.py \
  --plan {planPath} \
  --out {stagingDir} \
  --provider-profile chutes_all \
  --surfaces audio,captions,image \
  --transcribe-captions \
  --transcription-provider openai \
  --openai-api-key-env OPENAI_API_KEY \
  --openai-transcription-model whisper-1 \
  --openai-transcription-response-format verbose_json \
  --max-cost-usd {positiveBudget} \
  --request-timeout-seconds {timeout} \
  --public-base /artifacts/{artifactId}
```

Provider safety and privacy rules:

- Kokoro receives only derived `voiceScript` text.
- Z-Image receives only `visualPromptPlan.image.prompt` when `providerPromptPolicy == "sanitized_visual_only"`.
- Source refs, raw material text, graph records, dream bodies, and chat history must never be sent to Chutes or OpenAI.
- OpenAI receives only the rendered narration audio for transcription, after the plan has already enforced the no-raw-material provider policy.
- `externalProvidersAllowed=false` blocks Chutes and OpenAI transcription.
- Missing `no_raw_material_to_external_provider` blocks Chutes.
- Video and music remain disabled for this flow.
- Provider warnings are returned to Hermes in `artifact.renderWarnings` and merged into response warnings.

For a successful Chutes-backed photo + podcast artifact, `manifest.json` should contain Chutes audio, WebVTT caption tracks plus timed segments, and a generated image:

```ts
{
  schemaVersion: "hermes_ritual_artifact.v1",
  artifactId: "ritual_artifact_...",
  planId: "ritual_plan_...",
  durationMs: 120000 | 150000 | 180000,
  surfaces: {
    text: { body: string },
    audio: {
      src: "/artifacts/{artifactId}/audio.wav" | "/artifacts/{artifactId}/audio.mp3",
      mimeType: "audio/wav" | "audio/mpeg",
      durationMs: null,
      provider: "chutes",
      model: "chutes-kokoro",
      voiceId: "af_heart" | "af_nicole" | string,
      speed: 0.82 | 0.9 | 1.0,
      checksum: string
    },
    captions: {
      tracks: [{ src: "/artifacts/{artifactId}/captions.vtt", format: "webvtt" }],
      segments: [{ id: string, startMs: number, endMs: number, text: string }]
    },
    image: {
      enabled: true,
      src: "/artifacts/{artifactId}/image.png",
      mimeType: "image/png",
      provider: "chutes",
      model: "chutes-z-image-turbo",
      checksum: string
    }
  },
  render: {
    rendererVersion: "ritual-renderer.v1",
    mode: "render_static",
    providers: ["mock", "chutes", "openai"],
    warnings: []
  }
}
```

Degraded states remain valid when the manifest and captions are valid: unresolved or failed Chutes/OpenAI transcription keeps fallback captions; audio failure can leave placeholder audio plus warnings; image failure can leave image disabled plus warnings; missing token, zero budget, or disabled providers fall back to mock/dry-run-compatible output.

Existing manifests are checked for suitability before reuse. A mock manifest can satisfy a mock request, but it cannot satisfy a Chutes audio request unless `surfaces.audio.src` exists and `provider == "chutes"`; it cannot satisfy a Chutes image request unless image is enabled with a Chutes `src`; captions may be provider or fallback captions as long as segments or `captions.vtt` exist.

Provider-backed subprocess timeout is larger than mock rendering: at least 300 seconds and otherwise `max(config.renderer_timeout_seconds, requestTimeoutSeconds * 3 + 30)`. Staging directories are cleaned up on timeout, renderer error, or manifest validation failure, and the final artifact directory is replaced only after the staging manifest validates.

Frontend playback rules:

- `BroadcastDeck`, `TranscriptCard`, and `RitualPlayer` use `artifact.audioUrl` when present.
- Silent WAV object URLs remain fallback-only for mock artifacts.
- Generated blob URLs are revoked; public artifact URLs are not revoked.
- `RitualPlayer` preserves the existing dark/minimal player chrome while decoding real audio into waveform peaks underneath it.
- The scrub bar, audio element, decoded waveform progress, captions, and section clock share the same media time.
- Real audio metadata can arrive after first render; browser tests should wait for slider duration to switch from planned manifest duration to actual audio duration before asserting scrub behavior.
- Image-backed artifacts enter the Photo lens by default unless a cinema video is present.
- Caption timing from fallback segments, or a future working transcription provider, drives `CaptionStack`, section rows, transcript grouping, and ElevenLabs-style character alignment.
- `TranscriptCard` uses caption-derived character timing where segments exist; exact word-level alignment remains a future provider surface.

Script-duration follow-up: the current plan duration can target 120-180 seconds, but actual `voiceScript` text may be shorter. If exact podcast length becomes product-critical, add a podcast/broadcast profile in `CirculatioCore._presentation_voice_segments()` that accepts `target_seconds`, estimates a measured-pace word budget of roughly 240-280 words for two minutes or 330-390 words for three minutes, and emits structured segments such as opening, source thread, symbolic image, integration, and closing.

Tests for this flow should cover:

- Planning with audio/captions/image allows those render surfaces and keeps image prompts sanitized.
- Handoff defaults to mock/dry-run.
- Handoff builds Chutes argv only when mode, external provider, allowlist, profile, budget, token, plan policy, and surface gates pass.
- Handoff always passes explicit `--surfaces audio,captions,image` for this flow.
- Existing mock manifests do not block Chutes rerender when Chutes is actually requested.
- Renderer fallback captions remain valid when transcription is unavailable or unresolved.
- Explicit `--surfaces audio,captions,image` with `chutes_all` does not render music or cinema.
- Frontend components play `artifact.audioUrl` before silent fallback.

---

## Phase 2 Scheduled Ritual Invitations

Phase 2 adds **weekly scheduled ritual invitations only**. Cron may create a consent-bound `ritual_invitation` rhythmic brief, but must not call `plan_ritual` and must not render media.

### New proactive brief type

Use a dedicated proactive brief type:

```text
ritual_invitation
```

Do not overload:
- `weekly`
- `resource_invitation`
- `practice`
- `alive_today`

The brief carries a typed `RitualInvitationSummary`. Hermes receives enough structured data to present an invitation and later resolve acceptance, without Circulatio producing a ritual plan prematurely.

### Scheduled flow

```text
Hermes cron
-> check proactive_briefing consent
-> circulatio_generate_rhythmic_briefs(source="scheduled")
-> ProactiveEngine emits ritual_invitation brief
-> Hermes delivers invitation only
```

Cron explicitly must not call:
- `circulatio.presentation.plan_ritual`
- `scripts/render_ritual_artifact.py`
- any provider-backed render path
- any frontend artifact completion path

### Manual acceptance flow

```text
User accepts
-> Hermes resolves brief
-> Hermes calls circulatio.presentation.plan_ritual
-> Circulatio returns PresentationRitualPlan
-> Hermes may run renderer manually
-> Hermes returns /artifacts/{artifactId}
```

User acceptance is the boundary between invitation and planning. Accepted planning is still read-only. It creates no material, no interpretation run, no weekly review, and no practice session.

### Invitation summary contract

```text
RitualInvitationSummary
- invitationId
- userId
- sourceRef
- title
- summary
- suggestedIntent
- suggestedSurfaces
- privacyClass
- cadence
- generatedAt
- expiresAt?
- acceptancePayload
```

`acceptancePayload` is for Hermes routing. It should contain enough stable references to call `circulatio.presentation.plan_ritual` after acceptance, not enough data to render media directly.

### Plan draft contract

```text
RitualInvitationPlanDraft
- sourceRefs[]
- ritualIntent
- narrativeMode
- requestedSurfaces
- privacyClass
- safetyContext
- deliveryPolicy
- defaultRenderPolicy
```

The draft is not a plan. It is a typed suggestion for a later accepted plan request.

### Phase 2 acceptance criteria

- Scheduled cron creates only a `ritual_invitation` brief.
- `proactive_briefing` consent is required.
- No scheduled planning or rendering occurs.
- Dedupe, cooldown, cadence, and scheduled max reuse existing rhythmic brief machinery.
- User acceptance is required before `circulatio.presentation.plan_ritual`.
- Accepted planning creates no material, interpretation run, weekly review, or practice session.
- Default accepted render policy disables external providers and video.
- Source references survive through the brief and accepted plan path.
- Raw material text is never exposed in proactive brief payloads.

---

## Phase 3 Completion Sync And Provider Hardening

Phase 3 adds **idempotent completion sync** and hardens provider rendering. Completion is an explicit user action or playback event. It is not interpretation. The local backend/plugin route and frontend POST handler shape are implemented. Local development needs no external completion endpoint; production Hermes or another host may still override forwarding with `HERMES_RITUAL_COMPLETION_URL`.

### Completion flow

```text
Frontend POST /api/artifacts/{artifactId}/complete
-> validates manifest + idempotency key
-> if HERMES_RITUAL_COMPLETION_URL is set, POSTs normalized payload to that host
-> otherwise spawns scripts/record_ritual_completion.py in the repo-local Python environment
-> plugin dispatches circulatio_record_ritual_completion
-> Circulatio stores event idempotently
-> optional literal reflection material
-> optional explicit practice feedback
-> no interpretation run
```

The completion route must require either:
- `Idempotency-Key` header
- `completionId` in the request body

Replays with the same key and same normalized payload return the existing event. The same key with a different normalized payload is a validation error.

### Completion event contract

```text
RitualCompletionEvent
- id
- userId
- artifactId
- planId?
- sourceRefs[]
- idempotencyKey
- completedAt
- durationMs?
- playbackState:
    completed
    partial
    abandoned
- completedSections[]
- reflectionMaterialId?
- practiceFeedbackId?
- metadata
- createdAt
```

`reflectionMaterialId` is only present when the user explicitly authors a reflection. That reflection is stored literally. Recording completion must not trigger interpretation, symbol extraction, material classification, or practice suggestion.

`practiceFeedbackId` is only present when the user explicitly provides feedback about a practice. It is not inferred from playback.

### Completion input contract

```text
RecordRitualCompletionInput
- userId
- artifactId
- manifestVersion
- idempotencyKey
- completedAt
- playbackState
- durationMs?
- completedSections[]
- reflectionText?
- practiceFeedback?
- clientMetadata?
```

### Local completion adapter

The Hermes Rituals web app should work out of the box for local artifacts. If `HERMES_RITUAL_COMPLETION_URL` is unset, `apps/hermes-rituals-web/lib/hermes-completion-adapter.ts` invokes `scripts/record_ritual_completion.py` through local Python. That bridge calls only the plugin completion tool and must not call interpretation.

Operators and host agents can change the handoff with environment variables:
- `HERMES_RITUAL_COMPLETION_URL` - external POST receiver for Hermes or another host-owned adapter
- `CIRCULATIO_REPO_ROOT` - repo root used by the local web adapter
- `CIRCULATIO_PYTHON` - Python executable for the local bridge
- `CIRCULATIO_RITUAL_COMPLETION_SCRIPT` - alternate completion bridge script
- `CIRCULATIO_RITUAL_COMPLETION_TIMEOUT_MS` - local bridge timeout
- `CIRCULATIO_PROFILE` or `HERMES_PROFILE` - profile used for local completion storage

Users should not need any of these for the default local Hermes Rituals flow.

### Idempotency contract

Repository storage must be keyed by:

```text
(userId, idempotencyKey)
```

Rules:
- First valid request creates a completion event.
- Same key plus same normalized payload returns the existing event.
- Same key plus different normalized payload fails validation.
- Replays create no duplicate reflection material and no duplicate practice feedback.
- Missing idempotency key fails before Hermes dispatch.

This follows the general idempotency-key pattern for retry-safe POST side effects.

### Provider hardening

Provider hardening remains renderer-side:
- Chutes speech and image stay opt-in and budget-gated.
- The current Whisper/Chutes caption path is unresolved and must not be required for a passing ritual artifact.
- Fallback captions from `voiceScript.segments` stay first-class.
- Fallback captions must be valid timed cue files.
- Cinema/video is an opt-in manifest surface on `/artifacts/{artifactId}`, not a separate
  generated artifact route.
- Music and video remain explicit beta/developer surfaces.
- Chutes video requires external providers, the Chutes allowlist, explicit `cinema`/`video`
  render surfaces, `videoAllowed`, `allowBetaVideo`, positive budget, token availability, a
  plan-allowed cinema surface, and a sanitized storyboard prompt.
- Raw material text never goes to external providers.
- Video is never enabled by default.
- WAN image-to-video failure degrades to the photo/audio/caption artifact. Completion remains
  idempotent completion recording only; it must not trigger interpretation.

### Phase 3 acceptance criteria

- Completion POST validates artifact, manifest, payload, and idempotency.
- Completion is stored as `RitualCompletionEvent`.
- Same idempotency key plus same payload creates no duplicate side effects.
- Same idempotency key plus different payload is rejected.
- Reflection is stored literally only when user-authored.
- Practice feedback is recorded only when explicitly provided.
- No interpretation is triggered.
- Caption fallback survives missing or unresolved transcription and writes WebVTT cues.
- Music and video remain off by default.
- External providers remain opt-in, budget-gated, and renderer-owned.

---

## Backend Contracts

### PresentationArtifact

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

### VoiceScript

```text
VoiceScript
- segments[]
- tone: steady | gentle | clear | warm | holding | neutral
- pace: normal | measured | slow
- voiceId?: Kokoro voice id such as af_heart
- speed?: Kokoro speech speed, 0.1-3.0
- pausePolicy
- silenceMarkers[]
- contraindications[]
```

The LLM should not emit raw SSML as canonical output. It should emit structured voice intent.
Deterministic code can then render safe SSML, plain-text pause instructions, or provider-specific
speech settings. For meditation and breath-led rituals, Hermes should prefer slower speech
(`pace=slow` or `speed` around `0.82-0.9`) unless the user asks for a normal spoken pace.

### BreathCycleSpec

```text
BreathCycleSpec
- inhaleSeconds
- holdSeconds
- exhaleSeconds
- restSeconds
- cycles
- pattern: steadying | lengthened_exhale | box_breath | orienting
- visualForm: pacer | wave | mandala | horizon
- syncMarkers[]
```

`pattern` is the normalized breathing shape used by the runtime. `techniqueName` is the user-facing or host-requested technique label when one is explicitly wanted, including named forms such as prana-derived breathing or other custom practices. If the technique matters, the host should either carry the user's explicit preference or ask. Circulatio may suggest a fit, but the host owns whether to surface that suggestion, ask a clarifying question, or fall back to a neutral steadying pattern.

Breath tools should make the respiratory instruction legible. A default pacer can use one restrained grey ring: inhale expands, hold rests at maximum radius, exhale contracts, and rest quiets. Any vibration or edge pulse is a timing cue, not a symbolic interpretation.

### MeditationFieldSpec

```text
MeditationFieldSpec
- fieldType:
    coherence_convergence
    attention_anchor
    threshold_stillness
    image_afterglow
- durationMs
- sourceRefs[]
- macroProgressPolicy:
    session_progress
    section_progress
    untimed
- microMotion:
    still
    pulse
    convergence
    shimmer
- instructionDensity:
    none
    sparse
    phase_label
- safetyBoundary
- syncMarkers[]
```

Meditation fields are not breath instructions. They can borrow the same playback clock, but their job is containment, attention, and symbolic settling. For example, a coherence convergence field can let scattered traces slowly gather into one ring across the session while small phase-linked pulses keep the field alive.

### AssociationProtocol

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

## Tool Calling Contract

Embodied presentation should arrive through one explicit host bridge/tool call, not through a generic "make media" ingress and not through one backend tool per visual mode.

The tool call plans a ritual. Its arguments decide which surfaces are available for the host to render. Breath and meditation remain semantically distinct inside the same call:

```text
circulatio.presentation.plan_ritual

input
- sourceRefs[]
- ritualIntent:
    hold_container
    guided_ritual
    breath_container
    meditation_container
    image_return
    active_imagination_container
- narrativeMode:
    full_guided
    sparse_guided
    breath_only
    meditation_only
    user_script
    hybrid
- requestedSurfaces:
    breath:
      enabled: boolean
      request?: BreathCycleSpec
    meditation:
      enabled: boolean
      request?: MeditationFieldSpec
    photo:
      enabled: boolean
    cinema:
      enabled: boolean
    audio:
      enabled: boolean
    music:
      enabled: boolean
      allowExternalGeneration: boolean
      styleIntent?: dream_integration | body_settling | threshold_crossing | quiet_reflection | mythic_motion
      musicDurationSeconds?: integer
- privacyClass
- safetyContext
- deliveryPolicy
```

`requestedSurfaces.breath.request` asks for respiratory pacing. `requestedSurfaces.meditation.request` asks for a settling field or attention container. The host may render both in one ritual from the same tool response, but the tool call keeps them semantically separate so a meditation visual does not silently become a breathing instruction.

Planning is read-only. It compiles a presentation plan from existing context and explicit source references.
Generated cinema remains inside the same manifest-backed artifact route. Hosts render it as
`surfaces.cinema` and keep the ordinary ritual completion endpoint.

Chutes cinema rendering requires all of:
- `renderPolicy.mode = render_static`
- `renderPolicy.externalProvidersAllowed = true`
- `renderPolicy.providerAllowlist` containing `chutes`
- `renderPolicy.surfaces` containing `cinema` or `video`
- `renderPolicy.videoAllowed = true`
- `renderPolicy.allowBetaVideo = true`
- positive budget and a configured Chutes token
- `renderRequest.allowedSurfaces` containing `cinema`
- `visualPromptPlan.cinema.providerPromptPolicy = sanitized_visual_only`
- a non-empty sanitized storyboard prompt

Chutes DiffRhythm music rendering requires all of:
- `requestedSurfaces.music.enabled = true`
- `requestedSurfaces.music.allowExternalGeneration = true`
- a host-selected `requestedSurfaces.music.styleIntent` when Hermes memory has enough signal
- `renderPolicy.mode = render_static`
- `renderPolicy.externalProvidersAllowed = true`
- `renderPolicy.providerAllowlist` containing `chutes`
- `renderPolicy.providerProfile = chutes_music` or `chutes_all`
- `renderPolicy.surfaces` containing `music`
- `renderPolicy.allowBetaMusic = true`
- positive budget and a configured Chutes token
- `renderRequest.allowedSurfaces` containing `music`
- `plan.music.providerPromptPolicy = derived_user_facing_only`
- a non-empty `plan.music.stylePrompt`

The style prompt is derived from approved/user-facing Circulatio summaries, active themes,
recurring symbols, and Hermes-selected style intent. It must not contain raw dream text,
private notes, or unapproved material. The renderer sends that value to DiffRhythm as
`style_prompt`; narration audio remains `surfaces.audio`, and generated music remains the
separate `surfaces.music` ambient bed.

Hermes may also request narrow ritual plans. If the user asks for only breath and music,
the host should explicitly set `requestedSurfaces.breath.enabled=true`,
`requestedSurfaces.music.enabled=true`, and set unrelated surfaces such as captions,
meditation, audio, image, and cinema to `enabled=false`. `text` remains plan metadata even
when no spoken or visual text surface is rendered.

Completion sync uses a separate operation:

```text
circulatio.presentation.record_ritual_completion

input
- RecordRitualCompletionInput

output
- RitualCompletionEvent
- replayed: boolean
```

Recording completion is a persistence action only. It must not call the interpretation engine.

---

## Hermes And Plugin Contract

Phase 2 Hermes/plugin impact:
- `agent_bridge_contracts.py` adds the `ritual_invitation` proactive payload shape.
- `command_router.py` may add optional `/circulation ritual accept` dispatch.
- `agent_bridge.py` routes accepted invitation planning only after manual acceptance.
- `tools.py`, `schemas.py`, and `plugin.yaml` expose only the necessary accepted planning path.
- `skills/circulation/SKILL.md` strengthens the scheduled invitation-only rule.

Phase 3 Hermes/plugin impact:
- `agent_bridge_contracts.py` adds `circulatio.presentation.record_ritual_completion`.
- `command_router.py` adds completion dispatch.
- `agent_bridge.py` routes the completion operation.
- `tools.py`, `schemas.py`, and `plugin.yaml` add a completion tool if plugin dispatch is used.
- Completion dispatch must preserve the no-interpretation rule.

Hermes must enforce consent before scheduled invitation delivery. Circulatio can validate inputs and privacy classes, but Hermes owns consent UX and delivery timing.

---

## Renderer Contract

Renderer-owned responsibilities:
- Extend artifact manifest `interaction` with completion flags.
- Populate stable completion fields for frontend use.
- Preserve fallback captions when transcription is unavailable or unresolved.
- Keep provider calls isolated under provider adapters.
- Keep provider caches renderer-owned.
- Enforce budget gates before provider calls.
- Enforce raw prompt guards before provider calls.
- Keep video behind explicit beta/developer gates.
- Keep music behind explicit beta/developer gates and require a non-empty
  approved-summary-derived DiffRhythm style prompt.
- Keep default weekly ritual artifacts text, breath, meditation, and captions only.

`contracts.py` should model completion fields in the manifest. `renderer.py` should fill them. `providers/chutes.py` should remain provider-specific and should not leak provider assumptions into Circulatio domain types.

`scripts/render_ritual_artifact.py` should remain a manual renderer entrypoint unless a later host job system explicitly owns scheduling. Phase 2 cron must not call it.

`scripts/evaluate_journey_cli.py --ritual-eval` is the local long-form audit path for this contract.
It simulates daily and weekly ritual journeys, verifies invitation and provider gates, renders
accepted artifacts, records completion, and writes artifact/browser reports. It is not the proactive
runtime and must not weaken the cron rule above.

---

## Frontend Contract

Frontend Phase 3 work:
- `artifact-contract.ts` adds completion fields to `RitualArtifactManifest.interaction`.
- `mock-artifacts.ts` updates the weekly fixture.
- `app/artifacts/[artifactId]/page.tsx` extracts manifest loading for reuse.
- `app/api/artifacts/[artifactId]/complete/route.ts` adds a POST route.
- Ritual components add completion submit UI and stable completion ID handling.

The completion route should validate:
- artifact exists
- manifest exists
- route `artifactId` matches manifest artifact ID
- request has `Idempotency-Key` or `completionId`
- payload matches the manifest's completion contract
- local completion adapter can be resolved, or `HERMES_RITUAL_COMPLETION_URL` is set for external host forwarding

Next.js App Router Route Handlers are the intended shape for `app/api/.../route.ts` POST handling. The route should normalize payload before forwarding to the configured adapter so Circulatio receives stable idempotency semantics.

---

## Source Context And Privacy

Ritual planning and invitation generation must use source references, titles, summaries, tags, and derived context. They must not expose raw material text in:
- context snapshots
- graph nodes
- proactive brief payloads
- provider prompts
- artifact manifests
- renderer cache keys

When user-authored reflection is submitted on completion, it is stored literally because the user explicitly authored it for that purpose. That storage still does not trigger interpretation.

---

## Experience Stories

- A user says, "I only need help breathing for a minute." The host calls `plan_ritual` with `narrativeMode=breath_only` and `requestedSurfaces.breath.enabled=true`, then renders a minimal pacer with inhale, hold, exhale, and rest labels.
- A user brings a charged dream image but does not want interpretation yet. The host calls the same planner with `requestedSurfaces.meditation.enabled=true` and renders a coherence field that settles attention without turning the image into advice.
- A user receives a weekly invitation. Hermes delivers a `ritual_invitation` brief only. If the user accepts, Hermes calls `plan_ritual`; otherwise no plan or artifact exists.
- A user completes a ritual and adds a sentence about what happened. The frontend posts completion with an idempotency key. Circulatio stores a completion event and literal reflection material, then stops.
- A provider caption call fails. The renderer emits fallback WebVTT captions from `voiceScript.segments` and keeps the artifact playable.
- A user already has a breathing practice and names it directly. The host carries that explicit preference in `requestedSurfaces.breath.request` instead of letting Circulatio infer a technique from keywords.
- A user wants the image, music, and breath all present. The host enables multiple `requestedSurfaces` in one tool call, but the renderer still requires explicit provider, budget, and beta gates before producing non-default media.

---

## Implementation Impact

### Docs

- `docs/PRESENTATION_LAYER.md`: this Phase 2/3 architecture plan.
- `docs/ROADMAP.md`: add Phase 7.6/7.7 entries for ritual invitation and completion/provider hardening.
- `docs/ENGINEERING_GUIDE.md`: document cron, acceptance, completion, and provider boundaries.
- `README.md`: add manual plan -> render -> artifact URL path.

### Backend

- `src/circulatio/domain/presentation.py`: add `RitualInvitationSummary`, `RitualInvitationPlanDraft`, and `RitualCompletionEvent`.
- `src/circulatio/domain/proactive.py`: add `ritual_invitation`; add optional `ritualInvitation`.
- `src/circulatio/application/workflow_types.py`: add `RecordRitualCompletionInput` and result type.
- `src/circulatio/application/circulatio_service.py`: add `record_ritual_completion`; preserve read-only `plan_ritual`.
- `src/circulatio/core/proactive_engine.py`: generate consent-bound weekly ritual invitation seeds.
- `src/circulatio/core/circulatio_core.py`: preserve proactive brief source refs; keep accepted plan read-only.
- Repository layer: add idempotent completion-event storage keyed by `(userId, idempotencyKey)`.

### Hermes/plugin

- `agent_bridge_contracts.py`: add `circulatio.presentation.record_ritual_completion`.
- `command_router.py`: add completion dispatcher; optional `/circulation ritual accept`.
- `agent_bridge.py`: route new completion operation.
- `tools.py`, `schemas.py`, `plugin.yaml`: add completion tool if plugin dispatch is used.
- `commands.py`: add ritual accept command only if needed.
- `skills/circulation/SKILL.md`: strengthen scheduled invitation-only and completion no-interpretation rules.

### Renderer

- `contracts.py`: extend manifest `interaction` with completion flags.
- `renderer.py`: populate completion fields, harden provider gates, preserve fallback captions when transcription is unavailable or unresolved.
- `cli.py`: add cache flags only if renderer-owned cache is implemented.
- `providers/chutes.py`: keep provider isolation; add stricter errors only as needed.
- `scripts/render_ritual_artifact.py`: no functional change expected.

### Frontend

- `artifact-contract.ts`: add completion fields to `RitualArtifactManifest.interaction`.
- `mock-artifacts.ts`: update weekly fixture.
- `app/artifacts/[artifactId]/page.tsx`: extract manifest loader for reuse.
- `app/api/artifacts/[artifactId]/complete/route.ts`: add POST route.
- `components/**`: add completion submit UI and stable completion ID.

---

## Required Tests And Evals

### Phase 2 tests

- `tests/test_rhythmic_runtime.py`: consent, dedupe, cooldown, scheduled max, ritual invitation seed.
- `tests/test_presentation_plan_service.py`: accepted proactive brief source ref and no-write assertions.
- `tests/test_hermes_bridge_plugin.py`: ritual invitation payload and optional accept command.
- `tests/test_hermes_host_smoke.py`: scheduled invitation smoke and accepted plan smoke.

### Phase 2 evals

- No scheduled planning.
- No scheduled rendering.
- Consent required.
- Acceptance required.
- No hidden interpretation.

### Phase 3 tests

- Backend completion service tests for event storage, replay, conflict, reflection-only storage, and no interpretation.
- Hermes bridge/plugin tests for completion tool dispatch and schema.
- Frontend route tests for valid POST, missing manifest, ID mismatch, missing idempotency, and adapter not configured.
- Renderer tests for fallback captions without a working transcription provider, budget gate, raw prompt guard, video gate, and default weekly no music/video.

### Phase 3 evals

- Completion does not interpret.
- Completion creates no hidden memory proposals.
- Raw-text boundary holds.
- Caption fallback survives provider failure.
- Music and video stay off by default.

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
- `SomaticAnimationSpec`, `BreathCycleSpec`, `MeditationFieldSpec`, `AssociationProtocol`
- `AssociationSessionRecord`, `AssociationResponseRecord`, `RhythmicPresentationPlan`
- `RitualInvitationSummary`, `RitualInvitationPlanDraft`, `RitualCompletionEvent`
- `InvitationDeliveryPolicy`

Avoid:
- `WellnessAnimation`, `MeditationPlayer`, `WordAssociationTest`, `SelfScoreDashboard`, `TherapyMode`

---

## Roadmap Placement

Recommended sequence:
- Phase 6: Practice Engine & Adaptation Learning - implemented
- Phase 7: Rhythmic Companion Runtime - implemented
- Phase 7.5: Embodied Presentation Contract - implemented as plan-only local artifact flow
- Phase 7.6: Scheduled Ritual Invitations - planned Phase 2
- Phase 7.7: Completion Sync And Provider Hardening - planned Phase 3
- Phase 8: Teleological Individuation Layer - implemented
- Phase 9: Living Myth & Integration Layer - implemented
- Phase 10: Embodied Companion Runtime - future host/runtime work

Why:
- Phase 7.5 adds typed presentation contracts without making Circulatio a renderer.
- Phase 7.6 adds consent-bound weekly invitations without scheduled planning or rendering.
- Phase 7.7 records completion idempotently and hardens providers without hidden interpretation.
- Phases 8 and 9 provide deeper symbolic content.
- Phase 10 adds actual host/runtime orchestration, TTS adapters, local audio generation, breath sync, MCP rendering, or standalone host rendering.

---

## External Format Grounding

- Next.js App Router Route Handlers are the expected shape for `app/api/.../route.ts` POST completion handling.
- WebVTT fallback captions should remain timed cue files generated from `voiceScript.segments`.
- Completion POSTs should use idempotency keys to avoid duplicate side effects on retry.

These are implementation constraints for the host/frontend/renderer. They do not change Circulatio ownership.

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
- provider media gateway
- cron scheduler

The best summary is:

> Circulatio remains backend-pure, LLM-first, consent-bound, evidence-bound, and host-rendered. Through Hermes Rituals, it can help a host decide when a moment should become a guided ritual, a companion broadcast, a cinematic rendering, plain speech, breath pacing, silence, or association, while keeping routing, delivery, rendering, provider calls, and completion UX outside the backend core.
