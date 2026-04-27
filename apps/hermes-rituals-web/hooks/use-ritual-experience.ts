"use client"

import { useCallback, useEffect, useMemo, useRef, useState } from "react"

import type { PresentationArtifact, RitualSectionPreferredLens } from "@/lib/artifact-contract"
import {
  deriveRitualExperienceFrame,
  selectInitialRitualLens,
  type RitualExperienceCompletionStatus,
  type RitualExperienceFrame
} from "@/lib/ritual-experience"
import type { RitualSection } from "@/lib/artifact-contract"

export type RitualSessionEvent =
  | {
      type: "ritual_started"
      artifactId: string
      atMs: number
    }
  | {
      type: "section_entered"
      artifactId: string
      atMs: number
      sectionId: string
      sectionKind: RitualSection["kind"]
    }
  | {
      type: "lens_changed"
      artifactId: string
      atMs: number
      lens: RitualSectionPreferredLens
      sectionId?: string
    }
  | {
      type: "body_response_captured"
      artifactId: string
      atMs: number
      sectionId?: string
    }
  | {
      type: "active_imagination_note_created"
      artifactId: string
      atMs: number
      sectionId?: string
    }
  | {
      type: "ritual_completed"
      artifactId: string
      atMs: number
    }

export function useRitualExperience({
  artifact,
  sections,
  currentMs,
  completionStatus,
  onSessionEvent
}: {
  artifact: PresentationArtifact
  sections: RitualSection[]
  currentMs: number
  completionStatus: RitualExperienceCompletionStatus
  onSessionEvent?: (event: RitualSessionEvent) => void
}) {
  const [lensOverride, setLensOverride] = useState<{
    artifactId: string
    lens: RitualSectionPreferredLens
    sectionId?: string
  } | null>(null)
  const eventsRef = useRef<RitualSessionEvent[]>([])
  const previousSectionIdRef = useRef<string | null>(null)

  const baseFrame = useMemo<RitualExperienceFrame>(
    () =>
      deriveRitualExperienceFrame({
        artifact,
        sections,
        currentMs,
        completionStatus
      }),
    [artifact, completionStatus, currentMs, sections]
  )
  const activeLensOverride =
    lensOverride?.artifactId === artifact.id &&
    lensOverride.sectionId === baseFrame.activeSection?.id
      ? lensOverride.lens
      : null
  const frame = useMemo<RitualExperienceFrame>(
    () =>
      activeLensOverride
        ? deriveRitualExperienceFrame({
            artifact,
            sections,
            currentMs,
            userLensOverride: activeLensOverride,
            completionStatus
          })
        : baseFrame,
    [activeLensOverride, artifact, baseFrame, completionStatus, currentMs, sections]
  )

  const emit = useCallback(
    (event: RitualSessionEvent) => {
      eventsRef.current.push(event)
      onSessionEvent?.(event)
    },
    [onSessionEvent]
  )

  useEffect(() => {
    previousSectionIdRef.current = null
    eventsRef.current = []
    emit({
      type: "ritual_started",
      artifactId: artifact.id,
      atMs: 0
    })
  }, [artifact.id, emit])

  useEffect(() => {
    const activeSection = frame.activeSection
    const activeSectionId = activeSection?.id ?? null
    if (activeSectionId === previousSectionIdRef.current) return

    previousSectionIdRef.current = activeSectionId
    if (activeSection) {
      emit({
        type: "section_entered",
        artifactId: artifact.id,
        atMs: Math.max(currentMs, 0),
        sectionId: activeSection.id,
        sectionKind: activeSection.kind
      })
    }
  }, [artifact.id, currentMs, emit, frame.activeSection])

  const setStageLens = useCallback(
    (lens: RitualSectionPreferredLens) => {
      const sectionId = frame.activeSection?.id
      setLensOverride({ artifactId: artifact.id, lens, sectionId })
      emit({
        type: "lens_changed",
        artifactId: artifact.id,
        atMs: Math.max(currentMs, 0),
        lens,
        sectionId
      })
    },
    [artifact.id, currentMs, emit, frame.activeSection?.id]
  )

  const recordSessionEvent = useCallback(
    (event: Omit<RitualSessionEvent, "artifactId" | "atMs"> & { atMs?: number }) => {
      emit({
        ...event,
        artifactId: artifact.id,
        atMs: Math.max(event.atMs ?? currentMs, 0)
      } as RitualSessionEvent)
    },
    [artifact.id, currentMs, emit]
  )

  return {
    frame,
    stageLens: frame.effectiveLens || selectInitialRitualLens(artifact),
    setStageLens,
    recordSessionEvent,
    getSessionEvents: () => eventsRef.current
  }
}
