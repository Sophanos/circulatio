"use client"

import { useState } from "react"
import { motion, AnimatePresence } from "motion/react"

import { CompactChannelMixer, type ChannelName } from "@/components/ritual/CompactChannelMixer"
import { RitualQueue } from "@/components/ritual/RitualQueue"
import { RitualSectionList, type SectionMuteHandler } from "@/components/ritual/RitualSectionList"
import { RitualTranscript } from "@/components/ritual/RitualTranscript"
import type {
  ArtifactChannels,
  PresentationArtifact,
  RitualSection
} from "@/lib/artifact-contract"

export type RailTab = "sections" | "transcript" | "channels" | "queue"

const TAB_CONTENT = {
  initial: { opacity: 0, y: 8 },
  animate: { opacity: 1, y: 0 },
  exit: { opacity: 0, y: -8 },
  transition: { duration: 0.2, ease: "easeOut" as const }
}

export function RitualRail({
  artifact,
  currentMs,
  sections,
  channels,
  activeTab,
  onTabChange,
  onToggleSectionMute,
  onToggleChannelMute,
  onChannelGainChange,
  onSeek
}: {
  artifact: PresentationArtifact
  currentMs: number
  sections: RitualSection[]
  channels?: ArtifactChannels
  activeTab?: RailTab
  onTabChange?: (tab: RailTab) => void
  onToggleSectionMute?: SectionMuteHandler
  onToggleChannelMute?: (name: string, muted: boolean) => void
  onChannelGainChange?: (name: ChannelName, gain: number) => void
  onSeek?: (ms: number) => void
}) {
  const [internalTab, setInternalTab] = useState<RailTab>("sections")
  const tab = activeTab ?? internalTab
  const setTab = onTabChange ?? setInternalTab
  const activeSectionId = sections.find(
    (section) => currentMs >= section.startMs && currentMs < section.endMs
  )?.id

  return (
    <div className="flex h-full flex-col">
      {/* Tabs */}
      <div className="mb-3 flex items-center gap-1 rounded-2xl p-1">
        {artifact.musicQueue && (
          <TabButton active={tab === "queue"} onClick={() => setTab("queue")}>
            Queue
          </TabButton>
        )}
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

      {/* Content — animated transitions between tabs */}
      <div className="min-h-0 flex-1 overflow-y-auto rounded-2xl px-3 py-3">
        <AnimatePresence mode="wait" initial={false}>
          {tab === "queue" && (
            <motion.div key="queue" {...TAB_CONTENT}>
              <RitualQueue
                queue={artifact.musicQueue}
                activeSectionId={activeSectionId}
              />
            </motion.div>
          )}
          {tab === "sections" && (
            <motion.div key="sections" {...TAB_CONTENT}>
              <RitualSectionList
                sections={sections}
                currentMs={currentMs}
                onToggleMute={onToggleSectionMute}
                onSeek={onSeek}
              />
            </motion.div>
          )}
          {tab === "transcript" && (
            <motion.div key="transcript" {...TAB_CONTENT}>
              <RitualTranscript
                artifact={artifact}
                currentMs={currentMs}
                onSeek={onSeek}
              />
            </motion.div>
          )}
          {tab === "channels" && (
            <motion.div key="channels" {...TAB_CONTENT}>
              <CompactChannelMixer
                channels={channels}
                onToggle={(name, muted) => onToggleChannelMute?.(name, muted)}
                onGainChange={(name, gain) => onChannelGainChange?.(name, gain)}
              />
            </motion.div>
          )}
        </AnimatePresence>
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
        "flex-1 rounded-xl px-3 py-2 text-xs font-semibold transition-all duration-200",
        active
          ? "bg-white/[0.10] text-silver-100"
          : "text-silver-600 hover:text-silver-300"
      ].join(" ")}
    >
      {children}
    </button>
  )
}
