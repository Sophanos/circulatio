import { NextResponse } from "next/server"

import { forwardGuidanceAction } from "@/lib/hermes-guidance-adapter"
import { sanitizeActionDecisionRequest } from "@/lib/ritual-guidance-safety"

export async function POST(
  request: Request,
  { params }: { params: Promise<{ guidanceSessionId: string }> }
) {
  const { guidanceSessionId } = await params
  const body = await request.json().catch(() => null)
  const decision = sanitizeActionDecisionRequest(body)

  if (!decision) {
    return NextResponse.json({ error: "invalid_guidance_action" }, { status: 400 })
  }

  const action = {
    ...decision.action,
    guidanceSessionId,
    approvalState: decision.decision === "reject" ? "rejected" as const : "approved" as const,
    decidedAt: new Date().toISOString(),
    rejectionFinal: decision.decision === "reject" ? true : decision.action.rejectionFinal
  }
  const sanitizedDecision = { decision: decision.decision, action }

  if (!process.env.HERMES_GUIDANCE_SESSIONS_URL) {
    return NextResponse.json(
      {
        executed: false,
        mode: "local_stub",
        durableWritesEnabled: false,
        action
      },
      { status: decision.decision === "reject" ? 200 : 202 }
    )
  }

  try {
    const forwarded = await forwardGuidanceAction(guidanceSessionId, sanitizedDecision)
    if (!forwarded.ok) {
      return NextResponse.json(
        { error: "hermes_guidance_action_failed" },
        { status: forwarded.status >= 400 && forwarded.status < 600 ? forwarded.status : 502 }
      )
    }
    return NextResponse.json(forwarded.body, { status: forwarded.status || 200 })
  } catch {
    return NextResponse.json({ error: "hermes_guidance_action_unavailable" }, { status: 502 })
  }
}
