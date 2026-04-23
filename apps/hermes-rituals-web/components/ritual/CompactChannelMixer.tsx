"use client"

import { useCallback } from "react"
import { Volume2, VolumeX } from "lucide-react"

import type { ArtifactChannels } from "@/lib/artifact-contract"

const CHANNEL_ORDER = ["voice", "ambient", "breath", "pulse", "music"] as const

export type ChannelName = (typeof CHANNEL_ORDER)[number]

export function CompactChannelMixer({
  channels,
  onToggle
}: {
  channels?: ArtifactChannels
  onToggle?: (name: ChannelName, muted: boolean) => void
}) {
  return (
    <div className="flex items-center gap-2">
      {CHANNEL_ORDER.map((name) => {
        const channel = channels?.[name]
        if (!channel) return null
        return (
          <ChannelToggle
            key={name}
            name={name}
            muted={channel.muted}
            onToggle={onToggle}
          />
        )
      })}
    </div>
  )
}

function ChannelToggle({
  name,
  muted,
  onToggle
}: {
  name: ChannelName
  muted: boolean
  onToggle?: (name: ChannelName, muted: boolean) => void
}) {
  const handleClick = useCallback(() => {
    onToggle?.(name, !muted)
  }, [name, muted, onToggle])

  return (
    <button
      type="button"
      onClick={handleClick}
      className={[
        "flex items-center gap-1.5 rounded-full px-3 py-1.5 text-xs font-medium transition-colors",
        muted
          ? "bg-graphite-950/5 text-graphite-400"
          : "bg-graphite-950 text-silver-50"
      ].join(" ")}
    >
      {muted ? <VolumeX className="size-3.5" /> : <Volume2 className="size-3.5" />}
      <span className="capitalize">{name}</span>
    </button>
  )
}
