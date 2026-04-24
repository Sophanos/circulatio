import { NextResponse } from "next/server"

import { forwardRitualCompletion } from "@/lib/hermes-completion-adapter"
import { loadArtifactManifest } from "@/lib/load-artifact-manifest"

const PLAYBACK_STATES = new Set(["completed", "partial", "abandoned"])

function stringArray(value: unknown) {
  if (!Array.isArray(value)) return []
  return value.map((item) => String(item).trim()).filter(Boolean)
}

function cleanMetadata(value: unknown) {
  if (!value || typeof value !== "object" || Array.isArray(value)) return undefined
  const blocked = new Set(["transcript", "captions", "rawMaterialText", "providerPrompt"])
  return Object.fromEntries(
    Object.entries(value as Record<string, unknown>).filter(([key]) => !blocked.has(key))
  )
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
    clientMetadata: cleanMetadata(body.clientMetadata)
  }

  const forwarded = await forwardRitualCompletion(payload)
  return NextResponse.json(forwarded.body, { status: forwarded.status })
}
