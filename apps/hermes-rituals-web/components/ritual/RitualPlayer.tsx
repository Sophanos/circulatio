"use client"

import { useEffect, useImperativeHandle, useRef, useState, forwardRef } from "react"
import { Pause, Play } from "lucide-react"
import { AnimatePresence, motion } from "motion/react"

import { BreathStage } from "@/components/ritual/BreathStage"
import { CaptionStack } from "@/components/ritual/CaptionStack"
import { MatrixField } from "@/components/ritual/MatrixField"
import { ScrollingWaveform } from "@/components/ui/waveform"
import {
  ScrubBarContainer,
  ScrubBarProgress,
  ScrubBarThumb,
  ScrubBarTimeLabel,
  ScrubBarTrack
} from "@/components/ui/scrub-bar"
import type { PresentationArtifact, RitualSection, CaptionCue } from "@/lib/artifact-contract"
import { makeSilentWavBlobUrl } from "@/lib/mock-media"

export type RitualPlayerHandle = {
  seek: (ms: number) => void
}

export type RitualStageLens = "cinema" | "photo" | "breath"
export type PlayerMode = "full" | "minimal"

const SPRING = { type: "spring" as const, stiffness: 300, damping: 30, mass: 0.8 }

function formatTimestamp(value: number) {
  if (!Number.isFinite(value) || value < 0) return "0:00"
  const totalSeconds = Math.floor(value)
  const minutes = Math.floor(totalSeconds / 60)
  const seconds = totalSeconds % 60
  return `${minutes}:${seconds.toString().padStart(2, "0")}`
}

function VisualStage({
  artifact,
  currentMs,
  isPlaying,
  stageLens
}: {
  artifact: PresentationArtifact
  currentMs: number
  isPlaying: boolean
  stageLens: RitualStageLens
}) {
  const scenes = artifact.scenes ?? []
  const activeScene = scenes.find(
    (scene) => currentMs >= (scene.startMs ?? 0) && currentMs < (scene.endMs ?? Infinity)
  )
  const activeId = activeScene?.id
  const hasRealVideo = Boolean(artifact.videoUrl && !artifact.videoUrl.startsWith("mock://"))

  if (stageLens === "breath") {
    return (
      <BreathStage cycle={artifact.breathCycle} currentMs={currentMs} isPlaying={isPlaying} />
    )
  }

  if (stageLens === "cinema" && hasRealVideo) {
    return (
      <motion.div
        key="cinema-video"
        className="relative h-full w-full overflow-hidden rounded-3xl shadow-2xl"
        layout
        initial={{ opacity: 0, scale: 0.985 }}
        animate={{ opacity: 1, scale: 1 }}
        exit={{ opacity: 0, scale: 1.01 }}
        transition={SPRING}
      >
        <video
          src={artifact.videoUrl}
          className="h-full w-full object-cover"
          playsInline
          muted
          loop
          autoPlay
        />
        <div className="absolute inset-0 bg-[radial-gradient(circle_at_top,rgba(255,255,255,0.12),transparent_34%),linear-gradient(180deg,rgba(16,19,23,0.1)_0%,rgba(16,19,23,0.7)_100%)]" />
        <div className="absolute left-4 top-4 rounded-full bg-black/20 px-3 py-1.5 text-[10px] font-medium uppercase tracking-[0.18em] text-silver-300 backdrop-blur-xl">
          Cinema
        </div>
      </motion.div>
    )
  }

  if (!scenes.length) {
    return (
      <motion.div
        key={`${stageLens}-cover`}
        className="relative h-full w-full overflow-hidden rounded-3xl shadow-2xl"
        layout
        initial={{ opacity: 0, scale: 0.985 }}
        animate={{ opacity: 1, scale: 1 }}
        exit={{ opacity: 0, scale: 1.01 }}
        transition={SPRING}
      >
        {stageLens === "cinema" && <MatrixField currentMs={currentMs} />}
        {artifact.coverImageUrl && (
          <img
            src={artifact.coverImageUrl}
            alt={artifact.title}
            className="h-full w-full object-cover"
          />
        )}
        <div className="absolute inset-0 bg-gradient-to-t from-black/50 via-transparent to-transparent" />
        <div className="absolute left-4 top-4 rounded-full bg-black/20 px-3 py-1.5 text-[10px] font-medium uppercase tracking-[0.18em] text-silver-300 backdrop-blur-xl">
          {stageLens === "cinema" ? "Cinema" : "Photo"}
        </div>
      </motion.div>
    )
  }

  return (
    <motion.div
      key={stageLens}
      className="relative h-full w-full overflow-hidden rounded-3xl shadow-2xl"
      layout
      initial={{ opacity: 0, scale: 0.985 }}
      animate={{ opacity: 1, scale: 1 }}
      exit={{ opacity: 0, scale: 1.01 }}
      transition={SPRING}
    >
      {stageLens === "cinema" && <MatrixField currentMs={currentMs} />}
      {scenes.map((scene) => (
        <img
          key={scene.id}
          src={scene.imageUrl}
          alt={scene.title}
          className={[
            "absolute inset-0 h-full w-full object-cover transition-all duration-1000 ease-out",
            scene.id === activeId ? "opacity-100 scale-100" : "opacity-0 scale-105"
          ].join(" ")}
        />
      ))}
      <div className="absolute inset-0 bg-gradient-to-t from-black/50 via-transparent to-transparent" />
      <div className="absolute left-4 top-4 rounded-full bg-black/20 px-3 py-1.5 text-[10px] font-medium uppercase tracking-[0.18em] text-silver-300 backdrop-blur-xl">
        {stageLens === "cinema" ? "Cinema" : "Photo"}
      </div>
      {isPlaying && activeScene && (
        <div className="absolute bottom-4 left-4 rounded-lg bg-black/30 px-3 py-1.5 text-xs font-medium text-white/90 backdrop-blur-md">
          {activeScene.title}
        </div>
      )}
    </motion.div>
  )
}

