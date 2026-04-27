"use client"

import { motion } from "motion/react"

import { BodyChip, BODY_SPRING } from "@/components/ritual/body/BodyChip"
import {
  BACK_BODY_REGION_IDS,
  FRONT_BODY_REGION_IDS,
  REGION_LABELS,
  type BodyRegionId,
  type BodyView
} from "@/components/ritual/body/body-capture-model"
import { cn } from "@/lib/utils"

export function BodyMapFallback({
  selectedRegion,
  view,
  onViewChange,
  onRegionSelect,
  disabled,
  compact
}: {
  selectedRegion?: BodyRegionId
  view: BodyView
  onViewChange: (view: BodyView) => void
  onRegionSelect: (region: BodyRegionId) => void
  disabled?: boolean
  compact?: boolean
}) {
  const ids = view === "front" ? FRONT_BODY_REGION_IDS : BACK_BODY_REGION_IDS
  const selectedLabel = selectedRegion ? REGION_LABELS[selectedRegion] : "No area marked"

  return (
    <motion.div
      className={cn(
        "rounded-[1.75rem] border border-white/10 bg-black/25 p-4 backdrop-blur-xl",
        compact && "p-3"
      )}
      layout
      transition={BODY_SPRING}
    >
      <div className="flex flex-col gap-4">
        <div className="flex items-start justify-between gap-3">
          <div className="min-w-0">
            <p className="text-[10px] font-medium uppercase tracking-[0.16em] text-silver-500">
              Area selector
            </p>
            <p className="mt-1 truncate text-sm font-medium text-silver-100">{selectedLabel}</p>
            <p className="mt-1 text-xs leading-5 text-silver-500">
              Choose a region from the list if the body map is unavailable.
            </p>
          </div>

          <div className="flex shrink-0 rounded-full border border-white/10 bg-white/[0.045] p-1">
            {(["front", "back"] as const).map((nextView) => (
              <button
                key={nextView}
                type="button"
                disabled={disabled}
                onClick={() => onViewChange(nextView)}
                className={cn(
                  "rounded-full px-3 py-1.5 text-[10px] font-medium uppercase tracking-[0.16em] disabled:pointer-events-none disabled:opacity-40",
                  view === nextView ? "bg-white/15 text-silver-50" : "text-silver-500"
                )}
              >
                {nextView}
              </button>
            ))}
          </div>
        </div>

        <div className="flex flex-wrap gap-2">
          <BodyChip
            active={selectedRegion === "whole_body"}
            onClick={() => onRegionSelect("whole_body")}
            disabled={disabled}
          >
            Whole body
          </BodyChip>
          <BodyChip
            active={selectedRegion === "unclear"}
            onClick={() => onRegionSelect("unclear")}
            disabled={disabled}
          >
            Unclear
          </BodyChip>
        </div>

        <div className={cn("grid gap-2", compact ? "grid-cols-2" : "grid-cols-2 sm:grid-cols-3")}>
          {ids.map((id) => (
            <BodyChip
              key={id}
              active={selectedRegion === id}
              onClick={() => onRegionSelect(id)}
              disabled={disabled}
              className="justify-center px-2"
            >
              {REGION_LABELS[id]}
            </BodyChip>
          ))}
        </div>
      </div>
    </motion.div>
  )
}
