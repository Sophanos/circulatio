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
const RITUAL_LENS_OPTIONS: RitualStageLens[] = ["cinema", "photo", "breath", "meditation"]
const RITUAL_LENS_LABELS: Record<RitualStageLens, string> = {
  cinema: "cinema",
  photo: "photo",
  breath: "breath",
  meditation: "med"
}
type ChannelName = (typeof CHANNEL_ORDER)[number]

function formatTimestamp(value: number) {
  if (!Number.isFinite(value) || value < 0) return "0:00"
  const totalSeconds = Math.floor(value)
  const minutes = Math.floor(totalSeconds / 60)
  const seconds = totalSeconds % 60
  return `${minutes}:${seconds.toString().padStart(2, "0")}`
}

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
  session
}: {
  artifact: PresentationArtifact
  session?: SessionShell
}) {
  const router = useRouter()
  const playerRef = useRef<RitualPlayerHandle>(null)
  const railRef = useRef<HTMLElement>(null)
  const toggleRef = useRef<HTMLDivElement>(null)
  const hideTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null)

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

  // Immersive breath state
  const [isPlaying, setIsPlaying] = useState(false)
  const immersive = isPlaying && stageLens === "breath"
  const [showChrome, setShowChrome] = useState(true)

  const durationMs = artifact.captions?.at(-1)?.endMs ?? 60000
  const sessionProgress = Math.min(currentMs / durationMs, 1)
  const remainingSeconds = Math.max(Math.floor((durationMs - currentMs) / 1000), 0)

  // Auto-hide chrome in immersive mode
  useEffect(() => {
    if (!immersive) {
      setShowChrome(true)
      if (hideTimeoutRef.current) {
        clearTimeout(hideTimeoutRef.current)
        hideTimeoutRef.current = null
      }
      return
    }

    // When entering immersive, initially show chrome then fade
    setShowChrome(true)
    hideTimeoutRef.current = setTimeout(() => {
      setShowChrome(false)
    }, 3500)

    return () => {
      if (hideTimeoutRef.current) {
        clearTimeout(hideTimeoutRef.current)
      }
    }
  }, [immersive])

  // Mouse move reveals chrome in immersive mode
  useEffect(() => {
    if (!immersive) return

    const handleMouseMove = () => {
      setShowChrome(true)
      if (hideTimeoutRef.current) {
        clearTimeout(hideTimeoutRef.current)
      }
      hideTimeoutRef.current = setTimeout(() => {
        setShowChrome(false)
      }, 3000)
    }

    window.addEventListener("mousemove", handleMouseMove)
    window.addEventListener("touchstart", handleMouseMove)

    return () => {
      window.removeEventListener("mousemove", handleMouseMove)
      window.removeEventListener("touchstart", handleMouseMove)
    }
  }, [immersive])

  // Close rail when entering immersive
  useEffect(() => {
    if (immersive) {
      setRailOpen(false)
    }
  }, [immersive])

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
    playerRef.current?.seek(ms)
  }, [])

  return (
    <div className="page-shell relative flex h-[100dvh] flex-col overflow-hidden bg-graphite-950 text-silver-50">
      {/* Full-bleed artwork background — fades to black in immersive breath */}
      <AnimatePresence>
        {!immersive && artifact.coverImageUrl && (
          <motion.div
            key="bg-image"
            className="pointer-events-none absolute inset-0"
            initial={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 1.2, ease: "easeInOut" }}
            style={{
              backgroundImage: `url(${artifact.coverImageUrl})`,
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
          backgroundColor: immersive ? "rgba(0,0,0,0.85)" : "transparent"
        }}
        transition={{ duration: 1.2, ease: "easeInOut" }}
      />
      <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_top,rgba(16,19,23,0.4),transparent_60%),radial-gradient(circle_at_bottom_right,rgba(16,19,23,0.5),transparent_50%)]" />

      {/* Top chrome — fades out in immersive breath */}
      <motion.header
        className="relative z-10 flex items-start justify-between gap-4 px-4 py-3 md:px-6"
        animate={{
          opacity: immersive && !showChrome ? 0 : 1,
          y: immersive && !showChrome ? -12 : 0
        }}
        transition={{ duration: 0.5, ease: "easeInOut" }}
        style={{ pointerEvents: immersive && !showChrome ? "none" : "auto" }}
      >
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
      </motion.header>

      {/* Subtle top progress bar — always visible in immersive, very dim */}
      {immersive && (
        <motion.div
          className="absolute left-0 right-0 top-0 z-40"
          initial={{ opacity: 0 }}
          animate={{ opacity: showChrome ? 0.6 : 0.25 }}
          transition={{ duration: 0.5 }}
        >
          <div className="h-[2px] w-full bg-white/5">
            <motion.div
              className="h-full bg-white/30"
              style={{ width: `${sessionProgress * 100}%` }}
              transition={{ duration: 0.3 }}
            />
          </div>
          {/* Dimmed timer */}
          <div className="flex justify-center pt-2">
            <span className="text-[11px] font-medium tabular-nums tracking-wide text-silver-600">
              {formatTimestamp(remainingSeconds)} left
            </span>
          </div>
        </motion.div>
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
            playerMode={stageLens === "breath" || stageLens === "meditation" ? "minimal" : "full"}
            immersive={immersive}
            onTimeUpdate={setCurrentMs}
            onPlayingChange={setIsPlaying}
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
            {/* Rail content */}
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

      {/* Bottom-right toggle buttons — fade out in immersive */}
      <motion.div
        className="pointer-events-none absolute inset-x-0 bottom-0 z-20 flex justify-end px-5 pb-5 md:px-8 md:pb-8"
        animate={{
          opacity: immersive && !showChrome ? 0 : 1,
          y: immersive && !showChrome ? 12 : 0
        }}
        transition={{ duration: 0.5, ease: "easeInOut" }}
        style={{ pointerEvents: immersive && !showChrome ? "none" : "auto" }}
      >
        <div ref={toggleRef} className="pointer-events-auto flex items-center gap-2 rounded-full bg-black/40 p-1.5 backdrop-blur-xl">
          <button
            type="button"
            onClick={() => setRailOpen(!railOpen)}
            className={[
              "flex size-10 items-center justify-center rounded-full transition-colors",
              railOpen
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