function MinimalCaption({
  captions,
  currentMs,
  muted
}: {
  captions: CaptionCue[]
  currentMs: number
  muted?: boolean
}) {
  const active = captions.find(
    (c) => currentMs >= c.startMs && currentMs < c.endMs
  )

  return (
    <div className="flex min-h-[1.5rem] items-center justify-center px-4">
      <AnimatePresence mode="wait">
        {active ? (
          <motion.p
            key={`${active.startMs}-${active.endMs}`}
            initial={{ opacity: 0, y: 3 }}
            animate={{ opacity: muted ? 0.3 : 0.85, y: 0 }}
            exit={{ opacity: 0, y: -3 }}
            transition={{ duration: 0.25 }}
            className="max-w-md text-center text-sm font-medium leading-snug tracking-tight text-silver-200"
          >
            {active.text}
          </motion.p>
        ) : null}
      </AnimatePresence>
    </div>
  )
}

export const RitualPlayer = forwardRef<RitualPlayerHandle, {
  artifact: PresentationArtifact
  sections: RitualSection[]
  stageLens: RitualStageLens
  playerMode?: PlayerMode
  onTimeUpdate?: (ms: number) => void
}>(function RitualPlayer({ artifact, sections, stageLens, playerMode = "full", onTimeUpdate }, ref) {
  const audioRef = useRef<HTMLAudioElement>(null)
  const durationMs = artifact.captions?.at(-1)?.endMs ?? 60000
  const durationSeconds = durationMs / 1000
  const [audioUrl, setAudioUrl] = useState("")
  const [isPlaying, setIsPlaying] = useState(false)
  const [currentTime, setCurrentTime] = useState(0)

  useImperativeHandle(ref, () => ({
    seek: (ms: number) => {
      const audio = audioRef.current
      if (!audio) return
      const seconds = ms / 1000
      audio.currentTime = seconds
      setCurrentTime(seconds)
      onTimeUpdate?.(ms)
    }
  }))

  useEffect(() => {
    const url = makeSilentWavBlobUrl(durationMs)
    setAudioUrl(url)
    return () => URL.revokeObjectURL(url)
  }, [durationMs])

  useEffect(() => {
    const audio = audioRef.current
    if (!audio) return

    const syncTime = () => {
      setCurrentTime(audio.currentTime)
      onTimeUpdate?.(audio.currentTime * 1000)
    }
    const handlePlay = () => setIsPlaying(true)
    const handlePause = () => setIsPlaying(false)
    const handleEnded = () => {
      setIsPlaying(false)
      setCurrentTime(0)
      onTimeUpdate?.(0)
    }

    audio.addEventListener("timeupdate", syncTime)
    audio.addEventListener("play", handlePlay)
    audio.addEventListener("pause", handlePause)
    audio.addEventListener("ended", handleEnded)

    return () => {
      audio.removeEventListener("timeupdate", syncTime)
      audio.removeEventListener("play", handlePlay)
      audio.removeEventListener("pause", handlePause)
      audio.removeEventListener("ended", handleEnded)
    }
  }, [onTimeUpdate])

  const activeSection = sections.find(
    (s) => currentTime * 1000 >= s.startMs && currentTime * 1000 < s.endMs
  )
  const sectionMuted = activeSection?.muted ?? false

  const handleTogglePlay = async () => {
    if (!audioRef.current) return
    if (audioRef.current.paused) {
      await audioRef.current.play()
    } else {
      audioRef.current.pause()
    }
  }

  const handleScrub = (time: number) => {
    if (audioRef.current) {
      audioRef.current.currentTime = time
      setCurrentTime(time)
      onTimeUpdate?.(time * 1000)
    }
  }

  return (
    <div className="relative flex h-full flex-col items-center px-5 py-5 md:px-8 md:py-6">
      <audio ref={audioRef} src={audioUrl || undefined} preload="metadata" />

      {/* Scene / Video Stage */}
      <motion.div
        className="relative z-10 flex w-full max-w-lg flex-1 items-center justify-center"
        layout
      >
        <AnimatePresence initial={false} mode="wait">
          <VisualStage
            key={stageLens}
            artifact={artifact}
            currentMs={currentTime * 1000}
            isPlaying={isPlaying}
            stageLens={stageLens}
          />
        </AnimatePresence>
      </motion.div>

      {/* Ambient waveform — thin and unobtrusive (full only) */}
      {playerMode === "full" && (
        <motion.div
          className="relative z-10 w-full max-w-md py-2"
          layout
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
        >
          <ScrollingWaveform
            height={28}
            barCount={60}
            barWidth={2}
            barGap={1}
            barRadius={1}
            barColor="#ffffff"
            fadeEdges={true}
            fadeWidth={32}
            speed={25}
            className={[
              "transition-opacity duration-700",
              isPlaying ? "opacity-20" : "opacity-10"
            ].join(" ")}
          />
        </motion.div>
      )}

      {/* Bottom controls — morphing between full and minimal */}
      <motion.div
        className="relative z-10 flex w-full max-w-xl flex-col items-center"
        layout
      >
        <AnimatePresence initial={false} mode="wait">
          {playerMode === "full" ? (
            <motion.div
              key="full-bottom"
              className="flex w-full flex-col items-center gap-3 pb-2"
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: 6 }}
              transition={SPRING}
            >
              {/* Scrub bar with section markers */}
              <ScrubBarContainer
                duration={durationSeconds}
                value={currentTime}
                onScrub={handleScrub}
              >
                <div className="flex w-full flex-col gap-1.5">
                  <div className="relative">
                    <ScrubBarTrack className="h-1.5 bg-white/10">
                      {/* Section boundary markers */}
                      {sections.map((section) => {
                        const left = (section.startMs / 1000 / durationSeconds) * 100
                        const width =
                          ((section.endMs - section.startMs) / 1000 / durationSeconds) * 100
                        return (
                          <div
                            key={section.id}
                            className="absolute top-0 bottom-0"
                            style={{ left: `${left}%`, width: `${width}%` }}
                          >
                            <div
                              className={[
                                "h-full w-full rounded-full transition-opacity",
                                section.muted ? "bg-white/5" : "bg-white/15"
                              ].join(" ")}
                            />
                          </div>
                        )
                      })}
                      <ScrubBarProgress className="[&>div]:bg-white" />
                      <ScrubBarThumb className="size-3.5 bg-white shadow-lg" />
                    </ScrubBarTrack>
                  </div>
                  <div className="flex items-center justify-between text-[11px] font-medium text-silver-400">
                    <ScrubBarTimeLabel time={currentTime} />
                    <ScrubBarTimeLabel time={Math.max(durationSeconds - currentTime, 0)} />
                  </div>
                </div>
              </ScrubBarContainer>

              {/* Caption — glassy stack, current + next */}
              <CaptionStack
                captions={artifact.captions ?? []}
                currentMs={currentTime * 1000}
                muted={sectionMuted}
              />

              {/* Play button — compact */}
              <button
                type="button"
                onClick={handleTogglePlay}
                className={[
                  "flex size-14 items-center justify-center rounded-full border-2 transition-all duration-300",
                  sectionMuted
                    ? "border-white/15 bg-white/8 text-white/30"
                    : "border-white/25 bg-white/15 text-white shadow-2xl backdrop-blur-md hover:scale-105 hover:bg-white/25"
                ].join(" ")}
              >
                {isPlaying ? (
                  <Pause className="size-6" />
                ) : (
                  <Play className="size-6 ml-0.5" />
                )}
              </button>
            </motion.div>
          ) : (
            <motion.div
              key="minimal-bottom"
              className="flex w-full flex-col items-center gap-2 pb-10 md:pb-14"
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: 6 }}
              transition={SPRING}
            >
              {/* Floating single-line caption */}
              <MinimalCaption
                captions={artifact.captions ?? []}
                currentMs={currentTime * 1000}
                muted={sectionMuted}
              />

              {/* Compact player bar */}
              <div className="flex w-full items-center gap-3 rounded-2xl bg-white/[0.04] px-3 py-2.5 backdrop-blur-xl">
                {/* Thumbnail */}
                {artifact.coverImageUrl && (
                  <img
                    src={artifact.coverImageUrl}
                    alt={artifact.title}
                    className="h-9 w-9 shrink-0 rounded-lg object-cover"
                  />
                )}

                {/* Title + thin scrub */}
                <div className="flex min-w-0 flex-1 flex-col gap-1">
                  <span className="truncate text-xs font-medium text-silver-100">
                    {artifact.title}
                  </span>
                  <ScrubBarContainer
                    duration={durationSeconds}
                    value={currentTime}
                    onScrub={handleScrub}
                  >
                    <ScrubBarTrack className="h-1 bg-white/10">
                      <ScrubBarProgress className="[&>div]:bg-white/60" />
                    </ScrubBarTrack>
                  </ScrubBarContainer>
                </div>

                {/* Time */}
                <span className="shrink-0 text-xs tabular-nums text-silver-400">
                  {formatTimestamp(currentTime)}
                </span>

                {/* Compact play */}
                <button
                  type="button"
                  onClick={handleTogglePlay}
                  className={[
                    "flex shrink-0 items-center justify-center rounded-full transition-all duration-200",
                    sectionMuted
                      ? "h-8 w-8 bg-white/8 text-white/30"
                      : "h-8 w-8 bg-white/15 text-white hover:bg-white/25"
                  ].join(" ")}
                >
                  {isPlaying ? (
                    <Pause className="size-4" />
                  ) : (
                    <Play className="size-4 ml-0.5" />
                  )}
                </button>
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </motion.div>
    </div>
  )
})
