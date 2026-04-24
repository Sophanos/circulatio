"use client"

import { motion } from "motion/react"

import type { CaptionCue } from "@/lib/artifact-contract"

const SPRING = { type: "spring" as const, stiffness: 300, damping: 30, mass: 0.8 }

export function CaptionStack({
  captions,
  currentMs,
  muted
}: {
  captions: CaptionCue[]
  currentMs: number
  muted?: boolean
}) {
  const currentIndex = captions.findIndex(
    (c) => currentMs >= c.startMs && currentMs < c.endMs
  )

  const start = Math.max(0, currentIndex)
  const visible = captions.slice(start, start + 2)

  return (
    <div className="flex w-full flex-col items-center">
      <div className="flex flex-col items-center gap-1 px-5 py-2">
        {visible.map((cue, offset) => {
          const isCurrent = offset === 0
          const baseOpacity = isCurrent ? 1 : 0.35
          const blur = isCurrent ? 0 : 1
          const scale = isCurrent ? 1 : 0.98

          return (
            <motion.p
              key={`${cue.startMs}-${cue.endMs}`}
              initial={false}
              animate={{
                opacity: muted ? baseOpacity * 0.4 : baseOpacity,
                filter: `blur(${blur}px)`,
                scale
              }}
              transition={SPRING}
              className={[
                "text-balance text-center font-medium leading-snug tracking-tight",
                isCurrent
                  ? "text-base text-silver-50 md:text-lg"
                  : "text-sm text-silver-400 md:text-base"
              ].join(" ")}
            >
              {cue.text}
            </motion.p>
          )
        })}
      </div>
    </div>
  )
}
