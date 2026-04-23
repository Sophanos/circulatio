"use client"

import { useCallback, useEffect, useRef, useState } from "react"
import { ArrowLeft, ListMusic, MessageSquareText, Volume2, VolumeX } from "lucide-react"
import * as SliderPrimitive from "@radix-ui/react-slider"

import { useRouter } from "next/navigation"
import { motion, AnimatePresence } from "motion/react"

import {
  RitualPlayer,
  type RitualPlayerHandle,
  type RitualStageLens,
  type PlayerMode
} from "@/components/ritual/RitualPlayer"
import { RitualRail, type RailTab } from "@/components/ritual/RitualRail"
import type {
  ArtifactChannels,
  PresentationArtifact,
  RitualSection,
  SessionShell
} from "@/lib/artifact-contract"

const SPRING = { type: "spring" as const, stiffness: 300, damping: 30, mass: 0.8 }
const MORPH = { type: "spring" as const, stiffness: 450, damping: 28, mass: 0.5 }

const CHANNEL_ORDER = ["voice", "ambient", "breath", "pulse", "music"] as const
const RITUAL_LENS_OPTIONS: RitualStageLens[] = ["cinema", "photo", "breath"]
type ChannelName = (typeof CHANNEL_ORDER)[number]

function LiquidMixer({
  channels,
  masterVolume,
  onMasterChange,
  onChannelToggle,
  onChannelGainChange
}: {
  channels?: ArtifactChannels
  masterVolume: number
  onMasterChange: (v: number) => void
  onChannelToggle: (name: ChannelName) => void
  onChannelGainChange: (name: ChannelName, gain: number) => void
}) {
  const [hovered, setHovered] = useState(false)
  const [hoveredChannel, setHoveredChannel] = useState<ChannelName | null>(null)
  const isMuted = masterVolume === 0

  return (
    <motion.div
      className="relative flex flex-col overflow-hidden"
      style={{ backgroundColor: "rgba(255,255,255,0.02)" }}
      layout
      initial={false}
      animate={{
        width: hovered ? 240 : 36,
        height: hovered ? 248 : 36,
        borderRadius: hovered ? 20 : 18
      }}
      transition={MORPH}
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
        <button
          type="button"
          onClick={() => onMasterChange(isMuted ? 0.75 : 0)}
          className="flex size-7 shrink-0 items-center justify-center rounded-full text-silver-300 transition-colors hover:text-white"
        >
          {isMuted ? <VolumeX className="size-4" /> : <Volume2 className="size-4" />}
        </button>

        <AnimatePresence>
          {hovered && (
            <motion.div
              className="flex flex-1 items-center"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              transition={{ duration: 0.12, delay: 0.04 }}
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
            className="flex flex-col px-3 pb-3 pt-2"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.15, delay: 0.06 }}
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
                      "flex items-center gap-3 rounded-lg px-2 py-2 transition-colors",
                      muted
                        ? "text-silver-500"
                        : "text-silver-100 hover:bg-white/[0.04]"
                    ].join(" ")}
                    onMouseEnter={() => setHoveredChannel(name)}
                    onMouseLeave={() => setHoveredChannel((prev) => (prev === name ? null : prev))}
                  >
                    <button
                      type="button"
                      onClick={() => onChannelToggle(name)}
                      className="flex size-6 shrink-0 items-center justify-center rounded-full transition-colors"
                    >
                      {muted ? (
                        <VolumeX className="size-4" />
                      ) : (
                        <Volume2 className="size-4" />
                      )}
                    </button>

                    <div className="flex min-w-0 flex-1 items-center">
                      <AnimatePresence mode="popLayout">
                        {isChannelHovered && !muted ? (
                          <motion.div
                            key="slider"
                            className="flex flex-1 items-center"
                            initial={{ opacity: 0, width: 0 }}
                            animate={{ opacity: 1, width: "auto" }}
                            exit={{ opacity: 0, width: 0 }}
                            transition={{ duration: 0.15 }}
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
                            transition={{ duration: 0.1 }}
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
  onChange
}: {
  activeLens: RitualStageLens
  onChange: (lens: RitualStageLens) => void
}) {
  return (
    <div
      className="flex items-center gap-1 rounded-full p-1"
      style={{ backgroundColor: "rgba(255,255,255,0.03)" }}
    >
      {RITUAL_LENS_OPTIONS.map((lens) => {
        const active = activeLens === lens

        return (
          <button
            key={lens}
            type="button"
            onClick={() => onChange(lens)}
            className="relative flex items-center justify-center rounded-full px-2.5 py-1"
          >
            {active && (
              <motion.div
                layoutId="ritual-lens-pill"
                className="absolute inset-0 rounded-full bg-white/[0.10]"
                transition={SPRING}
              />
            )}
            <span
              className={[
                "relative text-[10px] font-medium uppercase leading-none tracking-[0.18em]",
                active ? "text-silver-100" : "text-silver-500"
              ].join(" ")}
            >
              {lens}
            </span>
          </button>
        )
      })}
    </div>
  )
}

