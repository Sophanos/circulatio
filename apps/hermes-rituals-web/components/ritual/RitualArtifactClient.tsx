"use client"

import { useCallback, useEffect, useMemo, useRef, useState } from "react"
import { ArrowLeft, CheckCircle2, ListMusic, MessageSquareText, Volume2, VolumeX } from "lucide-react"
import * as SliderPrimitive from "@radix-ui/react-slider"

import { useRouter } from "next/navigation"
import { motion, AnimatePresence } from "motion/react"

import {
  useRitualExperience,
  type RitualSessionEvent
} from "@/hooks/use-ritual-experience"
import { useRitualGuidanceSession } from "@/hooks/use-ritual-guidance-session"
import {
  RitualPlayer,
  type RitualPlayerHandle,
  type RitualStageLens
} from "@/components/ritual/RitualPlayer"
import {
  EMPTY_BODY_STATE_DRAFT,
  type BodyCompletionStatus,
  type BodyStateDraft
} from "@/components/ritual/BodyPicker"
import {
  RitualCompletionPanel,
  type RitualCompletionSubmitPayload
} from "@/components/ritual/completion/RitualCompletionPanel"
import { RitualRail, type RailTab } from "@/components/ritual/RitualRail"
import { RitualCompanionPanel } from "@/components/ritual/companion/RitualCompanionPanel"
import {
  RitualTimelineProgress,
  type RitualTimelineCompletionStatus
} from "@/components/ritual/RitualTimelineProgress"
import { MICRO_SPRING, PANEL_SPRING, RITUAL_FADE } from "@/components/ritual/motion"
import type {
  ArtifactChannels,
  PresentationArtifact,
  RitualCompletionBodyStatePayload,
  RitualSection,
  SessionShell
} from "@/lib/artifact-contract"
import type { RitualExperienceTrack } from "@/lib/ritual-experience"
import { guidanceFrameFromExperienceFrame } from "@/lib/ritual-guidance-safety"

const CHANNEL_ORDER = ["voice", "ambient", "breath", "pulse", "music"] as const
const RITUAL_LENS_OPTIONS: RitualStageLens[] = ["cinema", "photo", "breath", "meditation", "body"]
const RITUAL_LENS_LABELS: Record<RitualStageLens, string> = {
  cinema: "cinema",
  photo: "photo",
  breath: "breath",
  meditation: "med",
  body: "body"
}
const VISUAL_TRACK_TO_LENS: Partial<Record<RitualExperienceTrack, RitualStageLens>> = {
  cinema: "cinema",
  photo: "photo",
  breath: "breath",
  meditation: "meditation",
  body_map: "body"
}
type ChannelName = (typeof CHANNEL_ORDER)[number]
type BodyCaptureState = {
  artifactKey: string
  draft: BodyStateDraft
  completionStatus: BodyCompletionStatus
  submitError: string | null
}

function createInitialBodyDraft(privacyClass?: string): BodyStateDraft {
  return {
    ...EMPTY_BODY_STATE_DRAFT,
    privacyClass
  }
}

function createBodyCaptureState(artifactKey: string, privacyClass?: string): BodyCaptureState {
  return {
    artifactKey,
    draft: createInitialBodyDraft(privacyClass),
    completionStatus: "idle",
    submitError: null
  }
}

function currentBodyCaptureState(
  state: BodyCaptureState,
  artifactKey: string,
  privacyClass?: string
): BodyCaptureState {
  return state.artifactKey === artifactKey
    ? state
    : createBodyCaptureState(artifactKey, privacyClass)
}

function availableStageLenses(
  availableTracks: RitualExperienceTrack[],
  bodyCaptureAvailable: boolean
): RitualStageLens[] {
  const lenses = availableTracks.flatMap((track) => {
    const lens = VISUAL_TRACK_TO_LENS[track]
    if (!lens) return []
    if (lens === "body" && !bodyCaptureAvailable) return []
    return [lens]
  })

  return RITUAL_LENS_OPTIONS.filter((lens) => lenses.includes(lens))
}

function bodyCaptureAvailableInFrame({
  activeSection,
  completionStatus,
  playbackCompleted
}: {
  activeSection?: RitualSection | null
  completionStatus: BodyCompletionStatus
  playbackCompleted: boolean
}) {
  return (
    activeSection?.kind === "closing" ||
    playbackCompleted ||
    completionStatus === "submitting" ||
    completionStatus === "saved" ||
    completionStatus === "error"
  )
}

function timelineCompletionStatus(
  completionStatus: BodyCompletionStatus,
  playbackCompleted: boolean
): RitualTimelineCompletionStatus {
  if (completionStatus !== "idle") return completionStatus
  return playbackCompleted ? "completed" : "idle"
}

function createCompletionId(artifactId: string) {
  const randomId =
    typeof crypto !== "undefined" && "randomUUID" in crypto
      ? crypto.randomUUID()
      : `${Date.now()}-${Math.random().toString(36).slice(2)}`
  return `${artifactId}:completion:${randomId}`
}

function buildBodyStatePayload(
  draft: BodyStateDraft,
  privacyClass?: string
): RitualCompletionBodyStatePayload | null {
  const sensation = draft.sensation.trim()
  if (!sensation) return null

  return {
    sensation,
    bodyRegion: draft.bodyRegion,
    activation: draft.activation,
    tone: draft.tone?.trim() || undefined,
    temporalContext: draft.temporalContext?.trim() || "post_ritual_completion",
    noteText: draft.noteText?.trim() || undefined,
    privacyClass: draft.privacyClass?.trim() || privacyClass
  }
}

