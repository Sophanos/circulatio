import type {
  RitualChatRequest,
  RitualCompanionActionDecision,
  RitualGuidanceEventEnvelope,
  RitualGuidanceSessionCreateRequest
} from "@/lib/ritual-guidance-contract"

export type HermesGuidanceForwardResult = {
  ok: boolean
  status: number
  body: unknown
}

function joinEndpoint(base: string, ...segments: string[]) {
  const trimmed = base.replace(/\/+$/, "")
  return [trimmed, ...segments.map((segment) => encodeURIComponent(segment))].join("/")
}

async function readJsonResponse(response: Response) {
  return response.json().catch(() => ({}))
}

export async function forwardGuidanceSession(
  request: RitualGuidanceSessionCreateRequest,
  idempotencyKey: string
): Promise<HermesGuidanceForwardResult> {
  const endpoint = process.env.HERMES_GUIDANCE_SESSIONS_URL
  if (!endpoint) {
    return {
      ok: false,
      status: 503,
      body: { error: "hermes_guidance_sessions_not_configured" }
    }
  }

  const response = await fetch(endpoint, {
    method: "POST",
    headers: {
      "content-type": "application/json",
      "idempotency-key": idempotencyKey
    },
    body: JSON.stringify(request),
    cache: "no-store"
  })
  return { ok: response.ok, status: response.status, body: await readJsonResponse(response) }
}

export async function forwardGuidanceEvent(
  guidanceSessionId: string,
  envelope: RitualGuidanceEventEnvelope
): Promise<HermesGuidanceForwardResult> {
  const endpoint = process.env.HERMES_GUIDANCE_SESSIONS_URL
  if (!endpoint) {
    return {
      ok: false,
      status: 503,
      body: { error: "hermes_guidance_sessions_not_configured" }
    }
  }

  const response = await fetch(joinEndpoint(endpoint, guidanceSessionId, "events"), {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify(envelope),
    cache: "no-store"
  })
  return { ok: response.ok, status: response.status, body: await readJsonResponse(response) }
}

export async function forwardGuidanceAction(
  guidanceSessionId: string,
  decision: RitualCompanionActionDecision
): Promise<HermesGuidanceForwardResult> {
  const endpoint = process.env.HERMES_GUIDANCE_SESSIONS_URL
  if (!endpoint) {
    return {
      ok: false,
      status: 503,
      body: { error: "hermes_guidance_sessions_not_configured" }
    }
  }

  const response = await fetch(joinEndpoint(endpoint, guidanceSessionId, "actions"), {
    method: "POST",
    headers: {
      "content-type": "application/json",
      "idempotency-key": decision.action.idempotencyKey
    },
    body: JSON.stringify(decision),
    cache: "no-store"
  })
  return { ok: response.ok, status: response.status, body: await readJsonResponse(response) }
}

export async function forwardRitualChatStream(
  request: RitualChatRequest,
  signal?: AbortSignal
): Promise<Response | null> {
  const endpoint = process.env.HERMES_RITUAL_CHAT_URL
  if (!endpoint) return null

  return fetch(endpoint, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify(request),
    cache: "no-store",
    signal
  })
}

export function safeStreamingHeaders(headers: Headers) {
  const safe = new Headers()
  const contentType = headers.get("content-type")
  if (contentType) safe.set("content-type", contentType)
  const cacheControl = headers.get("cache-control")
  safe.set("cache-control", cacheControl || "no-cache, no-transform")
  const vary = headers.get("vary")
  if (vary) safe.set("vary", vary)
  return safe
}
