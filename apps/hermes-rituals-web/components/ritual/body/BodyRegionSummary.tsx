"use client"

import { motion } from "motion/react"

import { BodyChip, BODY_MICRO_SPRING, BODY_SPRING } from "@/components/ritual/body/BodyChip"
import {
  REGION_LABELS,
  type BodyRegionId,
  type BodyView
} from "@/components/ritual/body/body-capture-model"
import { cn } from "@/lib/utils"

export function BodyRegionSummary({
  selectedRegion,
  view,
  onViewChange,
  onRegionSelect,
  disabled,
  compact,
  surface = "inline"
}: {
  selectedRegion?: BodyRegionId
  view: BodyView
  onViewChange: (view: BodyView) => void
  onRegionSelect: (region: BodyRegionId) => void
  disabled?: boolean
  compact?: boolean
  surface?: "inline" | "card"
}) {
  const selectedLabel = selectedRegion ? REGION_LABELS[selectedRegion] : "Not marked"
  const isUnclear = selectedRegion === "unclear"

  return (
    <motion.div
      className={cn(
        "flex flex-col gap-3",
        surface === "card" &&
          "rounded-[1.4rem] border border-white/10 bg-black/25 p-3 backdrop-blur-xl"
      )}
      layout
      transition={BODY_SPRING}
    >
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <p className="text-[10px] font-medium uppercase tracking-[0.16em] text-silver-500">
            Area
          </p>
          <p className={cn("mt-1 truncate font-medium text-silver-100", compact ? "text-sm" : "text-base")}>
            {selectedLabel}
          </p>
          {isUnclear ? (
            <p className="mt-1 text-xs leading-5 text-silver-500">
              No need to locate it precisely.
            </p>
          ) : null}
        </div>

        <div className="flex shrink-0 rounded-full border border-white/10 bg-white/[0.045] p-1">
          {(["front", "back"] as const).map((nextView) => {
            const active = view === nextView
            return (
              <button
                key={nextView}
                type="button"
                disabled={disabled}
                onClick={() => onViewChange(nextView)}
                className="relative rounded-full px-3 py-1.5 disabled:pointer-events-none disabled:opacity-40"
                aria-pressed={active}
              >
                {active ? (
                  <motion.span
                    layoutId="body-view-pill"
                    className="absolute inset-0 rounded-full bg-white/15"
                    transition={BODY_MICRO_SPRING}
                  />
                ) : null}
                <span
                  className={cn(
                    "relative text-[10px] font-medium uppercase tracking-[0.16em]",
                    active ? "text-silver-50" : "text-silver-500"
                  )}
                >
                  {nextView}
                </span>
              </button>
            )
          })}
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
    </motion.div>
  )
}
