"use client"

import { motion } from "motion/react"

import {
  ScrubBarContainer,
  ScrubBarTrack
} from "@/components/ui/scrub-bar"
import type { RitualSection } from "@/lib/artifact-contract"
import { MICRO_SPRING, PANEL_SPRING, RITUAL_FADE } from "@/components/ritual/motion"

export type RitualTimelineCompletionStatus = "idle" | "completed" | "submitting" | "saved" | "error"

function clampMs(value: number, durationMs: number) {
  if (!Number.isFinite(value)) return 0
  return Math.min(Math.max(value, 0), Math.max(durationMs, 0))
}

function formatTimestampMs(value: number) {
  if (!Number.isFinite(value) || value < 0) return "0:00"
  const totalSeconds = Math.floor(value / 1000)
  const minutes = Math.floor(totalSeconds / 60)
  const seconds = totalSeconds % 60
  return `${minutes}:${seconds.toString().padStart(2, "0")}`
}

function completionLabel(status: RitualTimelineCompletionStatus) {
  switch (status) {
    case "completed":
      return "Complete"
    case "submitting":
      return "Saving"
    case "saved":
      return "Saved"
    case "error":
      return "Needs attention"
    case "idle":
      return null
  }
}

function TimelineSectionMarkers({
  sections,
  durationMs,
  activeSectionId
}: {
  sections: RitualSection[]
  durationMs: number
  activeSectionId?: string
}) {
  if (durationMs <= 0 || sections.length === 0) return null

  return (
    <div className="pointer-events-none absolute inset-0 overflow-hidden rounded-full">
      {sections.map((section) => {
        const startMs = clampMs(section.startMs, durationMs)
        const endMs = clampMs(Math.max(section.endMs, startMs), durationMs)
        const width = ((endMs - startMs) / durationMs) * 100
        if (width <= 0) return null

        const active = section.id === activeSectionId
        const muted = section.muted ?? false

        return (
          <motion.div
            key={section.id}
            className="absolute bottom-0 top-0 rounded-full"
            style={{ left: `${(startMs / durationMs) * 100}%`, width: `${width}%` }}
            initial={false}
            animate={{
              opacity: muted ? 0.24 : active ? 0.72 : 0.38,
              backgroundColor: active ? "rgba(255,255,255,0.42)" : "rgba(255,255,255,0.18)"
            }}
            transition={MICRO_SPRING}
          />
        )
      })}
    </div>
  )
}

export function RitualTimelineProgress({
  currentMs,
  durationMs,
  sections,
  activeSection,
  completionStatus,
  onSeek
}: {
  currentMs: number
  durationMs: number
  sections: RitualSection[]
  activeSection?: RitualSection | null
  completionStatus: RitualTimelineCompletionStatus
  onSeek?: (ms: number) => void
}) {
  const finished = completionStatus === "completed" || completionStatus === "saved"
  const displayMs = clampMs(finished ? durationMs : currentMs, durationMs)
  const remainingMs = Math.max(durationMs - displayMs, 0)
  const statusLabel = completionLabel(completionStatus)
  const sectionTitle = finished
    ? statusLabel ?? "Complete"
    : activeSection?.title ?? sections[0]?.title ?? "Artifact"
  const durationSeconds = Math.max(durationMs / 1000, 0)
  const progressRatio = durationMs > 0 ? displayMs / durationMs : 0
  const progressPercent = Math.min(Math.max(progressRatio, 0), 1) * 100

  return (
    <motion.div
      className="w-full rounded-[1.35rem] border border-white/10 bg-black/35 px-3 py-2.5 backdrop-blur-2xl md:px-4"
      layout
      initial={false}
      transition={PANEL_SPRING}
    >
      <div className="mb-2 flex items-center justify-between gap-3">
        <div className="min-w-0">
          <p className="text-[10px] font-medium uppercase tracking-[0.16em] text-silver-500">
            Timeline
          </p>
          <p className="truncate text-sm font-medium text-silver-100">{sectionTitle}</p>
        </div>
        <div className="flex shrink-0 items-center gap-2 text-[11px] font-medium tabular-nums text-silver-400">
          {statusLabel ? (
            <motion.span
              className="rounded-full bg-white/10 px-2 py-1 text-[10px] uppercase tracking-[0.14em] text-silver-100"
              initial={{ opacity: 0, scale: 0.96 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.98 }}
              transition={MICRO_SPRING}
            >
              {statusLabel}
            </motion.span>
          ) : null}
          <span>{formatTimestampMs(displayMs)}</span>
          <span className="text-silver-600">/</span>
          <span>{formatTimestampMs(remainingMs)} left</span>
        </div>
      </div>

      <ScrubBarContainer
        duration={durationSeconds}
        value={displayMs / 1000}
        onScrub={onSeek ? (seconds) => onSeek(seconds * 1000) : undefined}
      >
        <ScrubBarTrack className="h-1.5 bg-white/15">
          <TimelineSectionMarkers
            sections={sections}
            durationMs={durationMs}
            activeSectionId={activeSection?.id}
          />
          <motion.div
            className="pointer-events-none absolute inset-y-0 left-0 w-full origin-left rounded-full bg-white/85"
            initial={false}
            animate={{ scaleX: progressRatio }}
            transition={MICRO_SPRING}
          />
          <motion.div
            className="pointer-events-none absolute top-1/2 size-3 -translate-x-1/2 -translate-y-1/2 rounded-full bg-white shadow-lg"
            initial={false}
            animate={{ left: `${progressPercent}%` }}
            transition={MICRO_SPRING}
          />
        </ScrubBarTrack>
      </ScrubBarContainer>

      <motion.div
        className="mt-2 flex items-center justify-between text-[10px] font-medium uppercase tracking-[0.14em] text-silver-600"
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={RITUAL_FADE}
      >
        <span>Elapsed</span>
        <span>Remaining</span>
      </motion.div>
    </motion.div>
  )
}
