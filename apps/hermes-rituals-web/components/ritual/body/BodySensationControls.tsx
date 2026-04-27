"use client"

import { PencilLine } from "lucide-react"

import { BodyChip } from "@/components/ritual/body/BodyChip"
import { SENSATIONS } from "@/components/ritual/body/body-capture-model"

export function BodySensationControls({
  sensation,
  customSensation,
  onCustomSensationChange,
  onChoose,
  disabled,
  compact
}: {
  sensation: string
  customSensation: string
  onCustomSensationChange: (value: string) => void
  onChoose: (sensation: string) => void
  disabled?: boolean
  compact?: boolean
}) {
  const visibleSensations = compact ? SENSATIONS.slice(0, 8) : SENSATIONS

  const commitCustom = () => {
    const next = customSensation.trim()
    if (next) onChoose(next)
  }

  return (
    <div className="space-y-3">
      <div>
        <p className="text-[10px] font-medium uppercase tracking-[0.16em] text-silver-500">
          Sensation
        </p>
        <p className="mt-1 text-xs leading-5 text-silver-500">
          A word for what was noticed.
        </p>
      </div>

      <div className="flex flex-wrap gap-2">
        {visibleSensations.map((item) => (
          <BodyChip
            key={item}
            active={sensation === item}
            onClick={() => onChoose(item)}
            disabled={disabled}
          >
            {item}
          </BodyChip>
        ))}
      </div>

      {!compact ? (
        <div className="flex items-center gap-2 rounded-full border border-white/10 bg-white/[0.045] px-3 py-2">
          <PencilLine className="size-4 text-silver-500" />
          <input
            value={customSensation}
            disabled={disabled}
            onChange={(event) => onCustomSensationChange(event.target.value)}
            onBlur={commitCustom}
            onKeyDown={(event) => {
              if (event.key === "Enter") {
                event.preventDefault()
                commitCustom()
              }
            }}
            placeholder="Custom sensation"
            className="min-w-0 flex-1 bg-transparent text-sm text-silver-100 outline-none placeholder:text-silver-600"
          />
        </div>
      ) : null}
    </div>
  )
}
