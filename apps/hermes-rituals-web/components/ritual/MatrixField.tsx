"use client"

import { useMemo } from "react"

import { Matrix } from "@/components/ui/matrix"

function clamp(value: number) {
  return Math.max(0, Math.min(1, value))
}

export function MatrixField({ currentMs }: { currentMs: number }) {
  const levels = useMemo(() => {
    return Array.from({ length: 18 }, (_, index) => {
      const t = currentMs / 850
      const wave =
        Math.sin(t + index * 0.42) * 0.34 +
        Math.cos(t * 0.58 + index * 0.18) * 0.24 +
        Math.sin(t * 1.7 - index * 0.3) * 0.18
      return clamp(0.18 + wave)
    })
  }, [currentMs])

  return (
    <div className="pointer-events-none absolute inset-0 flex items-center justify-center opacity-70">
      <Matrix
        rows={10}
        cols={18}
        mode="vu"
        levels={levels}
        size={11}
        gap={5}
        brightness={0.86}
        palette={{ on: "#ffffff", off: "rgba(255,255,255,0.08)" }}
        className="scale-[1.15] blur-[0.2px]"
      />
    </div>
  )
}
