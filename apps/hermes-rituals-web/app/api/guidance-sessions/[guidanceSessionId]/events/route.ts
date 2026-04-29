import { NextResponse } from "next/server"

import { forwardGuidanceEvent } from "@/lib/hermes-guidance-adapter"
import { sanitizeGuidanceEventEnvelope } from "@/lib/ritual-guidance-safety"

export async function POST(
  request: Request,
  { params }: { params: Promise<{ guidanceSessionId: string }> }
) {
  const { guidanceSessionId } = await params
  const body = await request.json().catch(() => null)
  const envelope = sanitizeGuidanceEventEnvelope(body, guidanceSessionId)

  if (!envelope) {
    return NextResponse.json({ error: "invalid_guidance_event" }, { status: 400 })
  }

  if (!process.env.HERMES_GUIDANCE_SESSIONS_URL) {
    return NextResponse.json(
      { mode: "local_stub", forwarded: false, persisted: false },
      { status: 202 }
    )
  }

  try {
    const forwarded = await forwardGuidanceEvent(guidanceSessionId, envelope)
    if (!forwarded.ok) {
      return NextResponse.json(
        { error: "hermes_guidance_event_failed" },
        { status: forwarded.status >= 400 && forwarded.status < 600 ? forwarded.status : 502 }
      )
    }
    return NextResponse.json({ forwarded: true }, { status: 202 })
  } catch {
    return NextResponse.json({ error: "hermes_guidance_event_unavailable" }, { status: 502 })
  }
}
