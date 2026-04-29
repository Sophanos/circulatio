import { strict as assert } from "node:assert"
import test, { afterEach } from "node:test"

import {
  forwardRitualCompletion,
  type HermesCompletionPayload
} from "../hermes-completion-adapter"

const originalFetch = globalThis.fetch
const originalCompletionUrl = process.env.HERMES_RITUAL_COMPLETION_URL
const originalCompletionScript = process.env.CIRCULATIO_RITUAL_COMPLETION_SCRIPT
const originalRepoRoot = process.env.CIRCULATIO_REPO_ROOT

function restoreGlobals() {
  globalThis.fetch = originalFetch
  if (originalCompletionUrl === undefined) {
    delete process.env.HERMES_RITUAL_COMPLETION_URL
  } else {
    process.env.HERMES_RITUAL_COMPLETION_URL = originalCompletionUrl
  }
  if (originalCompletionScript === undefined) {
    delete process.env.CIRCULATIO_RITUAL_COMPLETION_SCRIPT
  } else {
    process.env.CIRCULATIO_RITUAL_COMPLETION_SCRIPT = originalCompletionScript
  }
  if (originalRepoRoot === undefined) {
    delete process.env.CIRCULATIO_REPO_ROOT
  } else {
    process.env.CIRCULATIO_REPO_ROOT = originalRepoRoot
  }
}

afterEach(restoreGlobals)

function payload(): HermesCompletionPayload {
  return {
    artifactId: "artifact-1",
    manifestVersion: "hermes_ritual_artifact.v1",
    idempotencyKey: "completion-1",
    completedAt: "2026-04-29T00:00:00.000Z",
    playbackState: "completed",
    sourceRefs: [],
    completedSections: ["closing"],
    reflectionText: "A literal reflection."
  }
}

test("completion adapter forwards to configured Hermes endpoint", async () => {
  process.env.HERMES_RITUAL_COMPLETION_URL = "https://hermes.example/complete"
  let capturedUrl = ""
  let capturedIdempotency = ""
  let capturedBody = ""
  globalThis.fetch = (async (url, init) => {
    capturedUrl = String(url)
    capturedIdempotency = new Headers(init?.headers).get("idempotency-key") ?? ""
    capturedBody = String(init?.body ?? "")
    return Response.json({ ok: true, recorded: true })
  }) as typeof fetch

  const result = await forwardRitualCompletion(payload())

  assert.equal(result.status, 200)
  assert.equal(result.ok, true)
  assert.equal(capturedUrl, "https://hermes.example/complete")
  assert.equal(capturedIdempotency, "completion-1")
  assert.equal(JSON.parse(capturedBody).reflectionText, "A literal reflection.")
})

test("completion adapter falls back to local bridge when no Hermes endpoint is set", async () => {
  delete process.env.HERMES_RITUAL_COMPLETION_URL
  process.env.CIRCULATIO_RITUAL_COMPLETION_SCRIPT = "/definitely/missing/record_ritual_completion.py"

  const result = await forwardRitualCompletion(payload())

  assert.equal(result.ok, false)
  assert.equal(result.status, 503)
  assert.equal(result.body.error, "local_completion_bridge_not_found")
})