function completedSectionIds(
  sections: RitualSection[],
  currentMs: number,
  durationMs: number
) {
  if (currentMs <= 0 || currentMs >= durationMs - 1000) {
    return sections.map((section) => section.id)
  }
  return sections.filter((section) => section.endMs <= currentMs).map((section) => section.id)
}

function useMediaQuery(query: string) {
  const [matches, setMatches] = useState(false)

  useEffect(() => {
    if (typeof window === "undefined") return
    const media = window.matchMedia(query)
    const update = () => setMatches(media.matches)
    update()
    media.addEventListener("change", update)
    return () => media.removeEventListener("change", update)
  }, [query])

  return matches
}

function LiquidMixer({
  channels,
  masterVolume,
  glassy,
  onMasterChange,
  onChannelToggle,
  onChannelGainChange
}: {
  channels?: ArtifactChannels
  masterVolume: number
  glassy?: boolean
  onMasterChange: (v: number) => void
  onChannelToggle: (name: ChannelName) => void
  onChannelGainChange: (name: ChannelName, gain: number) => void
}) {
  const [hovered, setHovered] = useState(false)
  const [hoveredChannel, setHoveredChannel] = useState<ChannelName | null>(null)
  const isMuted = masterVolume === 0

  return (
    <motion.div
      className="relative flex flex-col overflow-hidden border backdrop-blur-2xl"
      layout
      initial={false}
      animate={{
        width: hovered ? 220 : 36,
        height: hovered ? 220 : 36,
        borderRadius: hovered ? 20 : 18,
        backgroundColor: glassy && hovered ? "rgba(0,0,0,0.38)" : "rgba(255,255,255,0.02)",
        borderColor: glassy && hovered ? "rgba(255,255,255,0.10)" : "rgba(255,255,255,0)"
      }}
      transition={MICRO_SPRING}
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => {
        setHovered(false)
        setHoveredChannel(null)
      }}
    >
      {/* Master volume row */}
      <div
        className={[
          "flex shrink-0 items-center",
          hovered ? "h-9 gap-3 px-3 pt-3" : "h-9 justify-center"
        ].join(" ")}
      >
        <motion.button
          type="button"
          onClick={() => onMasterChange(isMuted ? 0.75 : 0)}
          className="flex size-7 shrink-0 items-center justify-center rounded-full text-silver-300 hover:text-white"
          whileHover={{ scale: 1.08 }}
          whileTap={{ scale: 0.94 }}
          transition={MICRO_SPRING}
        >
          {isMuted ? <VolumeX className="size-4" /> : <Volume2 className="size-4" />}
        </motion.button>

        <AnimatePresence>
          {hovered && (
            <motion.div
              className="flex flex-1 items-center"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              transition={RITUAL_FADE}
            >
              <SliderPrimitive.Root
                value={[masterVolume]}
                onValueChange={(vals) => onMasterChange(vals[0])}
                min={0}
                max={1}
                step={0.01}
                className="relative flex h-4 flex-1 touch-none items-center select-none"
              >
                <SliderPrimitive.Track className="relative h-1 w-full grow overflow-hidden rounded-full bg-white/15">
                  <SliderPrimitive.Range className="absolute h-full bg-white" />
                </SliderPrimitive.Track>
                <SliderPrimitive.Thumb className="block size-3.5 rounded-full bg-white shadow-md focus:outline-none" />
              </SliderPrimitive.Root>
            </motion.div>
          )}
        </AnimatePresence>
      </div>

      {/* Channel rows */}
      <AnimatePresence>
        {hovered && (
          <motion.div
            className="flex flex-col px-3 pb-3 pt-1.5"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={RITUAL_FADE}
          >
            <div className="mb-2 h-px bg-white/10" />
            <div className="flex flex-col">
              {CHANNEL_ORDER.map((name) => {
                const ch = channels?.[name]
                if (!ch) return null
                const muted = ch.muted ?? false
                const gain = ch.gain ?? 0.5
                const isChannelHovered = hoveredChannel === name

                return (
                  <div
                    key={name}
                    className={[
                      "flex items-center gap-3 rounded-lg px-2 py-1.5",
                      muted
                        ? "text-silver-500"
                        : "text-silver-100 hover:bg-white/[0.04]"
                    ].join(" ")}
                    onMouseEnter={() => setHoveredChannel(name)}
                    onMouseLeave={() => setHoveredChannel((prev) => (prev === name ? null : prev))}
                  >
                    <motion.button
                      type="button"
                      onClick={() => onChannelToggle(name)}
                      className="flex size-6 shrink-0 items-center justify-center rounded-full"
                      whileHover={{ scale: 1.08 }}
                      whileTap={{ scale: 0.94 }}
                      transition={MICRO_SPRING}
                    >
                      {muted ? (
                        <VolumeX className="size-4" />
                      ) : (
                        <Volume2 className="size-4" />
                      )}
                    </motion.button>

                    <div className="flex min-w-0 flex-1 items-center">
                      <AnimatePresence mode="popLayout">
                        {isChannelHovered && !muted ? (
                          <motion.div
                            key="slider"
                            className="flex flex-1 items-center"
                            initial={{ opacity: 0, width: 0 }}
                            animate={{ opacity: 1, width: "auto" }}
                            exit={{ opacity: 0, width: 0 }}
                            transition={MICRO_SPRING}
                          >
                            <SliderPrimitive.Root
                              value={[gain]}
                              onValueChange={(vals) => onChannelGainChange(name, vals[0])}
                              min={0}
                              max={1}
                              step={0.01}
                              className="relative flex h-4 w-full touch-none items-center select-none"
                            >
                              <SliderPrimitive.Track className="relative h-[3px] w-full grow overflow-hidden rounded-full bg-white/15">
                                <SliderPrimitive.Range className="absolute h-full bg-white/70" />
                              </SliderPrimitive.Track>
                              <SliderPrimitive.Thumb className="block size-2.5 rounded-full bg-white focus:outline-none" />
                            </SliderPrimitive.Root>
                          </motion.div>
                        ) : (
                          <motion.span
                            key="label"
                            className="truncate text-sm font-medium capitalize"
                            initial={{ opacity: 0 }}
                            animate={{ opacity: 1 }}
                            exit={{ opacity: 0 }}
                            transition={RITUAL_FADE}
                          >
                            {name}
                          </motion.span>
                        )}
                      </AnimatePresence>
                    </div>
                  </div>
                )
              })}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  )
}

function RitualLensSwitch({
  activeLens,
  availableLenses,
  onChange
}: {
  activeLens: RitualStageLens
  availableLenses: RitualStageLens[]
  onChange: (lens: RitualStageLens) => void
}) {
  if (availableLenses.length <= 1) return null

  return (
    <div
      className="flex items-center gap-1 rounded-full p-1"
      style={{ backgroundColor: "rgba(255,255,255,0.03)" }}
    >
      {availableLenses.map((lens) => {
        const active = activeLens === lens

        return (
          <button
            key={lens}
            type="button"
            data-testid={`ritual-lens-${lens}`}
            onClick={() => onChange(lens)}
            className="relative flex items-center justify-center rounded-full px-2.5 py-1"
          >
            {active && (
              <motion.div
                layoutId="ritual-lens-pill"
                className="pointer-events-none absolute inset-0 rounded-full bg-white/[0.10]"
                transition={MICRO_SPRING}
              />
            )}
            <span
              className={[
                "relative text-[10px] font-medium uppercase leading-none tracking-[0.18em]",
                active ? "text-silver-100" : "text-silver-500"
              ].join(" ")}
            >
              {RITUAL_LENS_LABELS[lens]}
            </span>
          </button>
        )
      })}
    </div>
  )
}

export function RitualArtifactClient({
  artifact,
  session,
  onSessionEvent
}: {
  artifact: PresentationArtifact
  session?: SessionShell
  onSessionEvent?: (event: RitualSessionEvent) => void
}) {
  const router = useRouter()
  const playerRef = useRef<RitualPlayerHandle>(null)
  const railRef = useRef<HTMLElement>(null)
  const toggleRef = useRef<HTMLDivElement>(null)
  const hideTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  const [currentMs, setCurrentMs] = useState(0)
  const [playbackCompletion, setPlaybackCompletion] = useState({
    artifactId: artifact.id,
    completed: false
  })
  const playbackCompleted =
    playbackCompletion.artifactId === artifact.id && playbackCompletion.completed
  const setPlaybackCompleted = useCallback((completed: boolean) => {
    setPlaybackCompletion({ artifactId: artifact.id, completed })
  }, [artifact.id])
  const [railOpen, setRailOpen] = useState(false)
  const [railTab, setRailTab] = useState<RailTab>("sections")
  const [masterVolume, setMasterVolume] = useState(0.75)
  const [sections, setSections] = useState<RitualSection[]>(
    artifact.ritualSections ?? []
  )
  const [channels, setChannels] = useState<ArtifactChannels>(
    artifact.channels ?? {}
  )
  const bodyStateKey = `${artifact.id}:${artifact.privacyClass ?? ""}`
  const [bodyCapture, setBodyCapture] = useState<BodyCaptureState>(() =>
    createBodyCaptureState(bodyStateKey, artifact.privacyClass)
  )
  const currentBodyCapture = currentBodyCaptureState(
    bodyCapture,
    bodyStateKey,
    artifact.privacyClass
  )
  const bodyDraft = currentBodyCapture.draft
  const bodyCompletionStatus = currentBodyCapture.completionStatus
  const bodySubmitError = currentBodyCapture.submitError
  const completionIdRef = useRef<{ artifactId: string; completionId: string | null }>({
    artifactId: artifact.id,
    completionId: null
  })
  const currentMsRef = useRef(currentMs)
  const guidanceEventHandlerRef = useRef<((event: RitualSessionEvent) => void) | null>(null)
  const pendingGuidanceEventsRef = useRef<RitualSessionEvent[]>([])
  const hostSessionId = session?.id ?? artifact.sessionId ?? `artifact:${artifact.id}`
  const guidanceSourceRefs = useMemo(() => artifact.sourceRefs ?? [], [artifact.sourceRefs])
  const handleRitualSessionEvent = useCallback(
    (event: RitualSessionEvent) => {
      onSessionEvent?.(event)
      const guidanceHandler = guidanceEventHandlerRef.current
      if (guidanceHandler) {
        guidanceHandler(event)
        return
      }
      pendingGuidanceEventsRef.current.push(event)
      if (pendingGuidanceEventsRef.current.length > 50) {
        pendingGuidanceEventsRef.current.splice(0, pendingGuidanceEventsRef.current.length - 50)
      }
    },
    [onSessionEvent]
  )

  useEffect(() => {
    currentMsRef.current = currentMs
  }, [currentMs])

  const ritualExperience = useRitualExperience({
    artifact,
    sections,
    currentMs,
    completionStatus: bodyCompletionStatus,
    onSessionEvent: handleRitualSessionEvent
  })
  const ritualFrame = ritualExperience.frame
  const rawStageLens = ritualExperience.stageLens as RitualStageLens
  const bodyCaptureAvailable = useMemo(
    () =>
      ritualFrame.availableTracks.includes("body_map") &&
      bodyCaptureAvailableInFrame({
        activeSection: ritualFrame.activeSection,
        completionStatus: bodyCompletionStatus,
        playbackCompleted
      }),
    [bodyCompletionStatus, playbackCompleted, ritualFrame.activeSection, ritualFrame.availableTracks]
  )
  const availableLenses = useMemo(
    () => availableStageLenses(ritualFrame.availableTracks, bodyCaptureAvailable),
    [bodyCaptureAvailable, ritualFrame.availableTracks]
  )
  const selectedStageLens = availableLenses.includes(rawStageLens)
    ? rawStageLens
    : availableLenses[0] ?? rawStageLens
  const stageLens = playbackCompleted && bodyCaptureAvailable ? "body" : selectedStageLens
  const timelineStatus = timelineCompletionStatus(bodyCompletionStatus, playbackCompleted)

  // Immersive ritual state (breath or meditation)
  const [isPlaying, setIsPlaying] = useState(false)
  const breathImmersive = isPlaying && (stageLens === "breath" || stageLens === "meditation")
  const cinemaImmersive =
    stageLens === "cinema" && artifact.stageVideo?.presentation === "full_background"
  const cinemaPlaybackImmersive = cinemaImmersive && isPlaying
  const autoHideChrome = breathImmersive || cinemaPlaybackImmersive
  const ritualImmersive = breathImmersive
  const [showChrome, setShowChrome] = useState(true)
  const chromeHidden = autoHideChrome && !showChrome
  const chromeVisible = !chromeHidden
  const cinemaChromeGlass = cinemaImmersive && chromeVisible
  const backgroundImageUrl = artifact.stageVideo?.posterImageUrl ?? artifact.coverImageUrl

  const declaredDurationMs = Math.max(
    artifact.durationMs ?? 0,
    artifact.captions?.at(-1)?.endMs ?? 0,
    sections.at(-1)?.endMs ?? 0
  )
  const durationMs = declaredDurationMs > 0 ? declaredDurationMs : 60000
  const durationMsRef = useRef(durationMs)
  useEffect(() => {
    durationMsRef.current = durationMs
  }, [durationMs])

  const currentGuidanceFrame = useMemo(
    () =>
      guidanceFrameFromExperienceFrame({
        frame: ritualFrame,
        currentMs,
        durationMs,
        lens: stageLens,
        isPlaying,
        playbackCompleted,
        completionStatus: bodyCompletionStatus
      }),
    [bodyCompletionStatus, currentMs, durationMs, isPlaying, playbackCompleted, ritualFrame, stageLens]
  )
  const guidance = useRitualGuidanceSession({
    artifactId: artifact.id,
    ritualPlanId: artifact.ritualPlanId,
    hostSessionId,
    userId: "local-user",
    privacyClass: artifact.privacyClass,
    sourceRefs: guidanceSourceRefs,
    currentFrame: currentGuidanceFrame
  })
  const recordGuidanceSessionEvent = guidance.recordSessionEvent

  useEffect(() => {
    guidanceEventHandlerRef.current = recordGuidanceSessionEvent
    const pending = pendingGuidanceEventsRef.current.splice(0, pendingGuidanceEventsRef.current.length)
    pending.forEach((event) => recordGuidanceSessionEvent(event))
    return () => {
      guidanceEventHandlerRef.current = null
    }
  }, [recordGuidanceSessionEvent])

  const handleTimeUpdate = useCallback((ms: number) => {
    setCurrentMs(ms)
    if (ms < durationMsRef.current - 1000) {
      setPlaybackCompleted(false)
    }
  }, [setPlaybackCompleted])

  const companionAvailable = Boolean(guidance.guidanceSessionId)
  const visibleRailTab =
    railTab === "body" && !bodyCaptureAvailable
      ? "sections"
      : railTab === "companion" && !companionAvailable
        ? "sections"
        : railTab
  const desktopRail = useMediaQuery("(min-width: 768px)")

  // Auto-hide chrome in immersive modes
  useEffect(() => {
    if (hideTimeoutRef.current) {
      clearTimeout(hideTimeoutRef.current)
      hideTimeoutRef.current = null
    }
    if (!autoHideChrome) return

    hideTimeoutRef.current = setTimeout(() => {
      setShowChrome(false)
    }, cinemaPlaybackImmersive ? 1800 : 3500)

    return () => {
      if (hideTimeoutRef.current) {
        clearTimeout(hideTimeoutRef.current)
      }
    }
  }, [autoHideChrome, cinemaPlaybackImmersive])

  // Pointer movement reveals chrome in immersive modes
  useEffect(() => {
    if (!autoHideChrome) return

    const revealChrome = () => {
      setShowChrome(true)
      if (hideTimeoutRef.current) {
        clearTimeout(hideTimeoutRef.current)
      }
      hideTimeoutRef.current = setTimeout(() => {
        setShowChrome(false)
      }, cinemaPlaybackImmersive ? 1600 : 3000)
    }

    window.addEventListener("mousemove", revealChrome)
    window.addEventListener("touchstart", revealChrome)

    return () => {
      window.removeEventListener("mousemove", revealChrome)
      window.removeEventListener("touchstart", revealChrome)
    }
  }, [autoHideChrome, cinemaPlaybackImmersive])

  useEffect(() => {
    if (!railOpen) return
    const handlePointerDownOutside = (event: PointerEvent) => {
      const path = event.composedPath()
      const clickedInsideRail = railRef.current ? path.includes(railRef.current) : false
      const clickedInsideToggle = toggleRef.current ? path.includes(toggleRef.current) : false

      if (!clickedInsideRail && !clickedInsideToggle) {
        setRailOpen(false)
      }
    }

    document.addEventListener("pointerdown", handlePointerDownOutside, true)
    return () => {
      document.removeEventListener("pointerdown", handlePointerDownOutside, true)
    }
  }, [railOpen])

  const handleToggleSectionMute = useCallback(
    (sectionId: string, muted: boolean) => {
      setSections((prev) =>
        prev.map((s) => (s.id === sectionId ? { ...s, muted } : s))
      )
    },
    []
  )

  const handleToggleChannelMute = useCallback(
    (name: string, muted: boolean) => {
      setChannels((prev) => ({
        ...prev,
        [name]: {
          ...prev[name as keyof ArtifactChannels],
          muted
        }
      }))
    },
    []
  )

  const handleQuickChannelToggle = useCallback(
    (name: ChannelName) => {
      const ch = channels?.[name]
      if (!ch) return
      setChannels((prev) => ({
        ...prev,
        [name]: { ...ch, muted: !ch.muted }
      }))
    },
    [channels]
  )

  const handleQuickChannelGain = useCallback(
    (name: ChannelName, gain: number) => {
      const ch = channels?.[name]
      if (!ch) return
      setChannels((prev) => ({
        ...prev,
        [name]: { ...ch, gain }
      }))
    },
    [channels]
  )

  const handleSeek = useCallback((ms: number) => {
    setPlaybackCompleted(false)
    setCurrentMs(ms)
    playerRef.current?.seek(ms)
  }, [setPlaybackCompleted])

  const handleStageLensChange = useCallback((lens: RitualStageLens) => {
    if (lens === "body" && !bodyCaptureAvailable) return
    ritualExperience.setStageLens(lens)
    setShowChrome(true)
    if (lens === "body") {
      setRailTab("body")
      setRailOpen(true)
    }
  }, [bodyCaptureAvailable, ritualExperience])

  const handlePlayerComplete = useCallback(() => {
    setPlaybackCompleted(true)
    ritualExperience.recordSessionEvent({ type: "ritual_completed" })
    if (!artifact.captureBodyResponse && !artifact.completionEndpoint) return
    ritualExperience.setStageLens("body")
    setRailTab("body")
    setRailOpen(true)
    setShowChrome(true)
  }, [artifact.captureBodyResponse, artifact.completionEndpoint, ritualExperience, setPlaybackCompleted])

  const handlePlayingChange = useCallback((playing: boolean) => {
    setIsPlaying(playing)
    if (playing && (stageLens === "breath" || stageLens === "meditation" || cinemaImmersive)) {
      setRailOpen(false)
      setShowChrome(true)
    }
  }, [cinemaImmersive, stageLens])

  const handleCompanionToggle = useCallback(() => {
    if (railOpen && visibleRailTab === "companion") {
      setRailOpen(false)
      return
    }
    setRailTab(companionAvailable ? "companion" : "sections")
    setRailOpen(true)
    setShowChrome(true)
  }, [companionAvailable, railOpen, visibleRailTab])

  const handleBodyRailToggle = useCallback(() => {
    if (!bodyCaptureAvailable) return
    setRailTab("body")
    setRailOpen(true)
    setShowChrome(true)
  }, [bodyCaptureAvailable])

  const handleContinueLive = useCallback(() => {
    const href = guidance.liveHref
    if (!href) return
    guidance.cacheForLiveRoute()
    router.push(href)
  }, [guidance, router])

  const setBodyCaptureStatus = useCallback(
    (completionStatus: BodyCompletionStatus, submitError: string | null = null) => {
      setBodyCapture((previous) => ({
        ...currentBodyCaptureState(previous, bodyStateKey, artifact.privacyClass),
        completionStatus,
        submitError
      }))
    },
    [artifact.privacyClass, bodyStateKey]
  )

  const handleBodyDraftChange = useCallback((nextDraft: BodyStateDraft) => {
    setBodyCapture((previous) => {
      const current = currentBodyCaptureState(previous, bodyStateKey, artifact.privacyClass)
      return {
        ...current,
        draft: nextDraft,
        completionStatus: current.completionStatus === "error" ? "idle" : current.completionStatus,
        submitError: current.completionStatus === "error" ? null : current.submitError
      }
    })
  }, [artifact.privacyClass, bodyStateKey])

  const handleSubmitCompletion = useCallback(async ({
    includeBodyState,
    reflectionText,
    practiceFeedback
  }: RitualCompletionSubmitPayload) => {
    const bodyState = includeBodyState
      ? buildBodyStatePayload(bodyDraft, artifact.privacyClass)
      : null
    if (includeBodyState && !bodyState) {
      setBodyCaptureStatus("error", "Choose a sensation before holding this body note.")
      return
    }

    if (!artifact.completionEndpoint) {
      setBodyCaptureStatus("error", "Completion sync is not available for this artifact.")
      return
    }

    setBodyCaptureStatus("submitting")

    if (completionIdRef.current.artifactId !== artifact.id) {
      completionIdRef.current = { artifactId: artifact.id, completionId: null }
    }
    if (!completionIdRef.current.completionId) {
      completionIdRef.current.completionId = createCompletionId(artifact.id)
    }
    const completionId = completionIdRef.current.completionId
    const playbackState =
      currentMsRef.current > 0 && currentMsRef.current < durationMsRef.current - 1000
        ? "partial"
        : "completed"

    try {
      const response = await fetch(artifact.completionEndpoint, {
        method: "POST",
        headers: {
          "content-type": "application/json",
          "idempotency-key": completionId
        },
        body: JSON.stringify({
          completionId,
          completedAt: new Date().toISOString(),
          playbackState,
          durationMs: durationMsRef.current,
          completedSections: completedSectionIds(
            sections,
            currentMsRef.current,
            durationMsRef.current
          ),
          ...(bodyState ? { bodyState } : {}),
          ...(reflectionText ? { reflectionText } : {}),
          ...(practiceFeedback ? { practiceFeedback } : {}),
          clientMetadata: {
            surface: "hermes-rituals-web",
            completionPanelVersion: "v1_quiet_memory_loop",
            bodyPickerVersion: "v2_symbolic_body_map",
            bodyMapMode:
              stageLens === "body" ? "stage_full2d_rail_summary" : "rail_compact2d",
            currentMs: Math.round(currentMsRef.current)
          }
        })
      })
      const payload = (await response.json().catch(() => ({}))) as Record<string, unknown>
      if (!response.ok) {
        throw new Error(typeof payload.error === "string" ? payload.error : "completion_save_failed")
      }
      setBodyCaptureStatus("saved")
      if (bodyState) {
        ritualExperience.recordSessionEvent({ type: "body_response_captured" })
      }
    } catch (error) {
      const message = error instanceof Error ? error.message : "completion_save_failed"
      setBodyCaptureStatus("error", message.replaceAll("_", " "))
    }
  }, [
    artifact.completionEndpoint,
    artifact.id,
    artifact.privacyClass,
    bodyDraft,
    sections,
    stageLens,
    ritualExperience,
    setBodyCaptureStatus
  ])

  const renderCompletionPanel = (testId?: string) => (
    <RitualCompletionPanel
      testId={testId}
      bodyDraft={bodyDraft}
      onBodyDraftChange={handleBodyDraftChange}
      completionPrompt={ritualFrame.activeSection?.capturePrompt ?? artifact.completionPrompt}
      completionStatus={bodyCompletionStatus}
      submitError={bodySubmitError}
      endpointAvailable={Boolean(artifact.completionEndpoint)}
      mapMode={stageLens === "body" ? "summary" : "compact2d"}
      disabled={bodyCompletionStatus === "submitting" || bodyCompletionStatus === "saved"}
      onSubmit={handleSubmitCompletion}
    />
  )

  const bodyCompletionOverlayVisible =
    stageLens === "body" && bodyCaptureAvailable && railOpen && visibleRailTab === "body"

  return (
    <div
      data-testid="ritual-artifact-client"
      data-artifact-id={artifact.id}
      className={[
        "relative flex h-[100dvh] flex-col overflow-hidden bg-graphite-950 text-silver-50",
        cinemaImmersive ? "" : "page-shell"
      ].join(" ")}
    >
      {/* Full-bleed artwork background — fades to black in immersive ritual */}
      <AnimatePresence>
        {!ritualImmersive && !cinemaImmersive && backgroundImageUrl && (
          <motion.div
            key="bg-image"
            className="pointer-events-none absolute inset-0"
            initial={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={PANEL_SPRING}
            style={{
              backgroundImage: `url(${backgroundImageUrl})`,
              backgroundSize: "cover",
              backgroundPosition: "center",
              filter: "blur(80px) saturate(0.6) brightness(0.35)",
              transform: "scale(1.15)"
            }}
          />
        )}
      </AnimatePresence>

      {/* Dark overlay — intensifies in immersive */}
      <motion.div
        className="pointer-events-none absolute inset-0"
        animate={{
          backgroundColor: ritualImmersive ? "rgba(0,0,0,0.85)" : "rgba(0,0,0,0)"
        }}
        transition={PANEL_SPRING}
      />
      {!cinemaImmersive && (
        <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_top,rgba(16,19,23,0.4),transparent_60%),radial-gradient(circle_at_bottom_right,rgba(16,19,23,0.5),transparent_50%)]" />
      )}

      {/* Top chrome — fades out in immersive ritual */}
      <motion.header
        className={[
          "flex items-start justify-between gap-4 px-4 py-3 md:px-6",
          cinemaImmersive ? "pointer-events-none absolute inset-x-0 top-0 z-30" : "relative z-10"
        ].join(" ")}
        animate={{
          opacity: chromeHidden ? 0 : 1,
          y: chromeHidden ? -12 : 0
        }}
        transition={PANEL_SPRING}
        style={{
          pointerEvents: chromeHidden ? "none" : "auto"
        }}
      >
        <div
          className={[
            "flex items-start gap-2",
            cinemaChromeGlass
              ? "pointer-events-auto rounded-[1.375rem] border border-white/10 bg-black/35 px-2.5 py-2.5 backdrop-blur-2xl"
              : cinemaImmersive
                ? "pointer-events-auto"
                : ""
          ].join(" ")}
        >
          <motion.button
            type="button"
            onClick={() => router.back()}
            className="flex size-8 items-center justify-center rounded-full bg-white/10 text-white/80 backdrop-blur-sm"
            aria-label="Go back"
            whileHover={{ scale: 1.05, backgroundColor: "rgba(255,255,255,0.20)" }}
            whileTap={{ scale: 0.94 }}
            transition={MICRO_SPRING}
          >
            <ArrowLeft className="size-4" />
          </motion.button>
          <div className="flex flex-col gap-2 pt-0.5">
            <div className="flex flex-col">
              <span className="text-[10px] font-medium uppercase tracking-wider text-silver-400">
                {artifact.mode}
              </span>
              <span className="max-w-[40vw] truncate text-sm font-medium text-silver-100">
                {artifact.title}
              </span>
            </div>
            {availableLenses.length > 1 ? (
              <div className="flex flex-wrap items-center gap-1.5">
                <span className="text-[10px] font-medium uppercase tracking-[0.18em] text-silver-600">
                  Lens
                </span>
                <RitualLensSwitch
                  activeLens={stageLens}
                  availableLenses={availableLenses}
                  onChange={handleStageLensChange}
                />
              </div>
            ) : null}
          </div>
        </div>

        <div className={cinemaImmersive ? "pointer-events-auto" : ""}>
          <LiquidMixer
            channels={channels}
            masterVolume={masterVolume}
            glassy={cinemaChromeGlass}
            onMasterChange={setMasterVolume}
            onChannelToggle={handleQuickChannelToggle}
            onChannelGainChange={handleQuickChannelGain}
          />
        </div>
      </motion.header>

      <motion.div
        className={[
          cinemaImmersive
            ? "pointer-events-auto absolute inset-x-4 top-36 z-20 md:inset-x-6 md:top-40"
            : "relative z-10 px-4 pb-2 md:px-6",
          chromeHidden ? "pointer-events-auto" : ""
        ].join(" ")}
        initial={false}
        animate={{
          opacity: chromeHidden ? 0.36 : 1,
          y: chromeHidden ? -6 : 0
        }}
        transition={PANEL_SPRING}
      >
        <RitualTimelineProgress
          currentMs={currentMs}
          durationMs={durationMs}
          sections={sections}
          activeSection={ritualFrame.activeSection}
          completionStatus={timelineStatus}
          onSeek={handleSeek}
        />
      </motion.div>

      {/* Main layout — spring-driven shared flex space */}
      <motion.main
        className="relative z-10 flex min-h-0 flex-1"
        layout
      >
        {/* Left stage — flex-1, shrinks as panel expands */}
        <motion.section
          className="relative z-10 flex min-h-0 min-w-0 flex-1 flex-col"
          layout
        >
          <RitualPlayer
            ref={playerRef}
            artifact={artifact}
            sections={sections}
            stageLens={stageLens}
            channels={channels}
            masterVolume={masterVolume}
            playerMode={
              stageLens === "breath" || stageLens === "meditation" || stageLens === "body"
                ? "minimal"
                : "full"
            }
            immersive={ritualImmersive}
            chromeVisible={chromeVisible}
            bodyDraft={bodyDraft}
            bodyCompletionStatus={bodyCompletionStatus}
            bodySubmitError={bodySubmitError}
            activeSection={ritualFrame.activeSection}
            bodyPromptMode={ritualFrame.bodyPromptMode}
            onBodyDraftChange={handleBodyDraftChange}
            onBodySubmit={() => handleSubmitCompletion({ includeBodyState: true })}
            onComplete={handlePlayerComplete}
            onTimeUpdate={handleTimeUpdate}
            onPlayingChange={handlePlayingChange}
          />
          {stageLens === "body" && bodyCaptureAvailable && !railOpen ? (
            <motion.button
              type="button"
              data-testid="ritual-open-completion-panel"
              aria-label="Open completion panel"
              onClick={() => {
                setRailTab("body")
                setRailOpen(true)
                setShowChrome(true)
              }}
              className="absolute bottom-5 right-5 z-30 inline-flex h-11 items-center gap-2 rounded-full border border-white/15 bg-white/12 px-4 text-sm font-medium text-silver-50 shadow-[0_18px_60px_rgba(0,0,0,0.34)] backdrop-blur-2xl hover:bg-white/18"
              whileHover={{ scale: 1.02 }}
              whileTap={{ scale: 0.98 }}
              transition={MICRO_SPRING}
            >
              <CheckCircle2 className="size-4" />
              <span>Save body detail</span>
            </motion.button>
          ) : null}
        </motion.section>

        {/* Right panel — desktop rail, mobile bottom sheet */}
        <motion.aside
          ref={railRef}
          className={[
            "z-30 h-full max-w-[100dvw] shrink-0 overflow-hidden border-white/5 bg-black/35 backdrop-blur-2xl md:bg-transparent md:backdrop-blur-none",
            desktopRail ? "relative border-l" : "fixed inset-x-0 bottom-0 border-t"
          ].join(" ")}
          layout
          initial={false}
          animate={
            desktopRail
              ? { width: railOpen ? 420 : 0 }
              : { width: "100dvw", height: railOpen ? "72dvh" : 0 }
          }
          transition={PANEL_SPRING}
        >
          <div className="flex h-full w-full flex-col md:w-[min(100dvw,420px)]">
            {/* Rail content */}
            <div className="min-h-0 flex-1 overflow-y-auto px-5 pb-6 pt-4">
              <RitualRail
                artifact={artifact}
                currentMs={currentMs}
                sections={sections}
                channels={channels}
                activeTab={visibleRailTab}
                onTabChange={setRailTab}
                onToggleSectionMute={handleToggleSectionMute}
                onToggleChannelMute={handleToggleChannelMute}
                onChannelGainChange={handleQuickChannelGain}
                onSeek={handleSeek}
                showBodyTab={bodyCaptureAvailable}
                bodyPanel={
                  bodyCaptureAvailable
                    ? renderCompletionPanel("ritual-completion-panel-rail")
                    : undefined
                }
                showCompanionTab={companionAvailable}
                companionPanel={
                  companionAvailable ? (
                    <RitualCompanionPanel
                      guidanceSessionId={guidance.guidanceSessionId}
                      guidanceStatus={guidance.status}
                      guidanceError={guidance.error}
                      playbackCompleted={playbackCompleted}
                      liveHref={guidance.liveHref}
                      getChatContext={guidance.getChatContext}
                      onContinueLive={handleContinueLive}
                    />
                  ) : undefined
                }
              />
            </div>
          </div>
        </motion.aside>

        <AnimatePresence>
          {bodyCompletionOverlayVisible ? (
            <motion.div
              key="body-completion-overlay"
              className="absolute bottom-4 right-4 top-4 z-40 w-[min(100dvw-2rem,420px)] overflow-y-auto rounded-2xl border border-white/10 bg-black/55 p-5 shadow-[0_24px_90px_rgba(0,0,0,0.42)] backdrop-blur-2xl"
              initial={{ opacity: 0, x: 20 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: 16 }}
              transition={PANEL_SPRING}
            >
              {renderCompletionPanel("ritual-completion-panel-overlay")}
            </motion.div>
          ) : null}
        </AnimatePresence>
      </motion.main>

      {/* Bottom-right toggle buttons — fade out in immersive */}
      <motion.div
        className={[
          "pointer-events-none absolute inset-x-0 z-20 flex justify-end px-5 md:px-8",
          cinemaPlaybackImmersive ? "bottom-20 pb-0 md:bottom-24" : "bottom-0 pb-5 md:pb-8"
        ].join(" ")}
        animate={{
          opacity: chromeHidden ? 0 : 1,
          y: chromeHidden ? 12 : 0
        }}
        transition={PANEL_SPRING}
        style={{ pointerEvents: "none" }}
      >
        <div
          ref={toggleRef}
          className={[
            "flex items-center gap-2 rounded-full bg-black/40 p-1.5 backdrop-blur-xl",
            chromeHidden ? "pointer-events-none" : "pointer-events-auto"
          ].join(" ")}
        >
          {bodyCaptureAvailable ? (
            <>
              <motion.button
                type="button"
                data-testid="ritual-body-rail-toggle"
                onClick={handleBodyRailToggle}
                className={[
                  "flex size-10 items-center justify-center rounded-full",
                  railOpen && visibleRailTab === "body"
                    ? "bg-white/20 text-white"
                    : "bg-transparent text-silver-400 hover:text-silver-100"
                ].join(" ")}
                aria-label="Open completion"
                whileHover={{ scale: 1.05 }}
                whileTap={{ scale: 0.94 }}
                transition={MICRO_SPRING}
              >
                <CheckCircle2 className="size-4.5" />
              </motion.button>
              <div className="h-5 w-px bg-white/15" />
            </>
          ) : null}
          <motion.button
            type="button"
            data-testid="ritual-companion-toggle"
            onClick={handleCompanionToggle}
            className={[
              "flex size-10 items-center justify-center rounded-full",
              railOpen && visibleRailTab === "companion"
                ? "bg-white/20 text-white"
                : "bg-transparent text-silver-400 hover:text-silver-100"
            ].join(" ")}
            aria-label="Open companion"
            whileHover={{ scale: 1.05 }}
            whileTap={{ scale: 0.94 }}
            transition={MICRO_SPRING}
          >
            <MessageSquareText className="size-4.5" />
          </motion.button>
          <div className="h-5 w-px bg-white/15" />
          <button
            type="button"
            disabled
            className="flex size-10 cursor-default items-center justify-center rounded-full bg-transparent text-silver-600"
            aria-label="Playlist (coming soon)"
          >
            <ListMusic className="size-4.5" />
          </button>
        </div>
      </motion.div>
    </div>
  )
}
