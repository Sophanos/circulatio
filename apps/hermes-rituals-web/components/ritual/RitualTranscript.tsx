"use client"

import { useMemo } from "react"

import { getSectionForCaption } from "@/components/ritual/RitualSectionList"
import type { PresentationArtifact, RitualSection } from "@/lib/artifact-contract"

export function RitualTranscript({
  artifact,
  currentMs,
  onSeek
}: {
  artifact: PresentationArtifact
  currentMs: number
  onSeek?: (ms: number) => void
}) {
  const sections = artifact.ritualSections ?? []
  const captions = artifact.captions ?? []

  const grouped = useMemo(() => {
    const map = new Map<string, { section: RitualSection; cues: typeof captions }>()
    for (const cue of captions) {
      const section = getSectionForCaption(sections, cue)
      if (!section) continue
      const entry = map.get(section.id)
      if (entry) {
        entry.cues.push(cue)
      } else {
        map.set(section.id, { section, cues: [cue] })
      }
    }
    return Array.from(map.values())
  }, [sections, captions])

  return (
    <div className="flex flex-col gap-8 py-2">
      {grouped.map(({ section, cues }) => {
        const muted = section.muted ?? false
        return (
          <div
            key={section.id}
            className={[
              "transition-opacity duration-500",
              muted ? "opacity-30" : "opacity-100"
            ].join(" ")}
          >
            {/* Section header */}
            <div className="mb-3 flex items-center gap-2.5">
              <span
                className={[
                  "size-2 rounded-full",
                  kindColor(section.kind)
                ].join(" ")}
              />
              <span className="text-[11px] font-semibold uppercase tracking-[0.14em] text-silver-400">
                {section.title}
              </span>
            </div>

            {/* Cues */}
            <div className="flex flex-col gap-1">
              {cues.map((cue) => {
                const isCurrent = currentMs >= cue.startMs && currentMs < cue.endMs
                return (
                  <button
                    key={`${cue.startMs}-${cue.endMs}`}
                    type="button"
                    onClick={() => onSeek?.(cue.startMs)}
                    className={[
                      "rounded-2xl px-4 py-3 text-left text-base leading-relaxed transition-all duration-300",
                      isCurrent
                        ? "bg-white/90 font-semibold text-graphite-950"
                        : "bg-transparent text-silver-200 hover:bg-white/10 hover:text-silver-50"
                    ].join(" ")}
                  >
                    {cue.text}
                  </button>
                )
              })}
            </div>
          </div>
        )
      })}
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
