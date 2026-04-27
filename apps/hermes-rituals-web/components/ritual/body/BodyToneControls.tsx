"use client"

import { BodyChip } from "@/components/ritual/body/BodyChip"
import { TONES } from "@/components/ritual/body/body-capture-model"

export function BodyToneControls({
  tone,
  onChoose,
  disabled
}: {
  tone?: string
  onChoose: (tone: string) => void
  disabled?: boolean
}) {
  return (
    <div className="space-y-3">
      <p className="text-[10px] font-medium uppercase tracking-[0.16em] text-silver-500">
        Tone
      </p>
      <div className="flex flex-wrap gap-2">
        {TONES.map((item) => (
          <BodyChip
            key={item}
            active={tone === item}
            onClick={() => onChoose(item)}
            disabled={disabled}
          >
            {item}
          </BodyChip>
        ))}
      </div>
    </div>
  )
}
