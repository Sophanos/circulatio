"use client"

/* eslint-disable react-hooks/set-state-in-effect */

import { useCallback, useEffect, useMemo, useRef, useState } from "react"

import type { RitualArtifactSourceRef } from "@/lib/artifact-contract"
import type { RitualSessionEvent } from "@/hooks/use-ritual-experience"
import type {
  RitualChatRequest,
  RitualGuidanceFrame,
  RitualGuidanceSession
} from "@/lib/ritual-guidance-contract"
import {
  buildGuidanceEventEnvelope,
  ritualSessionEventDedupeKey
} from "@/lib/ritual-guidance-events"
import {
  normalizeGuidanceSession,
  sanitizeSourceRefs,
  stableGuidanceSessionId
} from "@/lib/ritual-guidance-safety"

type UseRitualGuidanceSessionInput = {
  artifactId: string
  ritualPlanId?: string
  hostSessionId: string
  userId?: string
  privacyClass?: string
  sourceRefs: RitualArtifactSourceRef[]
  currentFrame: RitualGuidanceFrame
}

type QueuedEvent = {
  event: RitualSessionEvent
  frame: RitualGuidanceFrame
}

export type UseRitualGuidanceSessionReturn = {
  session: RitualGuidanceSession | null
  guidanceSessionId: string | null
  status: "idle" | "creating" | "ready" | "error"
  error: string | null
  recordSessionEvent: (event: RitualSessionEvent) => void
  getChatContext: () => Omit<RitualChatRequest, "messages">
  cacheForLiveRoute: () => void
  liveHref: string | null
}

function inputKey({ artifactId, hostSessionId, userId }: UseRitualGuidanceSessionInput) {
  return `${hostSessionId}:${artifactId}:${userId ?? "anonymous"}`
}

