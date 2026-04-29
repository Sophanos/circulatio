import { NextResponse } from "next/server"

import { forwardGuidanceSession } from "@/lib/hermes-guidance-adapter"
import {
  buildLocalGuidanceSession,
  normalizeGuidanceSession,
  sanitizeGuidanceSessionCreateRequest,
  stableGuidanceSessionId
} from "@/lib/ritual-guidance-safety"

function sessionIdempotencyKey(request: {
  guidanceSessionId?: string
  hostSessionId: string
  artifactId: string
  userId?: string
}) {
  return (
    request.guidanceSessionId ??
    `${request.hostSessionId}:${request.artifactId}:${request.userId ?? "anonymous"}`
  )
}

export async function POST(request: Request) {
  const body = await request.json().catch(() => null)
  const createRequest = sanitizeGuidanceSessionCreateRequest(body)
  if (!createRequest) {
    return NextResponse.json({ error: "invalid_guidance_session_request" }, { status: 400 })
  }

  const idempotencyKey = sessionIdempotencyKey(createRequest)

  if (!createRequest.guidanceSessionId) {
    createRequest.guidanceSessionId = stableGuidanceSessionId(createRequest)
  }

  if (!process.env.HERMES_GUIDANCE_SESSIONS_URL) {
    return NextResponse.json(buildLocalGuidanceSession(createRequest), { status: 200 })
  }

  try {
    const forwarded = await forwardGuidanceSession(createRequest, idempotencyKey)
    if (!forwarded.ok) {
      return NextResponse.json(
        { error: "hermes_guidance_session_failed" },
        { status: forwarded.status >= 400 && forwarded.status < 600 ? forwarded.status : 502 }
      )
    }

    return NextResponse.json(normalizeGuidanceSession(forwarded.body, createRequest), {
      status: 200
    })
  } catch {
    return NextResponse.json({ error: "hermes_guidance_session_unavailable" }, { status: 502 })
  }
}
