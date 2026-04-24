"use client"

import { useEffect, useImperativeHandle, useLayoutEffect, useRef, useState, forwardRef } from "react"
import { Pause, Play } from "lucide-react"
import { AnimatePresence, motion } from "motion/react"

import { BreathStage } from "@/components/ritual/BreathStage"
import { MeditationStage } from "@/components/ritual/MeditationStage"
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
import type {
  CaptionCue,
  PresentationArtifact,
  PresentationVideoSource,
  RitualSection
} from "@/lib/artifact-contract"
import { makeSilentWavBlobUrl } from "@/lib/mock-media"

export type RitualPlayerHandle = {
  seek: (ms: number) => void
}

export type RitualStageLens = "cinema" | "photo" | "breath" | "meditation" | "body"
export type PlayerMode = "full" | "minimal"

const SPRING = { type: "spring" as const, stiffness: 300, damping: 30, mass: 0.8 }

function formatTimestamp(value: number) {
  if (!Number.isFinite(value) || value < 0) return "0:00"
  const totalSeconds = Math.floor(value)
  const minutes = Math.floor(totalSeconds / 60)
  const seconds = totalSeconds % 60
  return `${minutes}:${seconds.toString().padStart(2, "0")}`
}

function resolveStageVideo(artifact: PresentationArtifact): PresentationVideoSource | undefined {
  if (artifact.stageVideo) {
    return artifact.stageVideo
  }

  if (artifact.videoUrl && !artifact.videoUrl.startsWith("mock://")) {
    return {
      provider: "direct",
      url: artifact.videoUrl,
      title: artifact.title,
      posterImageUrl: artifact.coverImageUrl,
      playbackMode: "transport_synced",
      presentation: "stage_card"
    }
  }

  return undefined
}

function extractYoutubeVideoId(url: string) {
  try {
    const parsed = new URL(url)

    if (parsed.hostname.includes("youtu.be")) {
      return parsed.pathname.split("/").filter(Boolean)[0] ?? null
    }

    if (parsed.pathname.startsWith("/embed/")) {
      return parsed.pathname.split("/")[2] ?? null
    }

    return parsed.searchParams.get("v")
  } catch {
    return null
  }
}

function buildYoutubeEmbedUrl(source: PresentationVideoSource) {
  if (source.provider !== "youtube") return null

  const videoId = extractYoutubeVideoId(source.url)
  if (!videoId) return null

  const params = new URLSearchParams({
    autoplay: "1",
    controls: "0",
    loop: "1",
    modestbranding: "1",
    mute: "1",
    playsinline: "1",
    playlist: videoId,
    rel: "0"
  })

  if (source.startAtSeconds) {
    params.set("start", String(source.startAtSeconds))
  }

  return `https://www.youtube-nocookie.com/embed/${videoId}?${params.toString()}`
}

function stageLabel(stageLens: RitualStageLens, videoSource?: PresentationVideoSource) {
  if (stageLens === "breath") return "Breath"
  if (stageLens === "meditation") return "Meditation"
  if (stageLens === "body") return "Body"
  if (stageLens === "cinema" && videoSource?.provider === "youtube") return "Cinema / YouTube"
  if (stageLens === "cinema" && videoSource?.provider === "direct") return "Cinema / Video"
  return stageLens === "cinema" ? "Cinema" : "Photo"
}

function isFullStageVideo(stageLens: RitualStageLens, videoSource?: PresentationVideoSource) {
  return stageLens === "cinema" && videoSource?.presentation === "full_background"
}

function MinimalLensPlayAffordance({
  stageLens,
  onPlay
}: {
  stageLens: Extract<RitualStageLens, "breath" | "meditation">
  onPlay: () => void | Promise<void>
}) {
  return (
    <motion.div
      className="pointer-events-none absolute inset-0 z-20 flex items-center justify-center"
      initial={{ opacity: 0, scale: 0.96 }}
      animate={{ opacity: 1, scale: 1 }}
      exit={{ opacity: 0, scale: 0.98 }}
      transition={SPRING}
    >
      <motion.button
        type="button"
        aria-label={`Play ${stageLens} ritual`}
        onClick={onPlay}
        className="pointer-events-auto flex size-16 items-center justify-center rounded-full border border-white/25 bg-black/35 text-white shadow-2xl backdrop-blur-2xl md:size-18"
        whileHover={{ scale: 1.05, backgroundColor: "rgba(255,255,255,0.18)" }}
        whileTap={{ scale: 0.97 }}
        transition={SPRING}
      >
        <Play className="ml-0.5 size-6 md:size-7" />
      </motion.button>
    </motion.div>
  )
}