export function useRitualGuidanceSession({
  artifactId,
  ritualPlanId,
  hostSessionId,
  userId,
  privacyClass,
  sourceRefs,
  currentFrame
}: UseRitualGuidanceSessionInput): UseRitualGuidanceSessionReturn {
  const sanitizedSourceRefs = useMemo(() => sanitizeSourceRefs(sourceRefs), [sourceRefs])
  const sourceRefsKey = useMemo(() => JSON.stringify(sanitizedSourceRefs), [sanitizedSourceRefs])
  const key = inputKey({
    artifactId,
    ritualPlanId,
    hostSessionId,
    userId,
    privacyClass,
    sourceRefs: sanitizedSourceRefs,
    currentFrame
  })
  const pendingGuidanceSessionId = useMemo(
    () => stableGuidanceSessionId({ hostSessionId, artifactId, userId }),
    [artifactId, hostSessionId, userId]
  )

  const [session, setSession] = useState<RitualGuidanceSession | null>(null)
  const [status, setStatus] = useState<UseRitualGuidanceSessionReturn["status"]>("idle")
  const [error, setError] = useState<string | null>(null)

  const currentFrameRef = useRef(currentFrame)
  const sessionRef = useRef<RitualGuidanceSession | null>(null)
  const queueRef = useRef<QueuedEvent[]>([])
  const dedupeRef = useRef<Set<string>>(new Set())
  const keyRef = useRef(key)

  useEffect(() => {
    currentFrameRef.current = currentFrame
  }, [currentFrame])

  const resetForKey = useCallback(() => {
    if (keyRef.current === key) return
    keyRef.current = key
    queueRef.current = []
    dedupeRef.current = new Set()
    sessionRef.current = null
    setSession(null)
  }, [key])

  const sendEvent = useCallback(
    async (queued: QueuedEvent, targetSession: RitualGuidanceSession) => {
      const envelope = buildGuidanceEventEnvelope({
        session: targetSession,
        event: queued.event,
        frame: queued.frame,
        sourceRefs: sanitizedSourceRefs,
        privacyClass
      })

      try {
        await fetch(
          `/api/guidance-sessions/${encodeURIComponent(targetSession.guidanceSessionId)}/events`,
          {
            method: "POST",
            headers: { "content-type": "application/json" },
            body: JSON.stringify(envelope)
          }
        )
      } catch {
        // Guidance telemetry must not interrupt playback.
      }
    },
    [privacyClass, sanitizedSourceRefs]
  )

  const flushQueue = useCallback(
    (targetSession: RitualGuidanceSession) => {
      const queued = queueRef.current.splice(0, queueRef.current.length)
      void (async () => {
        for (const item of queued) {
          await sendEvent(item, targetSession)
        }
      })()
    },
    [sendEvent]
  )

  useEffect(() => {
    resetForKey()
    const controller = new AbortController()
    const createRequest = {
      guidanceSessionId: pendingGuidanceSessionId,
      hostSessionId,
      artifactId,
      ritualPlanId,
      userId,
      privacyClass,
      sourceRefs: sanitizedSourceRefs,
      currentFrame: currentFrameRef.current,
      clientMetadata: {
        surface: "hermes-rituals-web" as const,
        version: "ritual_companion_v1" as const
      }
    }

    setStatus("creating")
    setError(null)

    void (async () => {
      try {
        const response = await fetch("/api/guidance-sessions", {
          method: "POST",
          headers: { "content-type": "application/json" },
          body: JSON.stringify(createRequest),
          signal: controller.signal
        })
        const payload = await response.json().catch(() => ({}))
        if (!response.ok) throw new Error("guidance_session_create_failed")
        const nextSession = normalizeGuidanceSession(payload, createRequest)
        sessionRef.current = nextSession
        setSession(nextSession)
        setStatus("ready")
        flushQueue(nextSession)
      } catch (caught) {
        if (controller.signal.aborted) return
        sessionRef.current = null
        setSession(null)
        setStatus("error")
        setError(caught instanceof Error ? caught.message : "guidance_session_create_failed")
      }
    })()

    return () => controller.abort()
  }, [
    artifactId,
    flushQueue,
    hostSessionId,
    pendingGuidanceSessionId,
    privacyClass,
    resetForKey,
    ritualPlanId,
    sanitizedSourceRefs,
    sourceRefsKey,
    userId
  ])

  const recordSessionEvent = useCallback(
    (event: RitualSessionEvent) => {
      resetForKey()
      const dedupeKey = ritualSessionEventDedupeKey(event)
      if (dedupeRef.current.has(dedupeKey)) return
      dedupeRef.current.add(dedupeKey)

      const queued = { event, frame: currentFrameRef.current }
      const targetSession = sessionRef.current
      if (targetSession) {
        void sendEvent(queued, targetSession)
        return
      }

      queueRef.current.push(queued)
      if (queueRef.current.length > 50) {
        queueRef.current.splice(0, queueRef.current.length - 50)
      }
    },
    [resetForKey, sendEvent]
  )

  const getChatContext = useCallback((): Omit<RitualChatRequest, "messages"> => {
    const activeSession = sessionRef.current
    return {
      guidanceSessionId: activeSession?.guidanceSessionId ?? pendingGuidanceSessionId,
      hostSessionId,
      artifactId,
      ritualPlanId,
      userId: activeSession?.userId ?? userId,
      privacyClass: activeSession?.privacyClass ?? privacyClass,
      sourceRefs: sanitizedSourceRefs,
      currentFrame: currentFrameRef.current,
      clientMetadata: {
        surface: "hermes-rituals-web",
        version: "ritual_companion_v1",
        variant: "rail"
      }
    }
  }, [artifactId, hostSessionId, pendingGuidanceSessionId, privacyClass, ritualPlanId, sanitizedSourceRefs, userId])

  const cacheForLiveRoute = useCallback(() => {
    if (typeof window === "undefined") return
    const context = getChatContext()
    const key = `hermes:ritual-guidance:${context.guidanceSessionId}`
    window.sessionStorage.setItem(
      key,
      JSON.stringify({
        session: sessionRef.current,
        chatContext: {
          ...context,
          clientMetadata: { ...context.clientMetadata, variant: "live" as const }
        },
        cachedAt: new Date().toISOString()
      })
    )
  }, [getChatContext])

  const liveHref = useMemo(() => {
    const guidanceSessionId = session?.guidanceSessionId ?? pendingGuidanceSessionId
    if (!guidanceSessionId) return null
    return `/live/${encodeURIComponent(guidanceSessionId)}?artifactId=${encodeURIComponent(artifactId)}`
  }, [artifactId, pendingGuidanceSessionId, session?.guidanceSessionId])

  return {
    session,
    guidanceSessionId: session?.guidanceSessionId ?? pendingGuidanceSessionId,
    status,
    error,
    recordSessionEvent,
    getChatContext,
    cacheForLiveRoute,
    liveHref
  }
}
