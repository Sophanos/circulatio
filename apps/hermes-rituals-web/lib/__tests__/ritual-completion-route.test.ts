import { strict as assert } from "node:assert"
import test, { afterEach } from "node:test"

import { POST as postArtifactCompletion } from "../../app/api/artifacts/[artifactId]/complete/route"

const originalFetch = globalThis.fetch
const originalCompletionUrl = process.env.HERMES_RITUAL_COMPLETION_URL

function restoreGlobals() {
  globalThis.fetch = originalFetch
  if (originalCompletionUrl === undefined) {
    delete process.env.HERMES_RITUAL_COMPLETION_URL
  } else {
    process.env.HERMES_RITUAL_COMPLETION_URL = originalCompletionUrl
  }
}

afterEach(restoreGlobals)

function completionRequest(idempotencyKey: string) {
  return new Request("http://localhost/api/artifacts/ritual-river-gate/complete", {
    method: "POST",
    headers: {
      "content-type": "application/json",
      "idempotency-key": idempotencyKey
    },
    body: JSON.stringify({
      completionId: idempotencyKey,
      completedAt: "2026-04-29T00:00:00.000Z",
      playbackState: "completed",
      durationMs: 56000,
      completedSections: ["section-closing"],
      transcript: "must not forward",
      captions: [{ text: "must not forward" }],
      reflectionText: "Browser-driver idempotency proof.",
      practiceFeedback: {
        fit: "good_fit",
        sensorTelemetry: "must_not_forward",
        nested: { poseLandmarks: "must_not_forward", keep: "yes" }
      },
      bodyState: {
        sensation: "easing",
        bodyRegion: "chest",
        activation: "low",
        tone: "settled",
        rawMaterialText: "must_not_forward"
      },
      clientMetadata: {
        source: "journey_cli_agent_browser",
        cameraData: "must_not_forward"
      }
    })
  })
}

test("completion route strips raw and sensor fields before forwarding", async () => {
  process.env.HERMES_RITUAL_COMPLETION_URL = "https://hermes.example/complete"
  const forwardedBodies: string[] = []
  const idempotencyHeaders: string[] = []
  globalThis.fetch = (async (_url, init) => {
    forwardedBodies.push(String(init?.body ?? ""))
    idempotencyHeaders.push(new Headers(init?.headers).get("idempotency-key") ?? "")
    return Response.json({ ok: true, recorded: true })
  }) as typeof fetch

  const first = await postArtifactCompletion(completionRequest("completion-route-proof"), {
    params: Promise.resolve({ artifactId: "ritual-river-gate" })
  })
  const second = await postArtifactCompletion(completionRequest("completion-route-proof"), {
    params: Promise.resolve({ artifactId: "ritual-river-gate" })
  })

  assert.equal(first.status, 200)
  assert.equal(second.status, 200)
  assert.deepEqual(idempotencyHeaders, ["completion-route-proof", "completion-route-proof"])
  assert.equal(forwardedBodies.length, 2)

  const payload = JSON.parse(forwardedBodies[0])
  assert.equal(payload.artifactId, "ritual-river-gate")
  assert.equal(payload.idempotencyKey, "completion-route-proof")
  assert.equal(payload.practiceFeedback.fit, "good_fit")
  assert.equal(payload.practiceFeedback.nested.keep, "yes")
  assert.equal(payload.practiceFeedback.sensorTelemetry, undefined)
  assert.equal(payload.practiceFeedback.nested.poseLandmarks, undefined)
  assert.equal(payload.clientMetadata.source, "journey_cli_agent_browser")
  assert.equal(payload.clientMetadata.cameraData, undefined)
  assert.equal(payload.bodyState.rawMaterialText, undefined)
  assert.equal(JSON.stringify(payload).includes("must_not_forward"), false)
})
