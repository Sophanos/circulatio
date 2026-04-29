import { createServer, type Server } from "node:http"
import { mkdir, rm, writeFile } from "node:fs/promises"
import path from "node:path"

import { expect, test, type Locator, type Page } from "@playwright/test"

const FULL_ARTIFACT_ID = "e2e-full-ritual"
const NARROW_ARTIFACT_ID = "e2e-breath-music"
const COMPLETION_PORT = Number(process.env.HERMES_RITUAL_COMPLETION_PORT ?? "3199")
const artifactRoot = path.join(process.cwd(), "public", "artifacts")

let completionServer: Server | null = null
const completionRequests: Array<{
  headers: Record<string, string | string[] | undefined>
  body: Record<string, unknown>
}> = []

function wavDataUri(durationSeconds = 1.2) {
  const sampleRate = 8_000
  const sampleCount = Math.floor(sampleRate * durationSeconds)
  const dataBytes = sampleCount * 2
  const buffer = Buffer.alloc(44 + dataBytes)
  buffer.write("RIFF", 0)
  buffer.writeUInt32LE(36 + dataBytes, 4)
  buffer.write("WAVE", 8)
  buffer.write("fmt ", 12)
  buffer.writeUInt32LE(16, 16)
  buffer.writeUInt16LE(1, 20)
  buffer.writeUInt16LE(1, 22)
  buffer.writeUInt32LE(sampleRate, 24)
  buffer.writeUInt32LE(sampleRate * 2, 28)
  buffer.writeUInt16LE(2, 32)
  buffer.writeUInt16LE(16, 34)
  buffer.write("data", 36)
  buffer.writeUInt32LE(dataBytes, 40)
  return `data:audio/wav;base64,${buffer.toString("base64")}`
}

