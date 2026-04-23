"use client"

import { useState } from "react"

import { CompactChannelMixer } from "@/components/ritual/CompactChannelMixer"
import { RitualSectionList, type SectionMuteHandler } from "@/components/ritual/RitualSectionList"
import { RitualTranscript } from "@/components/ritual/RitualTranscript"
import type {
  ArtifactChannels,
  PresentationArtifact,
  RitualSection
} from "@/lib/artifact-contract"

export type RailTab = "sections" | "transcript" | "channels"

export function RitualRail({
  artifact,
  currentMs,
  sections,
  channels,
  onToggleSectionMute,
  onToggleChannelMute,
  onSeek
}: {
  artifact: PresentationArtifact
  currentMs: number
  sections: RitualSection[]
  channels?: ArtifactChannels
  onToggleSectionMute?: SectionMuteHandler
  onToggleChannelMute?: (name: string, muted: boolean) => void
  onSeek?: (ms: number) => void
}) {
  const [tab, setTab] = useState<RailTab>("sections")

  return (
    <div className="flex h-full flex-col">
      {/* Tabs */}
      <div className="mb-3 flex items-center gap-1 rounded-2xl bg-white/40 p-1 backdrop-blur-md">
        <TabButton active={tab === "sections"} onClick={() => setTab("sections")}>
          Sections
        </TabButton>
        <TabButton active={tab === "transcript"} onClick={() => setTab("transcript")}>
          Transcript
        </TabButton>
        <TabButton active={tab === "channels"} onClick={() => setTab("channels")}>
          Channels
        </TabButton>
      </div>

      {/* Content */}
      <div className="min-h-0 flex-1 overflow-y-auto rounded-2xl bg-white/40 p-4 backdrop-blur-md">
        {tab === "sections" && (
          <RitualSectionList
            sections={sections}
            currentMs={currentMs}
            onToggleMute={onToggleSectionMute}
            onSeek={onSeek}
          />
        )}
        {tab === "transcript" && (
          <RitualTranscript
            artifact={artifact}
            currentMs={currentMs}
            onSeek={onSeek}
          />
        )}
        {tab === "channels" && (
          <div className="flex flex-col gap-4">
            <p className="text-xs font-medium uppercase tracking-wider text-graphite-500">
              Channel mixer
            </p>
            <CompactChannelMixer
              channels={channels}
              onToggle={(name, muted) => onToggleChannelMute?.(name, muted)}
            />
          </div>
        )}
      </div>
    </div>
  )
}

function TabButton({
  active,
  onClick,
  children
}: {
  active: boolean
  onClick: () => void
  children: React.ReactNode
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={[
        "flex-1 rounded-xl px-3 py-2 text-xs font-medium transition-colors",
        active
          ? "bg-white text-graphite-950 shadow-sm"
          : "text-graphite-500 hover:text-graphite-800"
      ].join(" ")}
    >
      {children}
    </button>
  )
}
