import { strict as assert } from "node:assert"
import test from "node:test"

import {
  deriveRitualSectionsFromManifest,
  ritualArtifactFromManifest,
  type RitualArtifactManifest
} from "../artifact-contract"
import { deriveRitualExperienceFrame } from "../ritual-experience"

function baseManifest(): RitualArtifactManifest {
  return {
    schemaVersion: "hermes_ritual_artifact.v1",
    artifactId: "test-artifact",
    planId: "test-plan",
    createdAt: "2026-04-28T00:00:00Z",
    title: "Test ritual",
    description: "A test ritual.",
    privacyClass: "private",
    locale: "en-US",
    sourceRefs: [],
    durationMs: 300000,
    surfaces: {
      text: { body: "Arrival. Breath. Reflection. Closing." },
      captions: {
        segments: [
          { id: "cap-1", startMs: 0, endMs: 7000, text: "Arrival." },
          { id: "cap-2", startMs: 9000, endMs: 17000, text: "Breath." },
          { id: "cap-3", startMs: 20000, endMs: 34000, text: "Reflection." },
          { id: "cap-4", startMs: 36000, endMs: 48000, text: "Stillness." },
          { id: "cap-5", startMs: 50000, endMs: 60000, text: "Closing." }
        ]
      },
      breath: {
        enabled: true,
        pattern: "lengthened_exhale",
        inhaleSeconds: 4,
        holdSeconds: 0,
        exhaleSeconds: 6,
        restSeconds: 2,
        cycles: 5,
        visualForm: "pacer"
      },
      meditation: {
        enabled: true,
        fieldType: "coherence_convergence",
        durationMs: 180000,
        macroProgressPolicy: "session_progress",
        microMotion: "convergence",
        instructionDensity: "sparse"
      },
      image: {
        enabled: true,
        src: "/artifacts/test/image.png"
      },
      cinema: {
        enabled: false,
        src: null
      }
    },
    timeline: [],
    interaction: {
      finishPrompt: "What did you notice?",
      captureBodyResponse: true,
      completion: {
        enabled: true,
        endpoint: "/api/artifacts/test-artifact/complete",
        idempotencyRequired: true,
        captureReflection: true,
        capturePracticeFeedback: true,
        completionIdStrategy: "client_uuid"
      }
    },
    safety: {
      stopInstruction: "Stop if this increases activation.",
      contraindications: [],
      blockedSurfaces: []
    },
    render: {
      rendererVersion: "test",
      mode: "dry_run_manifest",
      providers: ["mock"],
      cacheKeys: [],
      budget: { currency: "USD", estimated: 0, actual: 0 },
      warnings: []
    }
  }
}

test("explicit manifest sections win over captions", () => {
  const manifest = baseManifest()
  manifest.sections = [
    {
      id: "sec-arrival",
      title: "Arrival",
      kind: "arrival",
      startMs: 0,
      endMs: 12000
    },
    {
      id: "sec-closing",
      title: "Closing",
      kind: "closing",
      startMs: 252000,
      endMs: 300000
    }
  ]

  const sections = deriveRitualSectionsFromManifest(manifest)

  assert.deepEqual(sections.map((section) => section.id), ["sec-arrival", "sec-closing"])
  assert.equal(sections[0].captionCount, 2)
  assert.equal(sections[1].captionCount, undefined)
})

test("caption segments do not become the primary ritual structure", () => {
  const sections = deriveRitualSectionsFromManifest(baseManifest())

  assert.deepEqual(
    sections.map((section) => section.kind),
    ["arrival", "breath", "image", "reflection", "closing"]
  )
  assert.equal(sections[1].startMs, 12000)
  assert.equal(sections[1].endMs, 72000)
  assert.equal(sections.at(-1)?.endMs, 300000)
})

test("experience frame resolves recommended lens and body prompt state", () => {
  const manifest = baseManifest()
  manifest.sections = [
    {
      id: "sec-arrival",
      title: "Arrival",
      kind: "arrival",
      startMs: 0,
      endMs: 12000,
      preferredLens: "photo"
    },
    {
      id: "sec-reflection",
      title: "Reflection",
      kind: "reflection",
      startMs: 12000,
      endMs: 252000,
      preferredLens: "meditation"
    },
    {
      id: "sec-closing",
      title: "Closing",
      kind: "closing",
      startMs: 252000,
      endMs: 300000,
      preferredLens: "body"
    }
  ]
  const artifact = ritualArtifactFromManifest(manifest)
  const sections = artifact.ritualSections ?? []

  const reflection = deriveRitualExperienceFrame({
    artifact,
    sections,
    currentMs: 72000
  })
  assert.equal(reflection.recommendedLens, "meditation")
  assert.equal(reflection.effectiveLens, "meditation")
  assert.deepEqual(reflection.allowedWrites, ["reflection_text", "active_imagination_note"])

  const manual = deriveRitualExperienceFrame({
    artifact,
    sections,
    currentMs: 72000,
    userLensOverride: "photo"
  })
  assert.equal(manual.effectiveLens, "photo")

  const closing = deriveRitualExperienceFrame({
    artifact,
    sections,
    currentMs: 260000
  })
  assert.equal(closing.bodyPromptMode, "inline_hint")
  assert.equal(closing.recommendedLens, "meditation")
  assert.deepEqual(closing.allowedWrites, [
    "body_state",
    "reflection_text",
    "active_imagination_note"
  ])

  const focused = deriveRitualExperienceFrame({
    artifact,
    sections,
    currentMs: 260000,
    userLensOverride: "body"
  })
  assert.equal(focused.bodyPromptMode, "focused_capture")
  assert.equal(focused.effectiveLens, "body")
})
