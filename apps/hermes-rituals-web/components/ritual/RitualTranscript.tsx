"use client"

import { useMemo } from "react"
import { motion } from "motion/react"

import { MICRO_SPRING, RITUAL_FADE } from "@/components/ritual/motion"
import { getSectionForCaption } from "@/components/ritual/RitualSectionList"
import type { PresentationArtifact, RitualSection } from "@/lib/artifact-contract"

export function RitualTranscript({
  artifact,
  sections,
  currentMs,
  onSeek
}: {
  artifact: PresentationArtifact
  sections?: RitualSection[]
  currentMs: number
  onSeek?: (ms: number) => void
}) {
  const grouped = useMemo(() => {
    const activeSections = sections ?? artifact.ritualSections ?? []
    const captions = artifact.captions ?? []
    const map = new Map<string, { section: RitualSection; cues: typeof captions }>()
    for (const cue of captions) {
      const section = getSectionForCaption(activeSections, cue)
      if (!section) continue
      const entry = map.get(section.id)
      if (entry) {
        entry.cues.push(cue)
      } else {
        map.set(section.id, { section, cues: [cue] })
      }
    }
    return Array.from(map.values())
  }, [artifact.captions, artifact.ritualSections, sections])

  return (
    <div className="flex flex-col gap-8 py-2">
      {grouped.map(({ section, cues }) => {
        const muted = section.muted ?? false
        return (
          <motion.div
            key={section.id}
            initial={false}
            animate={{ opacity: muted ? 0.3 : 1 }}
            transition={RITUAL_FADE}
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
                  <motion.button
                    key={`${cue.startMs}-${cue.endMs}`}
                    type="button"
                    onClick={() => onSeek?.(cue.startMs)}
                    className={[
                      "rounded-2xl px-4 py-3 text-left text-base leading-relaxed",
                      isCurrent
                        ? "font-semibold text-graphite-950"
                        : "text-silver-200 hover:text-silver-50"
                    ].join(" ")}
                    initial={false}
                    animate={{
                      backgroundColor: isCurrent ? "rgba(255,255,255,0.90)" : "rgba(255,255,255,0)"
                    }}
                    whileHover={isCurrent ? undefined : { backgroundColor: "rgba(255,255,255,0.10)" }}
                    whileTap={{ scale: 0.99 }}
                    transition={MICRO_SPRING}
                  >
                    {cue.text}
                  </motion.button>
                )
              })}
            </div>
          </motion.div>
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
