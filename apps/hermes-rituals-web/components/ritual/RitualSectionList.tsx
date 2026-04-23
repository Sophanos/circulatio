"use client"

import { useMemo } from "react"
import { Volume2, VolumeX } from "lucide-react"

import type { RitualSection, CaptionCue } from "@/lib/artifact-contract"

export type SectionMuteHandler = (sectionId: string, muted: boolean) => void

export function RitualSectionList({
  sections,
  currentMs,
  onToggleMute,
  onSeek
}: {
  sections: RitualSection[]
  currentMs: number
  onToggleMute?: SectionMuteHandler
  onSeek?: (ms: number) => void
}) {
  const activeSectionId = useMemo(() => {
    return sections.find(
      (s) => currentMs >= s.startMs && currentMs < s.endMs
    )?.id
  }, [sections, currentMs])

  return (
    <div className="flex flex-col gap-1">
      {sections.map((section) => (
        <SectionRow
          key={section.id}
          section={section}
          isActive={section.id === activeSectionId}
          onToggleMute={onToggleMute}
          onSeek={onSeek}
        />
      ))}
    </div>
  )
}

function SectionRow({
  section,
  isActive,
  onToggleMute,
  onSeek
}: {
  section: RitualSection
  isActive: boolean
  onToggleMute?: SectionMuteHandler
  onSeek?: (ms: number) => void
}) {
  const durationSec = Math.round((section.endMs - section.startMs) / 1000)
  const muted = section.muted ?? false

  return (
    <div
      className={[
        "group relative flex items-center gap-3 rounded-2xl px-3 py-3 transition-colors",
        isActive
          ? "bg-white/60"
          : "bg-transparent hover:bg-white/30",
        muted ? "opacity-40" : "opacity-100"
      ].join(" ")}
    >
      {/* Progress indicator */}
      <div className="flex w-5 shrink-0 justify-center">
        {isActive && !muted && (
          <span className="block size-1.5 rounded-full bg-graphite-950" />
        )}
        {isActive && muted && (
          <span className="block size-1.5 rounded-full bg-graphite-400" />
        )}
      </div>

      {/* Kind dot */}
      <div
        className={[
          "size-2.5 shrink-0 rounded-full",
          kindColor(section.kind)
        ].join(" ")}
      />

      {/* Content */}
      <button
        type="button"
        onClick={() => onSeek?.(section.startMs)}
        className="flex min-w-0 flex-1 flex-col items-start text-left"
      >
        <span className="text-sm font-medium text-graphite-950">
          {section.title}
        </span>
        <span className="text-xs text-graphite-500">
          {formatTime(section.startMs)} — {formatTime(section.endMs)} · {durationSec}s
        </span>
      </button>

      {/* Mute toggle */}
      <button
        type="button"
        onClick={() => onToggleMute?.(section.id, !muted)}
        className={[
          "flex size-8 items-center justify-center rounded-full transition-colors",
          muted
            ? "bg-graphite-950/5 text-graphite-400 hover:bg-graphite-950/10"
            : "bg-graphite-950/5 text-graphite-700 hover:bg-graphite-950/10"
        ].join(" ")}
        aria-label={muted ? `Unmute ${section.title}` : `Mute ${section.title}`}
      >
        {muted ? <VolumeX className="size-3.5" /> : <Volume2 className="size-3.5" />}
      </button>
    </div>
  )
}

function kindColor(kind: RitualSection["kind"]) {
  switch (kind) {
    case "arrival":
      return "bg-emerald-400"
    case "breath":
      return "bg-sky-400"
    case "image":
      return "bg-amber-400"
    case "reflection":
      return "bg-rose-400"
    case "closing":
      return "bg-slate-400"
    default:
      return "bg-graphite-300"
  }
}

function formatTime(ms: number) {
  const totalSeconds = Math.floor(ms / 1000)
  const minutes = Math.floor(totalSeconds / 60)
  const seconds = totalSeconds % 60
  return `${minutes}:${seconds.toString().padStart(2, "0")}`
}

export function getSectionForCaption(
  sections: RitualSection[],
  caption: CaptionCue
) {
  return sections.find(
    (s) => caption.startMs >= s.startMs && caption.startMs < s.endMs
  )
}