function BodyStagePreview() {
  return (
    <motion.div
      key="body-preview"
      className="relative flex h-full w-full overflow-hidden rounded-3xl bg-white/[0.03]"
      layout
      initial={{ opacity: 0, scale: 0.985 }}
      animate={{ opacity: 1, scale: 1 }}
      exit={{ opacity: 0, scale: 1.01 }}
      transition={SPRING}
    >
      <div className="absolute inset-0 bg-[radial-gradient(circle_at_center,rgba(255,255,255,0.08),transparent_48%),linear-gradient(180deg,rgba(16,19,23,0.06)_0%,rgba(16,19,23,0.62)_100%)]" />
      <div className="relative z-10 flex h-full w-full flex-col justify-between p-4 md:p-5">
        <div className="flex flex-col gap-1">
          <span className="text-[10px] font-medium uppercase tracking-[0.18em] text-silver-400">
            Body
          </span>
          <span className="text-sm font-medium text-silver-100">Somatic check-in</span>
          <span className="text-[11px] text-silver-500">Picker planned</span>
        </div>
        <div className="flex flex-1 items-center justify-center">
          <div className="relative flex size-56 items-center justify-center rounded-full border border-white/10 bg-black/10 md:size-64">
            <div className="absolute size-36 rounded-full border border-white/15 md:size-40" />
            <div className="absolute size-16 rounded-full bg-white/[0.04]" />
            <span className="text-[10px] font-medium uppercase tracking-[0.2em] text-silver-500">
              Body map
            </span>
          </div>
        </div>
      </div>
    </motion.div>
  )
}

