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
    <div className="flex flex-col gap-6">
      {grouped.map(({ section, cues }) => {
        const muted = section.muted ?? false
        return (
          <div key={section.id} className={muted ? "opacity-40" : ""}>
            <div className="mb-2 flex items-center gap-2">
              <span className={["size-2 rounded-full", kindColor(section.kind)].join(" ")} />
              <span className="text-xs font-medium uppercase tracking-wider text-graphite-500">
                {section.title}
              </span>
            </div>
            <div className="flex flex-col gap-2">
              {cues.map((cue) => {
                const isCurrent = currentMs >= cue.startMs && currentMs < cue.endMs
                return (
                  <button
                    key={`${cue.startMs}-${cue.endMs}`}
                    type="button"
                    onClick={() => onSeek?.(cue.startMs)}
                    className={[
                      "rounded-xl px-3 py-2.5 text-left text-sm transition-colors",
                      isCurrent
                        ? "bg-white/80 font-medium text-graphite-950"
                        : "bg-transparent text-graphite-600 hover:bg-white/40"
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
