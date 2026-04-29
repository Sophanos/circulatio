import { strict as assert } from "node:assert"
import test from "node:test"

import type { RitualSection } from "../artifact-contract"
import type { RitualExperienceFrame } from "../ritual-experience"
import { ritualSessionEventDedupeKey } from "../ritual-guidance-events"
import {
  buildLocalGuidanceSession,
  guidanceFrameFromExperienceFrame,
  sanitizeRitualChatRequest,
  stableGuidanceSessionId,
  stripBlockedFields
} from "../ritual-guidance-safety"

function section(kind: RitualSection["kind"], id = `section-${kind}`): RitualSection {
  return {
    id,
    title: kind,
    startMs: 0,
    endMs: 1000,
    kind
  }
}

function internalFrame(activeSection: RitualSection | null): RitualExperienceFrame {
  return {
    phase: activeSection?.kind === "closing" ? "closing" : "ritual",
    activeSection,
    recommendedLens: "meditation",
    effectiveLens: "meditation",
    availableTracks: ["meditation"],
    bodyPromptMode: activeSection?.kind === "closing" ? "inline_hint" : "hidden",
    allowedWrites:
      activeSection?.kind === "closing"
        ? ["body_state", "reflection_text", "active_imagination_note"]
        : ["reflection_text", "active_imagination_note"]
  }
}

test("local guidance session IDs are stable for the same input", () => {
  const first = stableGuidanceSessionId({
    hostSessionId: "host-1",
    artifactId: "artifact-1",
    userId: "user-1"
  })
  const second = stableGuidanceSessionId({
    hostSessionId: "host-1",
    artifactId: "artifact-1",
    userId: "user-1"
  })
  const differentArtifact = stableGuidanceSessionId({
    hostSessionId: "host-1",
    artifactId: "artifact-2",
    userId: "user-1"
  })
  const differentUser = stableGuidanceSessionId({
    hostSessionId: "host-1",
    artifactId: "artifact-1",
    userId: "user-2"
  })

  assert.equal(first, second)
  assert.notEqual(first, differentArtifact)
  assert.notEqual(first, differentUser)
})

test("guidance frame maps reflection_text and adds practice outcome only in closing contexts", () => {
  const reflection = guidanceFrameFromExperienceFrame({
    frame: internalFrame(section("reflection")),
    currentMs: 24000,
    durationMs: 120000,
    lens: "meditation",
    isPlaying: false,
    playbackCompleted: false,
    completionStatus: "idle"
  })
  assert.deepEqual(reflection.allowedWrites, ["reflection", "active_imagination_note"])
  assert.equal(reflection.phase, "ritual")
  assert.deepEqual(reflection.availableTracks, ["meditation"])
  assert.equal(reflection.playback.state, "paused")

  const closing = guidanceFrameFromExperienceFrame({
    frame: internalFrame(section("closing")),
    currentMs: 118000,
    durationMs: 120000,
    lens: "body",
    isPlaying: false,
    playbackCompleted: false,
    completionStatus: "idle"
  })
  assert.deepEqual(closing.allowedWrites, [
    "body_state",
    "reflection",
    "practice_outcome",
    "active_imagination_note"
  ])

  const completed = guidanceFrameFromExperienceFrame({
    frame: internalFrame(section("reflection")),
    currentMs: 120000,
    durationMs: 120000,
    lens: "meditation",
    isPlaying: false,
    playbackCompleted: true,
    completionStatus: "saved"
  })
  assert.deepEqual(completed.allowedWrites, [
    "body_state",
    "reflection",
    "practice_outcome",
    "active_imagination_note"
  ])
  assert.equal(completed.playback.state, "completed")
})

test("blocked raw payload keys are stripped recursively", () => {
  const cleaned = stripBlockedFields({
    keep: "yes",
    transcript: "secret",
    nested: {
      captions: [{ text: "hidden" }],
      providerPrompt: "hidden",
      keepNested: true
    },
    list: [{ audioBase64: "hidden", label: "safe" }]
  })

  assert.deepEqual(cleaned, {
    keep: "yes",
    nested: { keepNested: true },
    list: [{ label: "safe" }]
  })
})

test("chat request sanitization keeps messages and bounded frame but drops raw artifact fields", () => {
  const frame = guidanceFrameFromExperienceFrame({
    frame: internalFrame(section("reflection")),
    currentMs: 1000,
    lens: "meditation",
    isPlaying: true,
    playbackCompleted: false,
    completionStatus: "idle"
  })
  const request = sanitizeRitualChatRequest({
    guidanceSessionId: "guidance-1",
    hostSessionId: "host-1",
    artifactId: "artifact-1",
    sourceRefs: [],
    currentFrame: frame,
    transcript: "do not forward",
    captions: [{ text: "do not forward" }],
    messages: [
      {
        id: "message-1",
        role: "user",
        parts: [
          { type: "text", text: "What should I stay with?" },
          { type: "data-unsafe", data: { rawMaterialText: "hidden" } }
        ]
      }
    ]
  })

  assert.ok(request)
  assert.equal(request.messages.length, 1)
  assert.equal(request.messages[0].parts.length, 1)
  assert.equal(request.currentFrame.phase, "ritual")
  assert.deepEqual(request.currentFrame.availableTracks, ["meditation"])
  assert.equal(JSON.stringify(request).includes("do not forward"), false)
})

test("event dedupe keys collapse repeated section entries but allow later lens changes", () => {
  const firstSection = ritualSessionEventDedupeKey({
    type: "section_entered",
    artifactId: "artifact-1",
    atMs: 100,
    sectionId: "closing",
    sectionKind: "closing"
  })
  const secondSection = ritualSessionEventDedupeKey({
    type: "section_entered",
    artifactId: "artifact-1",
    atMs: 900,
    sectionId: "closing",
    sectionKind: "closing"
  })
  const firstLens = ritualSessionEventDedupeKey({
    type: "lens_changed",
    artifactId: "artifact-1",
    atMs: 100,
    lens: "body",
    sectionId: "closing"
  })
  const laterLens = ritualSessionEventDedupeKey({
    type: "lens_changed",
    artifactId: "artifact-1",
    atMs: 1900,
    lens: "body",
    sectionId: "closing"
  })

  assert.equal(firstSection, secondSection)
  assert.notEqual(firstLens, laterLens)
})

test("local stub sessions keep top-level allowed writes equal to the frame", () => {
  const frame = guidanceFrameFromExperienceFrame({
    frame: internalFrame(section("closing")),
    currentMs: 1000,
    lens: "body",
    isPlaying: false,
    playbackCompleted: false,
    completionStatus: "idle"
  })
  const session = buildLocalGuidanceSession({
    hostSessionId: "host-1",
    artifactId: "artifact-1",
    currentFrame: frame,
    sourceRefs: []
  })

  assert.equal(session.mode, "local_stub")
  assert.equal(session.durableWritesEnabled, false)
  assert.deepEqual(session.allowedWrites, session.currentFrame.allowedWrites)
})