export function RitualArtifactClient({
  artifact,
  session
}: {
  artifact: PresentationArtifact
  session?: SessionShell
}) {
  const router = useRouter()
  const playerRef = useRef<RitualPlayerHandle>(null)
  const railRef = useRef<HTMLElement>(null)
  const toggleRef = useRef<HTMLDivElement>(null)
  const [currentMs, setCurrentMs] = useState(0)
  const [railOpen, setRailOpen] = useState(false)
  const [railTab, setRailTab] = useState<RailTab>("sections")
  const [stageLens, setStageLens] = useState<RitualStageLens>(() =>
    artifact.stageVideo || (artifact.videoUrl && !artifact.videoUrl.startsWith("mock://"))
      ? "cinema"
      : "breath"
  )
  const [masterVolume, setMasterVolume] = useState(0.75)
  const [sections, setSections] = useState<RitualSection[]>(
    artifact.ritualSections ?? []
  )
  const [channels, setChannels] = useState<ArtifactChannels>(
    artifact.channels ?? {}
  )
  const backgroundImageUrl = artifact.stageVideo?.posterImageUrl ?? artifact.coverImageUrl
  const immersiveStage = artifact.stageVideo?.presentation === "full_background"
  const [immersiveUiVisible, setImmersiveUiVisible] = useState(immersiveStage)

  const revealImmersiveUi = useCallback(() => {
    if (!immersiveStage) return
    setImmersiveUiVisible(true)
  }, [immersiveStage])

  useEffect(() => {
    setImmersiveUiVisible(immersiveStage)
  }, [immersiveStage])

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

  useEffect(() => {
    if (!immersiveStage || railOpen || !immersiveUiVisible) return

    const timeout = window.setTimeout(() => {
      setImmersiveUiVisible(false)
    }, 2200)

    return () => window.clearTimeout(timeout)
  }, [immersiveStage, immersiveUiVisible, railOpen, stageLens])

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
    playerRef.current?.seek(ms)
  }, [])

  return (
    <div
      className={[
        "relative flex h-[100dvh] flex-col overflow-hidden bg-graphite-950 text-silver-50",
        immersiveStage ? "" : "page-shell"
      ].join(" ")}
      onPointerMove={immersiveStage ? revealImmersiveUi : undefined}
      onPointerDown={immersiveStage ? revealImmersiveUi : undefined}
      onTouchStart={immersiveStage ? revealImmersiveUi : undefined}
      onKeyDown={immersiveStage ? revealImmersiveUi : undefined}
      tabIndex={immersiveStage ? 0 : -1}
    >
      {/* Full-bleed artwork background */}
      {!immersiveStage && backgroundImageUrl && (
        <div
          className="pointer-events-none absolute inset-0"
          style={{
            backgroundImage: `url(${backgroundImageUrl})`,
            backgroundSize: "cover",
            backgroundPosition: "center",
            filter: "blur(80px) saturate(0.6) brightness(0.35)",
            transform: "scale(1.15)"
          }}
        />
      )}
      {!immersiveStage && (
        <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_top,rgba(16,19,23,0.4),transparent_60%),radial-gradient(circle_at_bottom_right,rgba(16,19,23,0.5),transparent_50%)]" />
      )}

      {/* Top chrome */}
      {!immersiveStage && (
        <header className="relative z-10 flex items-start justify-between gap-4 px-4 py-3 md:px-6">
          <div className="flex items-start gap-2">
            <button
              type="button"
              onClick={() => router.back()}
              className="flex size-8 items-center justify-center rounded-full bg-white/10 text-white/80 backdrop-blur-sm transition-colors hover:bg-white/20"
              aria-label="Go back"
            >
              <ArrowLeft className="size-4" />
            </button>
            <div className="flex flex-col gap-2 pt-0.5">
              <div className="flex flex-col">
                <span className="text-[10px] font-medium uppercase tracking-wider text-silver-400">
                  {artifact.mode}
                </span>
                <span className="max-w-[40vw] truncate text-sm font-medium text-silver-100">
                  {artifact.title}
                </span>
              </div>
              <div className="flex flex-wrap items-center gap-1.5">
                <span className="text-[10px] font-medium uppercase tracking-[0.18em] text-silver-600">
                  Lens
                </span>
                <RitualLensSwitch activeLens={stageLens} onChange={setStageLens} />
              </div>
            </div>
          </div>

          <LiquidMixer
            channels={channels}
            masterVolume={masterVolume}
            onMasterChange={setMasterVolume}
            onChannelToggle={handleQuickChannelToggle}
            onChannelGainChange={handleQuickChannelGain}
          />
        </header>
      )}

      {immersiveStage && (
        <AnimatePresence>
          {immersiveUiVisible && (
            <motion.header
              className="pointer-events-none absolute inset-x-0 top-0 z-20 px-4 py-4 md:px-6"
              initial={{ opacity: 0, y: -18 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -12 }}
              transition={SPRING}
            >
              <div className="flex items-start justify-between gap-4">
                <div className="pointer-events-auto flex items-start gap-3 rounded-[1.75rem] border border-white/10 bg-black/35 px-3 py-3 backdrop-blur-2xl">
                  <button
                    type="button"
                    onClick={() => router.back()}
                    className="flex size-9 items-center justify-center rounded-full bg-white/10 text-white/80 transition-colors hover:bg-white/20"
                    aria-label="Go back"
                  >
                    <ArrowLeft className="size-4" />
                  </button>
                  <div className="flex min-w-0 flex-col gap-2 pt-0.5">
                    <div className="flex flex-col">
                      <span className="text-[10px] font-medium uppercase tracking-wider text-silver-500">
                        {artifact.mode}
                      </span>
                      <span className="max-w-[52vw] truncate text-sm font-medium text-silver-100">
                        {artifact.title}
                      </span>
                    </div>
                    <div className="flex flex-wrap items-center gap-1.5">
                      <span className="text-[10px] font-medium uppercase tracking-[0.18em] text-silver-600">
                        Lens
                      </span>
                      <RitualLensSwitch activeLens={stageLens} onChange={setStageLens} />
                    </div>
                  </div>
                </div>

                <div className="pointer-events-auto">
                  <LiquidMixer
                    channels={channels}
                    masterVolume={masterVolume}
                    onMasterChange={setMasterVolume}
                    onChannelToggle={handleQuickChannelToggle}
                    onChannelGainChange={handleQuickChannelGain}
                  />
                </div>
              </div>
            </motion.header>
          )}
        </AnimatePresence>
      )}

      {/* Main layout — spring-driven shared flex space */}
      <motion.main
        className="relative z-10 flex min-h-0 flex-1"
        layout
      >
        {/* Left stage — flex-1, shrinks as panel expands */}
        <motion.section
          className="relative z-10 flex min-h-0 flex-1 flex-col"
          layout
        >
          <RitualPlayer
            ref={playerRef}
            artifact={artifact}
            sections={sections}
            stageLens={stageLens}
            playerMode={stageLens === "breath" ? "minimal" : "full"}
            immersiveUiVisible={immersiveUiVisible}
            onTimeUpdate={setCurrentMs}
          />
        </motion.section>

        {/* Right panel — takes real space, spring width animation */}
        <motion.aside
          ref={railRef}
          className="relative z-30 overflow-hidden border-l border-white/5"
          layout
          initial={false}
          animate={{ width: railOpen ? 420 : 0 }}
          transition={SPRING}
        >
          <div className="flex h-full w-[420px] flex-col">
            <div className="min-h-0 flex-1 overflow-y-auto px-5 pb-6 pt-4">
              <RitualRail
                artifact={artifact}
                currentMs={currentMs}
                sections={sections}
                channels={channels}
                activeTab={railTab}
                onTabChange={setRailTab}
                onToggleSectionMute={handleToggleSectionMute}
                onToggleChannelMute={handleToggleChannelMute}
                onChannelGainChange={handleQuickChannelGain}
                onSeek={handleSeek}
              />
            </div>
          </div>
        </motion.aside>
      </motion.main>

      {/* Bottom-right toggle buttons */}
      {(!immersiveStage || immersiveUiVisible) && (
        <motion.div
          className="pointer-events-none absolute inset-x-0 bottom-0 z-20 flex justify-end px-5 pb-5 md:px-8 md:pb-8"
          initial={immersiveStage ? { opacity: 0, y: 18 } : false}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: 18 }}
          transition={SPRING}
        >
          <div ref={toggleRef} className="pointer-events-auto flex items-center gap-2 rounded-full bg-black/40 p-1.5 backdrop-blur-xl">
            <button
              type="button"
              onClick={() => {
                if (!railOpen) {
                  setRailTab((prev) => (prev === "queue" ? "sections" : prev))
                  setRailOpen(true)
                  setImmersiveUiVisible(true)
                  return
                }

                if (railTab === "queue") {
                  setRailTab("sections")
                  setImmersiveUiVisible(true)
                  return
                }

                setRailOpen(false)
              }}
              className={[
                "flex size-10 items-center justify-center rounded-full transition-colors",
                railOpen && railTab !== "queue"
                  ? "bg-white/20 text-white"
                  : "bg-transparent text-silver-400 hover:text-silver-100"
              ].join(" ")}
              aria-label="Toggle transcript and sections"
            >
              <MessageSquareText className="size-4.5" />
            </button>
            <div className="h-5 w-px bg-white/15" />
            <button
              type="button"
              onClick={() => {
                setRailTab("queue")
                setRailOpen(true)
                setImmersiveUiVisible(true)
              }}
              className={[
                "flex size-10 items-center justify-center rounded-full transition-colors",
                railOpen && railTab === "queue"
                  ? "bg-white/20 text-white"
                  : "bg-transparent text-silver-400 hover:text-silver-100"
              ].join(" ")}
              aria-label="Open ritual queue"
            >
              <ListMusic className="size-4.5" />
            </button>
          </div>
        </motion.div>
      )}
    </div>
  )
}