function VisualStage({
  artifact,
  currentMs,
  isPlaying,
  stageLens,
  immersive
}: {
  artifact: PresentationArtifact
  currentMs: number
  isPlaying: boolean
  stageLens: RitualStageLens
  immersive?: boolean
}) {
  const scenes = artifact.scenes ?? []
  const activeScene = scenes.find(
    (scene) => currentMs >= (scene.startMs ?? 0) && currentMs < (scene.endMs ?? Infinity)
  )
  const activeId = activeScene?.id
  const videoSource = resolveStageVideo(artifact)
  const youtubeEmbedUrl = videoSource ? buildYoutubeEmbedUrl(videoSource) : null
  const directVideoSource = videoSource?.provider === "direct" ? videoSource : undefined
  const directPlaybackMode = directVideoSource?.playbackMode
  const directVideoRef = useRef<HTMLVideoElement>(null)
  const durationMs = artifact.captions?.at(-1)?.endMs ?? 60000

  useEffect(() => {
    const video = directVideoRef.current
    if (!video || directPlaybackMode !== "transport_synced") return

    if (isPlaying) {
      void video.play().catch(() => {})
      return
    }

    video.pause()
  }, [directPlaybackMode, isPlaying])

  useEffect(() => {
    const video = directVideoRef.current
    if (!video || directPlaybackMode !== "transport_synced") return

    const nextTime = currentMs / 1000
    if (Math.abs(video.currentTime - nextTime) > 0.8) {
      video.currentTime = nextTime
    }
  }, [currentMs, directPlaybackMode])

  if (stageLens === "breath") {
    return (
      <BreathStage
        cycle={artifact.breathCycle}
        currentMs={currentMs}
        isPlaying={isPlaying}
        immersive={immersive}
        totalDurationMs={durationMs}
      />
    )
  }

  if (stageLens === "meditation") {
    return (
      <MeditationStage
        cycle={artifact.breathCycle}
        currentMs={currentMs}
        durationMs={durationMs}
      />
    )
  }

  if (stageLens === "body") {
    return <BodyStagePreview />
  }

  if (stageLens === "cinema" && (youtubeEmbedUrl || directVideoSource?.url)) {
    const fullStageVideo = isFullStageVideo(stageLens, videoSource)

    return (
      <motion.div
        key="cinema-video"
        className={[
          "relative h-full w-full overflow-hidden bg-black/60",
          fullStageVideo ? "rounded-none border-0 shadow-none" : "rounded-3xl shadow-2xl"
        ].join(" ")}
        layout
        initial={{ opacity: 0, scale: 0.985 }}
        animate={{ opacity: 1, scale: 1 }}
        exit={{ opacity: 0, scale: 1.01 }}
        transition={SPRING}
      >
        {youtubeEmbedUrl ? (
          <div className="pointer-events-none absolute inset-0 overflow-hidden">
            <iframe
              src={youtubeEmbedUrl}
              title={videoSource?.title ?? artifact.title}
              className={[
                fullStageVideo
                  ? "absolute left-1/2 top-1/2 h-[56.25vw] min-h-full w-full min-w-[177.78vh] -translate-x-1/2 -translate-y-1/2"
                  : "h-full w-full scale-[1.03]"
              ].join(" ")}
              allow="autoplay; encrypted-media; fullscreen; picture-in-picture"
              referrerPolicy="strict-origin-when-cross-origin"
            />
          </div>
        ) : (
          <video
            ref={directVideoRef}
            src={directVideoSource?.url}
            poster={directVideoSource?.posterImageUrl ?? artifact.coverImageUrl}
            className="h-full w-full object-cover"
            playsInline
            muted
            loop={directPlaybackMode !== "transport_synced"}
            autoPlay={directPlaybackMode !== "transport_synced"}
          />
        )}
        <div
          className={[
            "absolute inset-0",
            fullStageVideo
              ? "bg-[radial-gradient(circle_at_top_left,rgba(255,255,255,0.10),transparent_34%),linear-gradient(180deg,rgba(16,19,23,0.44)_0%,rgba(16,19,23,0.08)_28%,rgba(16,19,23,0.34)_62%,rgba(16,19,23,0.86)_100%)]"
              : "bg-[radial-gradient(circle_at_top,rgba(255,255,255,0.12),transparent_32%),linear-gradient(180deg,rgba(16,19,23,0.06)_0%,rgba(16,19,23,0.34)_48%,rgba(16,19,23,0.82)_100%)]"
          ].join(" ")}
        />
        {!fullStageVideo && (
          <>
            <div className="absolute left-4 top-4 rounded-full bg-black/25 px-3 py-1.5 text-[10px] font-medium uppercase tracking-[0.18em] text-silver-300 backdrop-blur-xl">
              {stageLabel(stageLens, videoSource)}
            </div>
            <div className="absolute right-4 top-4 rounded-full bg-black/25 px-3 py-1.5 text-[10px] font-medium uppercase tracking-[0.18em] text-silver-400 backdrop-blur-xl">
              {videoSource?.playbackMode === "transport_synced" ? "Synced" : "Ambient"}
            </div>
            {(videoSource?.title || activeScene?.title) && (
              <div className="absolute bottom-4 left-4 rounded-2xl bg-black/35 px-4 py-2.5 text-sm text-silver-100 backdrop-blur-xl">
                <p className="text-[10px] font-medium uppercase tracking-[0.18em] text-silver-400">
                  Ritual stage
                </p>
                <p className="mt-1 font-medium text-silver-100">
                  {videoSource?.title ?? activeScene?.title}
                </p>
              </div>
            )}
          </>
        )}
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

function CinemaCaptionOverlay({
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
    <AnimatePresence mode="wait">
      {active ? (
        <motion.p
          key={`${active.startMs}-${active.endMs}`}
          initial={{ opacity: 0, y: 6, filter: "blur(2px)" }}
          animate={{
            opacity: muted ? 0.4 : 0.94,
            y: 0,
            filter: "blur(0px)"
          }}
          exit={{ opacity: 0, y: -4, filter: "blur(2px)" }}
          transition={SPRING}
          className="max-w-[min(76vw,640px)] text-balance text-center text-base font-medium leading-snug tracking-tight text-white md:text-lg [text-shadow:0_2px_18px_rgba(0,0,0,0.95)]"
        >
          {active.text}
        </motion.p>
      ) : null}
    </AnimatePresence>
  )
}

export const RitualPlayer = forwardRef<RitualPlayerHandle, {
  artifact: PresentationArtifact
  sections: RitualSection[]
  stageLens: RitualStageLens
  playerMode?: PlayerMode
  immersive?: boolean
  chromeVisible?: boolean
  onTimeUpdate?: (ms: number) => void
  onPlayingChange?: (playing: boolean) => void
}>(function RitualPlayer({
  artifact,
  sections,
  stageLens,
  playerMode = "full",
  immersive,
  chromeVisible = true,
  onTimeUpdate,
  onPlayingChange
}, ref) {
  const audioRef = useRef<HTMLAudioElement>(null)
  const animationFrameRef = useRef<number | null>(null)
  const playbackAnchorRef = useRef<{ audioSeconds: number; startedAtMs: number } | null>(null)
  const durationMs = artifact.captions?.at(-1)?.endMs ?? 60000
  const durationSeconds = durationMs / 1000
  const [audioUrl, setAudioUrl] = useState("")
  const [isPlaying, setIsPlaying] = useState(false)
  const [currentTime, setCurrentTime] = useState(0)
  const [breathClockOffsetMs, setBreathClockOffsetMs] = useState(0)
  const currentTimeMs = currentTime * 1000
  const currentTimeMsRef = useRef(0)
  currentTimeMsRef.current = currentTimeMs
  const stageVideoSource = resolveStageVideo(artifact)
  const fullStageVideo = isFullStageVideo(stageLens, stageVideoSource)
  const fullStageChromeVisible = !fullStageVideo || chromeVisible

  useImperativeHandle(ref, () => ({
    seek: (ms: number) => {
      const audio = audioRef.current
      if (!audio) return
      const seconds = ms / 1000
      audio.currentTime = seconds
      if (!audio.paused && !audio.ended) {
        playbackAnchorRef.current = { audioSeconds: seconds, startedAtMs: performance.now() }
      }
      if (stageLens === "breath") {
        setBreathClockOffsetMs(ms)
      }
      setCurrentTime(seconds)
      onTimeUpdate?.(ms)
    }
  }))

  useEffect(() => {
    const url = makeSilentWavBlobUrl(durationMs)
    setAudioUrl(url)
    return () => URL.revokeObjectURL(url)
  }, [durationMs])

  useLayoutEffect(() => {
    if (stageLens === "breath") {
      setBreathClockOffsetMs(currentTimeMsRef.current)
    }
  }, [stageLens])

  useEffect(() => {
    const audio = audioRef.current
    if (!audio) return

    const stopFrameClock = () => {
      if (animationFrameRef.current === null) return
      cancelAnimationFrame(animationFrameRef.current)
      animationFrameRef.current = null
    }

    const readClockSeconds = () => {
      const audioSeconds = Number.isFinite(audio.currentTime) ? audio.currentTime : 0
      const anchor = playbackAnchorRef.current
      if (!anchor || audio.paused || audio.ended) {
        return Math.min(Math.max(audioSeconds, 0), durationSeconds)
      }
      const elapsedSeconds = (performance.now() - anchor.startedAtMs) / 1000
      const fallbackSeconds = anchor.audioSeconds + elapsedSeconds
      return Math.min(Math.max(audioSeconds, fallbackSeconds, 0), durationSeconds)
    }

    const syncTime = () => {
      const nextSeconds = readClockSeconds()
      setCurrentTime(nextSeconds)
      onTimeUpdate?.(nextSeconds * 1000)
      return nextSeconds
    }

    const finishPlayback = () => {
      playbackAnchorRef.current = null
      stopFrameClock()
      setIsPlaying(false)
      onPlayingChange?.(false)
      setCurrentTime(0)
      onTimeUpdate?.(0)
    }

    const tick = () => {
      const nextSeconds = syncTime()
      if (nextSeconds >= durationSeconds) {
        audio.pause()
        audio.currentTime = 0
        finishPlayback()
        return
      }
      if (!audio.paused && !audio.ended) {
        animationFrameRef.current = requestAnimationFrame(tick)
        return
      }
      animationFrameRef.current = null
    }

    const startFrameClock = () => {
      playbackAnchorRef.current = {
        audioSeconds: readClockSeconds(),
        startedAtMs: performance.now()
      }
      stopFrameClock()
      animationFrameRef.current = requestAnimationFrame(tick)
    }

    const handlePlay = () => {
      startFrameClock()
      syncTime()
      setIsPlaying(true)
      onPlayingChange?.(true)
    }
    const handlePause = () => {
      syncTime()
      playbackAnchorRef.current = null
      stopFrameClock()
      setIsPlaying(false)
      onPlayingChange?.(false)
    }
    const handleEnded = () => {
      finishPlayback()
    }

    audio.addEventListener("timeupdate", syncTime)
    audio.addEventListener("play", handlePlay)
    audio.addEventListener("pause", handlePause)
    audio.addEventListener("ended", handleEnded)

    return () => {
      stopFrameClock()
      audio.removeEventListener("timeupdate", syncTime)
      audio.removeEventListener("play", handlePlay)
      audio.removeEventListener("pause", handlePause)
      audio.removeEventListener("ended", handleEnded)
    }
  }, [durationSeconds, onPlayingChange, onTimeUpdate])

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
      if (!audioRef.current.paused && !audioRef.current.ended) {
        playbackAnchorRef.current = { audioSeconds: time, startedAtMs: performance.now() }
      }
      if (stageLens === "breath") {
        setBreathClockOffsetMs(time * 1000)
      }
      setCurrentTime(time)
      onTimeUpdate?.(time * 1000)
    }
  }

  const visualStageCurrentMs =
    stageLens === "breath" ? Math.max(currentTimeMs - breathClockOffsetMs, 0) : currentTimeMs
  const showMinimalLensPlayAffordance =
    playerMode === "minimal" &&
    (stageLens === "breath" || stageLens === "meditation") &&
    !isPlaying

  return (
    <div
      data-cinema-fullstage={fullStageVideo ? "true" : undefined}
      className={[
        "relative flex h-full flex-col items-center",
        fullStageVideo ? "overflow-hidden px-0 py-0" : "px-5 py-5 md:px-8 md:py-6"
      ].join(" ")}
    >
      <audio ref={audioRef} src={audioUrl || undefined} preload="metadata" />

      {/* Scene / Video Stage */}
      <motion.div
        className={[
          "flex w-full flex-1 items-center justify-center",
          fullStageVideo
            ? "absolute inset-0 z-0 min-h-0 max-w-none self-stretch"
            : "relative z-10 max-w-lg"
        ].join(" ")}
        layout
      >
        <AnimatePresence initial={false} mode="wait">
          <VisualStage
            key={stageLens}
            artifact={artifact}
            currentMs={visualStageCurrentMs}
            isPlaying={isPlaying}
            stageLens={stageLens}
            immersive={immersive}
          />
        </AnimatePresence>
      </motion.div>

      <AnimatePresence>
        {showMinimalLensPlayAffordance && (
          <MinimalLensPlayAffordance stageLens={stageLens} onPlay={handleTogglePlay} />
        )}
      </AnimatePresence>

      {fullStageVideo && (
        <motion.div
          data-cinema-caption="true"
          className="pointer-events-none absolute inset-x-5 z-10 flex justify-center"
          initial={false}
          animate={{
            bottom: fullStageChromeVisible ? 224 : 44,
            opacity: sectionMuted ? 0.45 : 1,
            y: fullStageChromeVisible ? -8 : 0
          }}
          transition={SPRING}
        >
          <CinemaCaptionOverlay
            captions={artifact.captions ?? []}
            currentMs={currentTime * 1000}
            muted={sectionMuted}
          />
        </motion.div>
      )}

      {/* Ambient waveform — thin and unobtrusive (full only) */}
      {playerMode === "full" && !fullStageVideo && (
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
        data-cinema-controls={fullStageVideo ? "true" : undefined}
        data-chrome-visible={fullStageChromeVisible ? "true" : "false"}
        className={[
          "flex w-full flex-col items-center",
          fullStageVideo
            ? "absolute inset-x-6 bottom-20 z-20 mx-auto max-w-[40rem] px-0 sm:max-w-[42rem] md:bottom-24 lg:max-w-[44rem] xl:max-w-[48rem]"
            : "relative z-10 max-w-xl"
        ].join(" ")}
        layout
        animate={{
          opacity: fullStageChromeVisible ? 1 : 0,
          y: fullStageChromeVisible ? 0 : 18
        }}
        transition={SPRING}
        style={{ pointerEvents: fullStageChromeVisible ? "auto" : "none" }}
      >
        <AnimatePresence initial={false} mode="wait">
          {playerMode === "full" ? (
            <motion.div
              key="full-bottom"
              className={[
                "flex w-full flex-col items-center",
                fullStageVideo
                  ? "gap-3 rounded-[1.35rem] border border-white/10 bg-black/45 px-4 py-3 backdrop-blur-2xl md:px-5 md:py-3.5"
                  : "gap-3 pb-2"
              ].join(" ")}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: 6 }}
              transition={SPRING}
            >
              {fullStageVideo ? (
                <>
                  <div className="flex w-full items-center justify-center">
                    <button
                      type="button"
                      aria-label={isPlaying ? "Pause ritual" : "Play ritual"}
                      onClick={handleTogglePlay}
                      className={[
                        "flex size-11 items-center justify-center rounded-full border transition-all duration-300 md:size-12",
                        sectionMuted
                          ? "border-white/15 bg-white/8 text-white/30"
                          : "border-white/25 bg-white/15 text-white shadow-2xl backdrop-blur-md hover:scale-105 hover:bg-white/25"
                      ].join(" ")}
                    >
                      {isPlaying ? (
                        <Pause className="size-5 md:size-5.5" />
                      ) : (
                        <Play className="ml-0.5 size-5 md:size-5.5" />
                      )}
                    </button>
                  </div>

                  <ScrubBarContainer
                    duration={durationSeconds}
                    value={currentTime}
                    onScrub={handleScrub}
                  >
                    <div className="flex w-full items-center gap-3 md:gap-5">
                      <ScrubBarTimeLabel
                        time={currentTime}
                        className="w-10 shrink-0 text-left text-sm font-semibold tabular-nums text-silver-100 md:w-12 md:text-base"
                      />
                      <div className="relative min-w-0 flex-1">
                        <ScrubBarTrack className="h-1.5 bg-white/20 md:h-2">
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
                          <ScrubBarThumb className="size-4 bg-white shadow-lg md:size-5" />
                        </ScrubBarTrack>
                      </div>
                      <ScrubBarTimeLabel
                        time={Math.max(durationSeconds - currentTime, 0)}
                        className="w-10 shrink-0 text-right text-sm font-semibold tabular-nums text-silver-100 md:w-12 md:text-base"
                      />
                    </div>
                  </ScrubBarContainer>
                </>
              ) : (
                <>
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
                    aria-label={isPlaying ? "Pause ritual" : "Play ritual"}
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
                      <Play className="ml-0.5 size-6" />
                    )}
                  </button>
                </>
              )}
            </motion.div>
          ) : (
            <motion.div
              key="minimal-bottom"
              className={[
                "flex w-full flex-col items-center",
                immersive ? "gap-0 pb-0" : "gap-2 pb-10 md:pb-14"
              ].join(" ")}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: immersive ? 0 : 1, y: 0 }}
              exit={{ opacity: 0, y: 6 }}
              transition={SPRING}
            >
              {/* Floating single-line caption — hidden in immersive */}
              {!immersive && (
                <MinimalCaption
                  captions={artifact.captions ?? []}
                  currentMs={currentTime * 1000}
                  muted={sectionMuted}
                />
              )}

              {/* Compact player bar — hidden in immersive */}
              {!immersive && (
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
                    aria-label={isPlaying ? "Pause ritual" : "Play ritual"}
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
              )}
            </motion.div>
          )}
        </AnimatePresence>
      </motion.div>
    </div>
  )
})
