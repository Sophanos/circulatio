"use client"

import { useEffect, useImperativeHandle, useRef, useState, forwardRef } from "react"
import { Pause, Play } from "lucide-react"

import { CaptionOverlay } from "@/components/ritual/CaptionOverlay"
import { ScrollingWaveform } from "@/components/ui/waveform"
import {
  ScrubBarContainer,
  ScrubBarProgress,
  ScrubBarThumb,
  ScrubBarTimeLabel,
  ScrubBarTrack
} from "@/components/ui/scrub-bar"
import type { PresentationArtifact, RitualSection } from "@/lib/artifact-contract"
import { makeSilentWavBlobUrl } from "@/lib/mock-media"

export type RitualPlayerHandle = {
  seek: (ms: number) => void
}

function SceneStack({
  artifact,
  currentMs,
  isPlaying
}: {
  artifact: PresentationArtifact
  currentMs: number
  isPlaying: boolean
}) {
  const hasRealVideo = artifact.videoUrl && !artifact.videoUrl.startsWith("mock://")

  if (hasRealVideo) {
    return (
      <div className="relative h-full w-full overflow-hidden rounded-3xl shadow-2xl">
        <video
          src={artifact.videoUrl}
          className="h-full w-full object-cover"
          playsInline
          muted
          loop
          autoPlay
        />
        <div className="absolute inset-0 bg-gradient-to-t from-black/50 via-transparent to-transparent" />
      </div>
    )
  }

  const scenes = artifact.scenes ?? []
  const activeScene = scenes.find(
    (s) => currentMs >= (s.startMs ?? 0) && currentMs < (s.endMs ?? Infinity)
  )
  const activeId = activeScene?.id

  if (!scenes.length) {
    return (
      <div className="relative h-full w-full overflow-hidden rounded-3xl shadow-2xl">
        {artifact.coverImageUrl && (
          <img
            src={artifact.coverImageUrl}
            alt={artifact.title}
            className="h-full w-full object-cover"
          />
        )}
        <div className="absolute inset-0 bg-gradient-to-t from-black/50 via-transparent to-transparent" />
      </div>
    )
  }

  return (
    <div className="relative h-full w-full overflow-hidden rounded-3xl shadow-2xl">
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
      {isPlaying && activeScene && (
        <div className="absolute bottom-4 left-4 rounded-lg bg-black/30 px-3 py-1.5 text-xs font-medium text-white/90 backdrop-blur-md">
          {activeScene.title}
        </div>
      )}
    </div>
  )
}

export const RitualPlayer = forwardRef<RitualPlayerHandle, {
  artifact: PresentationArtifact
  sections: RitualSection[]
  onTimeUpdate?: (ms: number) => void
}>(function RitualPlayer({ artifact, sections, onTimeUpdate }, ref) {
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

  const activeCaption =
    artifact.captions?.find(
      (caption) =>
        currentTime * 1000 >= caption.startMs && currentTime * 1000 < caption.endMs
    ) ?? artifact.captions?.[0]

  const activeSection = sections.find(
    (s) => currentTime * 1000 >= s.startMs && currentTime * 1000 < s.endMs
  )
  const sectionMuted = activeSection?.muted ?? false

  return (
    <div className="relative flex h-full flex-col items-center px-5 py-5 md:px-8 md:py-6">
      <audio ref={audioRef} src={audioUrl} preload="metadata" />

      {/* Scene / Video Stage */}
      <div className="relative z-10 w-full max-w-lg flex-1">
        <SceneStack artifact={artifact} currentMs={currentTime * 1000} isPlaying={isPlaying} />
      </div>

      {/* Waveform */}
      <div className="relative z-10 w-full max-w-2xl py-5 md:py-6">
        <ScrollingWaveform
          height={100}
          barCount={80}
          barWidth={3}
          barGap={2}
          barRadius={2}
          barColor="#ffffff"
          fadeEdges={true}
          fadeWidth={48}
          speed={35}
          className={[
            "transition-opacity duration-700",
            isPlaying ? "opacity-90" : "opacity-35"
          ].join(" ")}
        />
      </div>

      {/* Transport */}
      <div className="relative z-10 flex w-full max-w-xl flex-col items-center gap-4">
        {/* Scrub bar with section markers */}
        <ScrubBarContainer
          duration={durationSeconds}
          value={currentTime}
          onScrub={(time) => {
            if (audioRef.current) {
              audioRef.current.currentTime = time
              setCurrentTime(time)
              onTimeUpdate?.(time * 1000)
            }
          }}
        >
          <div className="flex w-full flex-col gap-2">
            <div className="relative">
              <ScrubBarTrack className="h-2.5 bg-white/10">
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
                <ScrubBarThumb className="size-5 bg-white shadow-lg" />
              </ScrubBarTrack>
            </div>
            <div className="flex items-center justify-between text-xs font-medium text-silver-400">
              <ScrubBarTimeLabel time={currentTime} />
              <ScrubBarTimeLabel time={Math.max(durationSeconds - currentTime, 0)} />
            </div>
          </div>
        </ScrubBarContainer>

        {/* Play button */}
        <button
          type="button"
          onClick={async () => {
            if (!audioRef.current) return
            if (audioRef.current.paused) {
              await audioRef.current.play()
            } else {
              audioRef.current.pause()
            }
          }}
          className={[
            "flex size-20 items-center justify-center rounded-full border-2 transition-all duration-300 md:size-24",
            sectionMuted
              ? "border-white/15 bg-white/8 text-white/30"
              : "border-white/25 bg-white/15 text-white shadow-2xl backdrop-blur-md hover:scale-105 hover:bg-white/25"
          ].join(" ")}
        >
          {isPlaying ? (
            <Pause className="size-8 md:size-10" />
          ) : (
            <Play className="size-8 ml-1 md:size-10" />
          )}
        </button>
      </div>

      {/* Caption overlay */}
      <CaptionOverlay
        text={activeCaption?.text ?? ""}
        muted={sectionMuted}
      />
    </div>
  )
})
