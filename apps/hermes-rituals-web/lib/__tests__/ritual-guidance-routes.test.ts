import { strict as assert } from "node:assert"
import test, { afterEach } from "node:test"

import { POST as createGuidanceSession } from "../../app/api/guidance-sessions/route"
import { POST as postGuidanceAction } from "../../app/api/guidance-sessions/[guidanceSessionId]/actions/route"
import { POST as postGuidanceEvent } from "../../app/api/guidance-sessions/[guidanceSessionId]/events/route"
import { POST as postRitualChat } from "../../app/api/ritual-chat/route"
import type { RitualCompanionAction } from "../ritual-guidance-contract"
import { emptyGuidanceFrame } from "../ritual-guidance-safety"

const originalFetch = globalThis.fetch
const originalGuidanceUrl = process.env.HERMES_GUIDANCE_SESSIONS_URL
const originalChatUrl = process.env.HERMES_RITUAL_CHAT_URL

function restoreGlobals() {
  globalThis.fetch = originalFetch
  if (originalGuidanceUrl === undefined) {
    delete process.env.HERMES_GUIDANCE_SESSIONS_URL
  } else {
    process.env.HERMES_GUIDANCE_SESSIONS_URL = originalGuidanceUrl
  }
  if (originalChatUrl === undefined) {
    delete process.env.HERMES_RITUAL_CHAT_URL
  } else {
    process.env.HERMES_RITUAL_CHAT_URL = originalChatUrl
  }
}

afterEach(restoreGlobals)

function jsonRequest(body: unknown) {
  return new Request("http://localhost/test", {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify(body)
  })
}

function createRequestBody() {
  return {
    hostSessionId: "host-1",
    artifactId: "artifact-1",
    userId: "user-1",
    sourceRefs: [],
    currentFrame: emptyGuidanceFrame(),
    transcript: "must not forward",
    clientMetadata: {
      surface: "hermes-rituals-web",
      version: "ritual_companion_v1",
      providerPrompt: "must not forward"
    }
  }
}

function action(): RitualCompanionAction {
  return {
    actionId: "action-1",
    guidanceSessionId: "guidance-1",
    type: "store_reflection",
    previewText: "Hold this reflection.",
    sourceRefs: [],
    idempotencyKey: "idem-1",
    approvalState: "proposed",
    proposedAt: "2026-04-28T00:00:00.000Z",
    frame: emptyGuidanceFrame({ allowedWrites: ["reflection"] }),
    payload: { type: "store_reflection", text: "A bounded reflection." }
  }
}

test("guidance session route returns deterministic local stub with no Hermes env", async () => {
  delete process.env.HERMES_GUIDANCE_SESSIONS_URL
  let called = false
  globalThis.fetch = (async () => {
    called = true
    return new Response("{}")
  }) as typeof fetch

  const first = await createGuidanceSession(jsonRequest(createRequestBody()))
  const second = await createGuidanceSession(jsonRequest(createRequestBody()))
  const firstBody = await first.json()
  const secondBody = await second.json()

  assert.equal(called, false)
  assert.equal(firstBody.mode, "local_stub")
  assert.equal(firstBody.durableWritesEnabled, false)
  assert.equal(firstBody.guidanceSessionId, secondBody.guidanceSessionId)
})

test("guidance session route forwards sanitized body and idempotency header", async () => {
  process.env.HERMES_GUIDANCE_SESSIONS_URL = "https://hermes.example/guidance"
  let capturedBody = ""
  let capturedIdempotency = ""
  globalThis.fetch = (async (_url, init) => {
    capturedBody = String(init?.body ?? "")
    capturedIdempotency = new Headers(init?.headers).get("idempotency-key") ?? ""
    return Response.json({
      guidanceSessionId: "guidance-remote",
      hostSessionId: "host-1",
      artifactId: "artifact-1",
      userId: "user-1",
      sourceRefs: [],
      currentFrame: emptyGuidanceFrame(),
      mode: "hermes",
      durableWritesEnabled: true,
      createdAt: "2026-04-28T00:00:00.000Z"
    })
  }) as typeof fetch

  const response = await createGuidanceSession(jsonRequest(createRequestBody()))
  const body = await response.json()

  assert.equal(response.status, 200)
  assert.equal(body.mode, "hermes")
  assert.ok(capturedIdempotency.includes("host-1:artifact-1:user-1"))
  assert.equal(capturedBody.includes("must not forward"), false)
})

test("event route accepts local preview without persisting or forwarding", async () => {
  delete process.env.HERMES_GUIDANCE_SESSIONS_URL
  let called = false
  globalThis.fetch = (async () => {
    called = true
    return new Response("{}")
  }) as typeof fetch

  const response = await postGuidanceEvent(jsonRequest({
    guidanceSessionId: "wrong-id",
    hostSessionId: "host-1",
    artifactId: "artifact-1",
    eventId: "event-1",
    event: { type: "ritual_started", artifactId: "artifact-1", atMs: 0 },
    frame: emptyGuidanceFrame(),
    sourceRefs: [],
    audioBase64: "hidden"
  }), { params: Promise.resolve({ guidanceSessionId: "guidance-1" }) })
  const body = await response.json()

  assert.equal(response.status, 202)
  assert.equal(body.persisted, false)
  assert.equal(called, false)
})

