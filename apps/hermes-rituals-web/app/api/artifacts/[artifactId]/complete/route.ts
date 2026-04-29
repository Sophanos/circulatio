import { NextResponse } from "next/server"

import { forwardRitualCompletion } from "@/lib/hermes-completion-adapter"
import type { RitualCompletionBodyStatePayload } from "@/lib/artifact-contract"
import { loadArtifactManifest } from "@/lib/load-artifact-manifest"

const BODY_ACTIVATIONS = new Set(["low", "moderate", "high", "overwhelming"])
const PLAYBACK_STATES = new Set(["completed", "partial", "abandoned"])

function stringArray(value: unknown) {
  if (!Array.isArray(value)) return []
  return value.map((item) => String(item).trim()).filter(Boolean)
}

function cleanMetadata(value: unknown) {
  if (!value || typeof value !== "object" || Array.isArray(value)) return undefined
  const blocked = new Set([
    "transcript",
    "captions",
    "rawMaterialText",
    "providerPrompt",
    "cameraData",
    "videoFrame",
    "poseLandmarks",
    "sensorTelemetry"
  ])
  return Object.fromEntries(
    Object.entries(value as Record<string, unknown>).filter(([key]) => !blocked.has(key))
  )
}

function optionalString(value: unknown) {
  if (typeof value !== "string") return undefined
  const text = value.trim()
  return text || undefined
}

function cleanBodyState(
  value: unknown,
  privacyClass: string
): RitualCompletionBodyStatePayload | Response | undefined {
  if (value === undefined || value === null) return undefined
  if (typeof value !== "object" || Array.isArray(value)) {
    return NextResponse.json({ error: "invalid_body_state" }, { status: 400 })
  }

  const raw = value as Record<string, unknown>
  const sensation = optionalString(raw.sensation)
  if (!sensation) {
    return NextResponse.json({ error: "body_state_sensation_required" }, { status: 400 })
  }

  const activation = optionalString(raw.activation)
  if (activation && !BODY_ACTIVATIONS.has(activation)) {
    return NextResponse.json({ error: "invalid_body_state_activation" }, { status: 400 })
  }

  return {
    sensation,
    bodyRegion: optionalString(raw.bodyRegion),
    activation: activation as RitualCompletionBodyStatePayload["activation"],
    tone: optionalString(raw.tone),
    temporalContext: optionalString(raw.temporalContext),
    noteText: optionalString(raw.noteText),
    privacyClass: optionalString(raw.privacyClass) ?? privacyClass
  }
}

export async function POST(
  request: Request,
  { params }: { params: Promise<{ artifactId: string }> }
) {
  const { artifactId } = await params
  const manifest = await loadArtifactManifest(artifactId)

  if (!manifest) {
    return NextResponse.json({ error: "artifact_manifest_not_found" }, { status: 404 })
  }
  if (manifest.artifactId !== artifactId) {
    return NextResponse.json({ error: "artifact_id_mismatch" }, { status: 400 })
  }

  const body = (await request.json().catch(() => ({}))) as Record<string, unknown>
  const idempotencyKey =
    request.headers.get("idempotency-key")?.trim() || String(body.completionId || "").trim()
  if (!idempotencyKey) {
    return NextResponse.json({ error: "idempotency_key_required" }, { status: 400 })
  }

  const playbackState = String(body.playbackState || "completed")
  if (!PLAYBACK_STATES.has(playbackState)) {
    return NextResponse.json({ error: "invalid_playback_state" }, { status: 400 })
  }

  const bodyState = cleanBodyState(body.bodyState, manifest.privacyClass)
  if (bodyState instanceof Response) {
    return bodyState
  }

  const payload = {
    artifactId: manifest.artifactId,
    manifestVersion: manifest.schemaVersion,
    idempotencyKey,
    completedAt: String(body.completedAt || new Date().toISOString()),
    playbackState: playbackState as "completed" | "partial" | "abandoned",
    planId: manifest.planId,
    sourceRefs: manifest.sourceRefs,
    durationMs: typeof body.durationMs === "number" ? body.durationMs : manifest.durationMs,
    completedSections: stringArray(body.completedSections),
    reflectionText: typeof body.reflectionText === "string" ? body.reflectionText : undefined,
    practiceFeedback:
      body.practiceFeedback && typeof body.practiceFeedback === "object" && !Array.isArray(body.practiceFeedback)
        ? (body.practiceFeedback as Record<string, unknown>)
        : undefined,
    bodyState,
    clientMetadata: cleanMetadata(body.clientMetadata)
  }

  const forwarded = await forwardRitualCompletion(payload)
  return NextResponse.json(forwarded.body, { status: forwarded.status })
}
