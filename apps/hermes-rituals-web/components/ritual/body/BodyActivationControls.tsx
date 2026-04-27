"use client"

import { BodyChip } from "@/components/ritual/body/BodyChip"
import {
  ACTIVATIONS,
  type BodyActivation
} from "@/components/ritual/body/body-capture-model"

export function BodyActivationControls({
  activation,
  onChoose,
  disabled,
  compact
}: {
  activation?: BodyActivation
  onChoose: (activation: BodyActivation) => void
  disabled?: boolean
  compact?: boolean
}) {
  return (
    <div className="space-y-3">
      <div>
        <p className="text-[10px] font-medium uppercase tracking-[0.16em] text-silver-500">
          Activation
        </p>
        {!compact ? (
          <p className="mt-1 text-xs leading-5 text-silver-500">
            Qualitative intensity, not a score.
          </p>
        ) : null}
      </div>

      <div className="grid grid-cols-2 gap-2">
        {ACTIVATIONS.map((item) => (
          <BodyChip
            key={item.id}
            active={activation === item.id}
            onClick={() => onChoose(item.id)}
            disabled={disabled}
            className="justify-center"
          >
            {item.label}
          </BodyChip>
        ))}
      </div>
    </div>
  )
}