test("event and action routes forward to scoped Hermes endpoints", async () => {
  process.env.HERMES_GUIDANCE_SESSIONS_URL = "https://hermes.example/guidance"
  const urls: string[] = []
  const bodies: string[] = []
  globalThis.fetch = (async (url, init) => {
    urls.push(String(url))
    bodies.push(String(init?.body ?? ""))
    return Response.json({ ok: true, executed: true, action: action() })
  }) as typeof fetch

  await postGuidanceEvent(jsonRequest({
    guidanceSessionId: "guidance-1",
    hostSessionId: "host-1",
    artifactId: "artifact-1",
    eventId: "event-1",
    event: { type: "ritual_completed", artifactId: "artifact-1", atMs: 120000 },
    frame: emptyGuidanceFrame(),
    sourceRefs: [],
    transcript: "hidden"
  }), { params: Promise.resolve({ guidanceSessionId: "guidance-1" }) })

  await postGuidanceAction(jsonRequest({ action: action(), decision: "approve" }), {
    params: Promise.resolve({ guidanceSessionId: "guidance-1" })
  })

  assert.deepEqual(urls, [
    "https://hermes.example/guidance/guidance-1/events",
    "https://hermes.example/guidance/guidance-1/actions"
  ])
  assert.equal(bodies.some((body) => body.includes("hidden")), false)
})

test("chat route returns local preview stream with no chat env", async () => {
  delete process.env.HERMES_RITUAL_CHAT_URL
  const response = await postRitualChat(jsonRequest({
    guidanceSessionId: "guidance-1",
    hostSessionId: "host-1",
    artifactId: "artifact-1",
    sourceRefs: [],
    currentFrame: emptyGuidanceFrame(),
    messages: [
      {
        id: "message-1",
        role: "user",
        parts: [{ type: "text", text: "Stay with this?" }]
      }
    ]
  }))
  const text = await response.text()

  assert.equal(response.status, 200)
  assert.ok(text.includes("Companion unavailable in local preview"))
  assert.equal(text.includes("data-ritual-companion-action"), false)
})

test("chat route proposes local preview action only for explicit write intent", async () => {
  delete process.env.HERMES_RITUAL_CHAT_URL
  const response = await postRitualChat(jsonRequest({
    guidanceSessionId: "guidance-1",
    hostSessionId: "host-1",
    artifactId: "artifact-1",
    sourceRefs: [
      {
        sourceType: "dream",
        recordId: "dream-1",
        role: "primary",
        label: "River gate",
        rawMaterialText: "hidden raw"
      }
    ],
    currentFrame: emptyGuidanceFrame({ allowedWrites: ["reflection"] }),
    messages: [
      {
        id: "message-1",
        role: "user",
        parts: [
          {
            type: "text",
            text: "save this reflection: the breath felt softer."
          }
        ]
      }
    ]
  }))
  const text = await response.text()

  assert.equal(response.status, 200)
  assert.ok(text.includes("data-ritual-companion-action"))
  assert.ok(text.includes("store_reflection"))
  assert.ok(text.includes("Awaiting approval") || text.includes("proposed"))
  assert.equal(text.includes("hidden raw"), false)
})

test("local action approval and rejection never execute durable writes", async () => {
  delete process.env.HERMES_GUIDANCE_SESSIONS_URL
  const approved = await postGuidanceAction(jsonRequest({ action: action(), decision: "approve" }), {
    params: Promise.resolve({ guidanceSessionId: "guidance-1" })
  })
  const approvedBody = await approved.json()

  assert.equal(approved.status, 202)
  assert.equal(approvedBody.executed, false)
  assert.equal(approvedBody.mode, "local_stub")
  assert.equal(approvedBody.durableWritesEnabled, false)
  assert.equal(approvedBody.persistence, "not_persisted")
  assert.equal(approvedBody.action.approvalState, "approved")

  const rejected = await postGuidanceAction(jsonRequest({ action: action(), decision: "reject" }), {
    params: Promise.resolve({ guidanceSessionId: "guidance-1" })
  })
  const rejectedBody = await rejected.json()

  assert.equal(rejected.status, 200)
  assert.equal(rejectedBody.executed, false)
  assert.equal(rejectedBody.persistence, "not_persisted")
  assert.equal(rejectedBody.action.approvalState, "rejected")
  assert.equal(rejectedBody.action.rejectionFinal, true)
})

test("chat route falls back when Hermes stream fails without exposing internals", async () => {
  process.env.HERMES_RITUAL_CHAT_URL = "https://hermes.example/chat"
  globalThis.fetch = (async () => {
    throw new Error("secret upstream stack")
  }) as typeof fetch

  const response = await postRitualChat(jsonRequest({
    guidanceSessionId: "guidance-1",
    hostSessionId: "host-1",
    artifactId: "artifact-1",
    sourceRefs: [],
    currentFrame: emptyGuidanceFrame(),
    messages: [
      {
        id: "message-1",
        role: "user",
        parts: [{ type: "text", text: "Stay with this?" }]
      }
    ]
  }))
  const text = await response.text()

  assert.ok(text.includes("Companion stream is unavailable"))
  assert.equal(text.includes("secret upstream stack"), false)
})
