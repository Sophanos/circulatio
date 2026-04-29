import type { RitualSessionEvent } from "@/hooks/use-ritual-experience"
import type {
  RitualGuidanceEventEnvelope,
  RitualGuidanceFrame,
  RitualGuidanceSession
} from "@/lib/ritual-guidance-contract"
import { sanitizeSourceRefs } from "@/lib/ritual-guidance-safety"
import type { RitualArtifactSourceRef } from "@/lib/artifact-contract"

function roundedAtMs(event: RitualSessionEvent) {
  return Math.round(Math.max(event.atMs ?? 0, 0) / 1000) * 1000
}

export function ritualSessionEventDedupeKey(event: RitualSessionEvent): string {
  const sectionId = "sectionId" in event ? event.sectionId ?? "none" : "none"
  switch (event.type) {
    case "ritual_started":
      return `${event.artifactId}:ritual_started`
    case "section_entered":
      return `${event.artifactId}:section_entered:${event.sectionId}`
    case "ritual_completed":
      return `${event.artifactId}:ritual_completed`
    case "body_response_captured":
      return `${event.artifactId}:body_response_captured:${sectionId}`
    case "active_imagination_note_created":
      return `${event.artifactId}:active_imagination_note_created:${sectionId}:${roundedAtMs(event)}`
    case "lens_changed":
      return `${event.artifactId}:lens_changed:${sectionId}:${event.lens}:${roundedAtMs(event)}`
  }
}

export function ritualSessionEventId({
  guidanceSessionId,
  event
}: {
  guidanceSessionId: string
  event: RitualSessionEvent
}) {
  return `${guidanceSessionId}:${ritualSessionEventDedupeKey(event)}`
}

export function buildGuidanceEventEnvelope({
  session,
  event,
  frame,
  sourceRefs,
  privacyClass,
  occurredAt = new Date().toISOString()
}: {
  session: Pick<RitualGuidanceSession, "guidanceSessionId" | "hostSessionId" | "artifactId">
  event: RitualSessionEvent
  frame: RitualGuidanceFrame
  sourceRefs: RitualArtifactSourceRef[]
  privacyClass?: string
  occurredAt?: string
}): RitualGuidanceEventEnvelope {
  return {
    guidanceSessionId: session.guidanceSessionId,
    hostSessionId: session.hostSessionId,
    artifactId: session.artifactId,
    eventId: ritualSessionEventId({ guidanceSessionId: session.guidanceSessionId, event }),
    event,
    frame,
    sourceRefs: sanitizeSourceRefs(sourceRefs),
    privacyClass,
    occurredAt,
    clientMetadata: {
      surface: "hermes-rituals-web",
      version: "ritual_companion_v1"
    }
  }
}
