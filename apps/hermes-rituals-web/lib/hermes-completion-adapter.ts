import type {
  RitualArtifactSourceRef,
  RitualCompletionBodyStatePayload
} from "@/lib/artifact-contract"

export type HermesCompletionPayload = {
  artifactId: string
  manifestVersion: string
  idempotencyKey: string
  completedAt: string
  playbackState: "completed" | "partial" | "abandoned"
  planId?: string
  sourceRefs: RitualArtifactSourceRef[]
  durationMs?: number
  completedSections: string[]
  reflectionText?: string
  practiceFeedback?: Record<string, unknown>
  bodyState?: RitualCompletionBodyStatePayload
  clientMetadata?: Record<string, unknown>
}

export async function forwardRitualCompletion(payload: HermesCompletionPayload) {
  const endpoint = process.env.HERMES_RITUAL_COMPLETION_URL
  if (!endpoint) {
    return {
      ok: false as const,
      status: 503,
      body: { error: "hermes_completion_adapter_not_configured" }
    }
  }

  const response = await fetch(endpoint, {
    method: "POST",
    headers: {
      "content-type": "application/json",
      "idempotency-key": payload.idempotencyKey
    },
    body: JSON.stringify(payload),
    cache: "no-store"
  })

  const body = await response.json().catch(() => ({}))
  return { ok: response.ok, status: response.status, body }
}
