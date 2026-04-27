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
    <div className="flex flex-col gap-1 py-1">
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
        "group relative flex items-center gap-3 rounded-2xl px-3 py-3 transition-all duration-300",
        isActive
          ? "bg-white/15"
          : "bg-transparent hover:bg-white/10",
        muted ? "opacity-30" : "opacity-100"
      ].join(" ")}
    >
      {/* Progress indicator */}
      <div className="flex w-5 shrink-0 justify-center">
        {isActive && (
          <span className={[
            "block size-1.5 rounded-full",
            muted ? "bg-silver-500" : "bg-silver-100"
          ].join(" ")} />
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
        <span className="text-sm font-medium text-silver-100">
          {section.title}
        </span>
        <span className="text-xs text-silver-500">
          {formatTime(section.startMs)} — {formatTime(section.endMs)} · {durationSec}s
        </span>
        {section.transcript && (
          <span className="mt-1 line-clamp-2 text-xs leading-snug text-silver-400">
            {section.transcript}
          </span>
        )}
      </button>

      {/* Mute toggle */}
      <button
        type="button"
        onClick={() => onToggleMute?.(section.id, !muted)}
        className={[
          "flex size-8 items-center justify-center rounded-full transition-colors",
          muted
            ? "bg-white/5 text-silver-500 hover:bg-white/10 hover:text-silver-300"
            : "bg-white/10 text-silver-200 hover:bg-white/20 hover:text-white"
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
