"use client"

import { useState } from "react"

import { Button } from "@/components/ui/button"
import type { ArtifactChannels } from "@/lib/artifact-contract"

const CHANNEL_ORDER = ["voice", "ambient", "breath", "pulse", "music"] as const

export function ChannelMixer({ channels }: { channels?: ArtifactChannels }) {
  const [state, setState] = useState(channels ?? {})

  return (
    <article className="media-card gsap-media-card h-full p-8 md:p-10">
      <p className="text-xs font-medium tracking-[0.22em] uppercase text-graphite-500">
        Channel mixer
      </p>
      <div className="mt-6 space-y-5">
        {CHANNEL_ORDER.map((name) => {
          const channel = state[name]
          if (!channel) return null

          return (
            <div key={name} className="rounded-[1.35rem] border border-graphite-950/8 bg-silver-100/75 p-4">
              <div className="flex items-center justify-between gap-3">
                <div>
                  <div className="text-sm font-medium capitalize text-graphite-950">{name}</div>
                  <div className="text-xs text-graphite-500">
                    {channel.muted ? "muted" : `${Math.round(channel.gain * 100)}%`}
                  </div>
                </div>
                <Button
                  variant="outline"
                  size="sm"
                  className="rounded-full"
                  onClick={() =>
                    setState((current) => ({
                      ...current,
                      [name]: {
                        ...current[name],
                        muted: !current[name]?.muted
                      }
                    }))
                  }
                >
                  {channel.muted ? "Unmute" : "Mute"}
                </Button>
              </div>
              <input
                type="range"
                min={0}
                max={100}
                value={Math.round(channel.gain * 100)}
                onChange={(event) =>
                  setState((current) => ({
                    ...current,
                    [name]: {
                      ...current[name],
                      gain: Number(event.target.value) / 100
                    }
                  }))
                }
                className="mt-4 w-full accent-[#171b1f]"
              />
            </div>
          )
        })}
      </div>
    </article>
  )
}
