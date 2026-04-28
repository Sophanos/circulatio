"use client"

import { useState } from "react"
import { Volume2, VolumeX } from "lucide-react"
import * as SliderPrimitive from "@radix-ui/react-slider"
import { motion, AnimatePresence } from "motion/react"

import { MICRO_SPRING, RITUAL_FADE } from "@/components/ritual/motion"
import type { ArtifactChannels } from "@/lib/artifact-contract"

const CHANNEL_ORDER = ["voice", "ambient", "breath", "pulse", "music"] as const

export type ChannelName = (typeof CHANNEL_ORDER)[number]

export function CompactChannelMixer({
  channels,
  onToggle,
  onGainChange
}: {
  channels?: ArtifactChannels
  onToggle?: (name: ChannelName, muted: boolean) => void
  onGainChange?: (name: ChannelName, gain: number) => void
}) {
  const [hoveredChannel, setHoveredChannel] = useState<ChannelName | null>(null)

  return (
    <div className="flex flex-col">
      {CHANNEL_ORDER.map((name) => {
        const channel = channels?.[name]
        if (!channel) return null
        const muted = channel.muted ?? false
        const gain = channel.gain ?? 0.5
        const isHovered = hoveredChannel === name

        return (
          <motion.div
            key={name}
            className={[
              "flex items-center gap-3 rounded-lg px-2 py-2.5",
              muted ? "text-silver-500" : "text-silver-100"
            ].join(" ")}
            whileHover={muted ? undefined : { backgroundColor: "rgba(255,255,255,0.04)" }}
            transition={MICRO_SPRING}
            onMouseEnter={() => setHoveredChannel(name)}
            onMouseLeave={() => setHoveredChannel((prev) => (prev === name ? null : prev))}
          >
            <motion.button
              type="button"
              onClick={() => onToggle?.(name, !muted)}
              className="flex size-6 shrink-0 items-center justify-center rounded-full"
              whileHover={{ scale: 1.08 }}
              whileTap={{ scale: 0.94 }}
              transition={MICRO_SPRING}
            >
              {muted ? <VolumeX className="size-4" /> : <Volume2 className="size-4" />}
            </motion.button>

            <div className="flex min-w-0 flex-1 items-center">
              <AnimatePresence mode="popLayout">
                {isHovered && !muted ? (
                  <motion.div
                    key="slider"
                    className="flex flex-1 items-center"
                    initial={{ opacity: 0, width: 0 }}
                    animate={{ opacity: 1, width: "auto" }}
                    exit={{ opacity: 0, width: 0 }}
                    transition={MICRO_SPRING}
                  >
                    <SliderPrimitive.Root
                      value={[gain]}
                      onValueChange={(vals) => onGainChange?.(name, vals[0])}
                      min={0}
                      max={1}
                      step={0.01}
                      className="relative flex h-4 w-full touch-none items-center select-none"
                    >
                      <SliderPrimitive.Track className="relative h-[3px] w-full grow overflow-hidden rounded-full bg-white/15">
                        <SliderPrimitive.Range className="absolute h-full bg-white/70" />
                      </SliderPrimitive.Track>
                      <SliderPrimitive.Thumb className="block size-2.5 rounded-full bg-white focus:outline-none" />
                    </SliderPrimitive.Root>
                  </motion.div>
                ) : (
                  <motion.span
                    key="label"
                    className="truncate text-sm font-medium capitalize"
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    exit={{ opacity: 0 }}
                    transition={RITUAL_FADE}
                  >
                    {name}
                  </motion.span>
                )}
              </AnimatePresence>
            </div>
          </motion.div>
        )
      })}
    </div>
  )
}