function imageDataUri(label: string) {
  const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="800" viewBox="0 0 1200 800"><rect width="1200" height="800" fill="#101317"/><circle cx="600" cy="360" r="220" fill="#a6d6c9" opacity="0.58"/><text x="600" y="705" text-anchor="middle" fill="#f4f0e8" font-family="Arial" font-size="44">${label}</text></svg>`
  return `data:image/svg+xml,${encodeURIComponent(svg)}`
}

function videoDataUri() {
  return "data:video/mp4;base64,AAAAIGZ0eXBpc29tAAACAGlzb21pc28yYXZjMW1wNDE="
}

async function writeManifest(artifactId: string, manifest: Record<string, unknown>) {
  const artifactDir = path.join(artifactRoot, artifactId)
  await mkdir(artifactDir, { recursive: true })
  await writeFile(path.join(artifactDir, "manifest.json"), JSON.stringify(manifest, null, 2))
}

function fullRitualManifest(audioSrc: string) {
  return {
    schemaVersion: "hermes_ritual_artifact.v1",
    artifactId: FULL_ARTIFACT_ID,
    planId: "e2e_plan_full",
    createdAt: "2026-04-29T10:00:00Z",
    title: "E2E voice music cinema ritual",
    description: "Browser verification fixture for synchronized ritual playback.",
    privacyClass: "private",
    locale: "en-US",
    sourceRefs: [{ sourceType: "test_fixture", recordId: "e2e", role: "primary" }],
    durationMs: 2_400,
    sections: [
      { id: "arrival", kind: "arrival", title: "Arrival", startMs: 0, endMs: 500, preferredLens: "cinema" },
      { id: "breath", kind: "breath", title: "Breath", startMs: 500, endMs: 1_600, preferredLens: "breath" },
      {
        id: "closing",
        kind: "closing",
        title: "Closing",
        startMs: 1_600,
        endMs: 2_400,
        preferredLens: "body",
        capturePrompt: "What did you notice after the ritual?"
      }
    ],
    surfaces: {
      text: { body: "A short local fixture with voice, music, image, and cinema surfaces." },
      audio: { src: audioSrc, mimeType: "audio/wav", durationMs: 2_400, provider: "fixture" },
      captions: {
        segments: [
          { id: "cap_1", startMs: 0, endMs: 700, text: "Arrive with the breath." },
          { id: "cap_2", startMs: 700, endMs: 1_600, text: "Let the music hold the pace." }
        ]
      },
      breath: {
        enabled: true,
        pattern: "lengthened_exhale",
        inhaleSeconds: 1,
        holdSeconds: 0,
        exhaleSeconds: 1,
        restSeconds: 0,
        cycles: 1,
        visualForm: "pacer",
        phaseLabels: true
      },
      meditation: {
        enabled: true,
        fieldType: "coherence_convergence",
        durationMs: 1_000,
        macroProgressPolicy: "session_progress",
        microMotion: "convergence",
        instructionDensity: "sparse"
      },
      image: {
        enabled: true,
        src: imageDataUri("Full ritual"),
        alt: "Local generated fixture image.",
        provider: "fixture"
      },
      music: { src: audioSrc, mimeType: "audio/wav", durationMs: 2_400, provider: "fixture" },
      cinema: {
        enabled: true,
        src: videoDataUri(),
        posterSrc: imageDataUri("Cinema"),
        mimeType: "video/mp4",
        durationMs: 2_400,
        provider: "direct",
        title: "Local cinema fixture",
        playbackMode: "transport_synced",
        presentation: "stage_card"
      }
    },
    timeline: [],
    interaction: {
      finishPrompt: "What did you notice after the ritual?",
      captureBodyResponse: true,
      completionEndpoint: `/api/artifacts/${FULL_ARTIFACT_ID}/complete`,
      completion: {
        enabled: true,
        endpoint: `/api/artifacts/${FULL_ARTIFACT_ID}/complete`,
        idempotencyRequired: true,
        captureReflection: true,
        capturePracticeFeedback: true,
        completionIdStrategy: "client_uuid"
      }
    },
    safety: { stopInstruction: "Stop if needed.", contraindications: [], blockedSurfaces: [] },
    render: {
      rendererVersion: "ritual-renderer.v1",
      mode: "fixture_manifest",
      providers: ["fixture"],
      cacheKeys: [],
      budget: { currency: "USD", estimated: 0, actual: 0 },
      warnings: []
    }
  }
}

function narrowBreathMusicManifest(audioSrc: string) {
  return {
    schemaVersion: "hermes_ritual_artifact.v1",
    artifactId: NARROW_ARTIFACT_ID,
    planId: "e2e_plan_breath_music",
    createdAt: "2026-04-29T10:05:00Z",
    title: "E2E breath and music ritual",
    description: "Narrow fixture without narration, captions, transcript, image, or cinema.",
    privacyClass: "private",
    locale: "en-US",
    sourceRefs: [{ sourceType: "test_fixture", recordId: "e2e", role: "primary" }],
    durationMs: 2_000,
    sections: [
      { id: "breath", kind: "breath", title: "Breath", startMs: 0, endMs: 1_600, preferredLens: "breath" }
    ],
    surfaces: {
      text: { body: "" },
      audio: { src: null, mimeType: null, durationMs: null, provider: null },
      captions: { segments: [] },
      breath: {
        enabled: true,
        pattern: "lengthened_exhale",
        inhaleSeconds: 1,
        holdSeconds: 0,
        exhaleSeconds: 1,
        restSeconds: 0,
        cycles: 1,
        visualForm: "pacer",
        phaseLabels: true
      },
      meditation: {
        enabled: false,
        fieldType: "none",
        durationMs: 0,
        macroProgressPolicy: "session_progress",
        microMotion: "still",
        instructionDensity: "none"
      },
      music: { src: audioSrc, mimeType: "audio/wav", durationMs: 1_200, provider: "fixture" },
      image: { enabled: false, src: null, alt: "", provider: null },
      cinema: { enabled: false, src: null, provider: null }
    },
    timeline: [],
    interaction: {
      finishPrompt: "What did you notice?",
      captureBodyResponse: false
    },
    safety: { stopInstruction: "Stop if needed.", contraindications: [], blockedSurfaces: [] },
    render: {
      rendererVersion: "ritual-renderer.v1",
      mode: "fixture_manifest",
      providers: ["fixture"],
      cacheKeys: [],
      budget: { currency: "USD", estimated: 0, actual: 0 },
      warnings: []
    }
  }
}

async function startCompletionServer() {
  completionRequests.length = 0
  completionServer = createServer((request, response) => {
    if (request.method !== "POST" || request.url !== "/complete") {
      response.writeHead(404).end()
      return
    }

    const chunks: Buffer[] = []
    request.on("data", (chunk) => chunks.push(Buffer.from(chunk)))
    request.on("end", () => {
      const raw = Buffer.concat(chunks).toString("utf-8")
      const parsed = raw ? JSON.parse(raw) : {}
      completionRequests.push({
        headers: request.headers,
        body:
          parsed && typeof parsed === "object" && !Array.isArray(parsed)
            ? (parsed as Record<string, unknown>)
            : {}
      })
      response.writeHead(200, { "content-type": "application/json" })
      response.end(JSON.stringify({ ok: true, recorded: true }))
    })
  })

  await new Promise<void>((resolve) => {
    completionServer?.listen(COMPLETION_PORT, "127.0.0.1", resolve)
  })
}

async function stopCompletionServer() {
  if (!completionServer) return
  await new Promise<void>((resolve, reject) => {
    completionServer?.close((error) => (error ? reject(error) : resolve()))
  })
  completionServer = null
}

async function waitForDuration(locator: Locator) {
  await expect.poll(async () => {
    return locator.evaluate((node) => {
      const media = node as HTMLMediaElement
      return Number.isFinite(media.duration) && media.duration > 0
    })
  }).toBe(true)
}

function collectRuntimeErrors(page: Page) {
  const errors: string[] = []
  page.on("pageerror", (error) => errors.push(error.message))
  return errors
}

test.describe.configure({ mode: "serial" })

test.beforeAll(async () => {
  const fullAudio = wavDataUri(2.4)
  const narrowAudio = wavDataUri()
  await startCompletionServer()
  await writeManifest(FULL_ARTIFACT_ID, fullRitualManifest(fullAudio))
  await writeManifest(NARROW_ARTIFACT_ID, narrowBreathMusicManifest(narrowAudio))
})

test.afterAll(async () => {
  await stopCompletionServer()
  await Promise.all([
    rm(path.join(artifactRoot, FULL_ARTIFACT_ID), { recursive: true, force: true }),
    rm(path.join(artifactRoot, NARROW_ARTIFACT_ID), { recursive: true, force: true })
  ])
})

test("full artifact syncs narration, music, cinema, breath, and completion", async ({ page }) => {
  completionRequests.length = 0
  const runtimeErrors = collectRuntimeErrors(page)

  await page.goto(`/artifacts/${FULL_ARTIFACT_ID}`)
  await expect(page.getByTestId("ritual-player")).toBeVisible()
  expect(runtimeErrors).toEqual([])

  const narration = page.getByTestId("ritual-narration-audio")
  const music = page.getByTestId("ritual-music-audio")
  await expect(narration).toBeAttached()
  await expect(music).toBeAttached()
  await waitForDuration(narration)
  await waitForDuration(music)
  await expect(music).toHaveAttribute("loop", "")
  await expect(page.getByTestId("ritual-cinema-video")).toBeAttached()

  await page.getByTestId("ritual-lens-breath").click()
  await expect(page.getByTestId("ritual-breath-pacer")).toBeVisible()
  await expect(page.getByTestId("ritual-completion-panel")).toHaveCount(0)

  const playButton = page.getByTestId("ritual-play-toggle").first()
  await playButton.click()
  await expect.poll(async () => music.evaluate((node) => !(node as HTMLMediaElement).paused)).toBe(true)

  await playButton.click()
  await expect.poll(async () => music.evaluate((node) => (node as HTMLMediaElement).paused)).toBe(true)

  await playButton.click()
  const scrub = page.getByTestId("ritual-scrub-track").first()
  const box = await scrub.boundingBox()
  expect(box).not.toBeNull()
  await page.mouse.click(box!.x + box!.width * 0.7, box!.y + box!.height / 2)
  await expect.poll(async () => music.evaluate((node) => (node as HTMLMediaElement).currentTime)).toBeGreaterThan(0)

  await narration.evaluate((node) => {
    const media = node as HTMLMediaElement
    if (Number.isFinite(media.duration) && media.duration > 0) {
      media.currentTime = media.duration
    }
    media.dispatchEvent(new Event("timeupdate"))
    media.dispatchEvent(new Event("ended"))
  })
  await expect(page.getByTestId("ritual-body-capture")).toBeVisible()
  const completionPanel = page.getByTestId("ritual-completion-panel")
  if (!(await completionPanel.isVisible())) {
    await page.getByTestId("ritual-body-rail-toggle").click()
  }
  await expect(completionPanel).toBeVisible()
  const submit = completionPanel.getByTestId("ritual-completion-submit")
  await expect(submit).toContainText("Complete ritual")
  await expect(submit).toBeEnabled()
  await submit.scrollIntoViewIfNeeded()
  await submit.click()
  await expect.poll(() => completionRequests.length).toBe(1)
  await expect(completionPanel.getByText("Held with the ritual.")).toBeVisible()

  const completion = completionRequests[0]
  expect(completion.body.bodyState).toBeUndefined()
  expect(completion.headers["idempotency-key"]).toBeTruthy()
  expect(completion.body.artifactId).toBe(FULL_ARTIFACT_ID)
  expect(completion.body.manifestVersion).toBe("hermes_ritual_artifact.v1")
  expect(completion.body.playbackState).toBe("completed")

  await page.waitForTimeout(250)
  expect(completionRequests).toHaveLength(1)
  expect(runtimeErrors).toEqual([])
})


test("live guidance route starts in no-camera continuation mode", async ({ page }) => {
  const runtimeErrors = collectRuntimeErrors(page)

  await page.goto(`/live/e2e-guidance?artifactId=${FULL_ARTIFACT_ID}`)
  await expect(page.getByTestId("live-guidance-shell")).toBeVisible()
  await expect(page.getByText("No-camera guidance is active.")).toBeVisible()
  await page.getByRole("button", { name: "Camera preflight" }).click()
  await expect(page.getByText("Camera stays off until you enable it.")).toBeVisible()
  await page.getByRole("button", { name: "No camera" }).click()
  await expect(page.getByText("No-camera guidance is active.")).toBeVisible()
  await page.getByRole("button", { name: "Complete" }).click()
  await expect(page.getByText("Live guidance was completed.")).toBeVisible()

  expect(runtimeErrors).toEqual([])
})

test("narrow breath and music artifact hides narration transcript and cinema UI", async ({ page }) => {
  const runtimeErrors = collectRuntimeErrors(page)

  await page.goto(`/artifacts/${NARROW_ARTIFACT_ID}`)
  await expect(page.getByTestId("ritual-player")).toBeVisible()
  await expect(page.getByTestId("ritual-music-audio")).toBeAttached()
  await expect(page.getByTestId("ritual-breath-pacer")).toBeVisible()
  await expect(page.getByTestId("ritual-caption-cue")).toHaveCount(0)
  await expect(page.getByTestId("ritual-lens-cinema")).toHaveCount(0)
  await expect(page.getByTestId("ritual-cinema-stage")).toHaveCount(0)
  await expect(page.getByTestId("ritual-rail-tab-transcript")).toHaveCount(0)

  expect(runtimeErrors).toEqual([])
})
