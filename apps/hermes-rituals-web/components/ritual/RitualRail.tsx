"use client"

import { useState, type ReactNode } from "react"
import { motion, AnimatePresence } from "motion/react"

import { CompactChannelMixer, type ChannelName } from "@/components/ritual/CompactChannelMixer"
import { MICRO_SPRING, RITUAL_FADE } from "@/components/ritual/motion"
import { RitualSectionList, type SectionMuteHandler } from "@/components/ritual/RitualSectionList"
import { RitualTranscript } from "@/components/ritual/RitualTranscript"
import type {
  ArtifactChannels,
  PresentationArtifact,
  RitualSection
} from "@/lib/artifact-contract"

export type RailTab = "sections" | "transcript" | "channels" | "body" | "companion"

const TAB_CONTENT = {
  initial: { opacity: 0 },
  animate: { opacity: 1 },
  exit: { opacity: 0 },
  transition: RITUAL_FADE
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
  onSeek,
  bodyPanel,
  showBodyTab,
  companionPanel,
  showCompanionTab
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
  bodyPanel?: ReactNode
  showBodyTab?: boolean
  companionPanel?: ReactNode
  showCompanionTab?: boolean
}) {
  const [internalTab, setInternalTab] = useState<RailTab>("sections")
  const tab = activeTab ?? internalTab
  const setTab = onTabChange ?? setInternalTab
  const bodyTabVisible = Boolean(showBodyTab && bodyPanel)
  const companionTabVisible = Boolean(showCompanionTab && companionPanel)
  const transcriptTabVisible = Boolean(
    artifact.transcript?.trim() || (artifact.captions?.length ?? 0) > 0
  )
  const visibleTab =
    (tab === "body" && !bodyTabVisible) || (tab === "companion" && !companionTabVisible)
      ? "sections"
      : tab

  return (
    <div className="flex h-full flex-col">
      {/* Tabs */}
      <div className="mb-3 flex items-center gap-1 rounded-2xl p-1">
        <TabButton
          active={visibleTab === "sections"}
          testId="ritual-rail-tab-sections"
          onClick={() => setTab("sections")}
        >
          Sections
        </TabButton>
        {transcriptTabVisible ? (
          <TabButton
            active={visibleTab === "transcript"}
            testId="ritual-rail-tab-transcript"
            onClick={() => setTab("transcript")}
          >
            Transcript
          </TabButton>
        ) : null}
        <TabButton
          active={visibleTab === "channels"}
          testId="ritual-rail-tab-channels"
          onClick={() => setTab("channels")}
        >
          Channels
        </TabButton>
        {bodyTabVisible ? (
          <TabButton
            active={visibleTab === "body"}
            testId="ritual-rail-tab-body"
            onClick={() => setTab("body")}
          >
            Body
          </TabButton>
        ) : null}
        {companionTabVisible ? (
          <TabButton active={visibleTab === "companion"} onClick={() => setTab("companion")}>
            Companion
          </TabButton>
        ) : null}
      </div>

      {/* Content — animated transitions between tabs */}
      <div className="min-h-0 flex-1 overflow-y-auto rounded-2xl px-3 py-3">
        <AnimatePresence mode="wait" initial={false}>
          {visibleTab === "sections" && (
            <motion.div key="sections" {...TAB_CONTENT}>
              <RitualSectionList
                sections={sections}
                currentMs={currentMs}
                onToggleMute={onToggleSectionMute}
                onSeek={onSeek}
              />
            </motion.div>
          )}
          {visibleTab === "transcript" && transcriptTabVisible && (
            <motion.div key="transcript" {...TAB_CONTENT}>
              <RitualTranscript
                artifact={artifact}
                sections={sections}
                currentMs={currentMs}
                onSeek={onSeek}
              />
            </motion.div>
          )}
          {visibleTab === "channels" && (
            <motion.div key="channels" {...TAB_CONTENT}>
              <CompactChannelMixer
                channels={channels}
                onToggle={(name, muted) => onToggleChannelMute?.(name, muted)}
                onGainChange={(name, gain) => onChannelGainChange?.(name, gain)}
              />
            </motion.div>
          )}
          {visibleTab === "body" && bodyPanel ? (
            <motion.div key="body" className="h-full" {...TAB_CONTENT}>
              {bodyPanel}
            </motion.div>
          ) : null}
          {visibleTab === "companion" && companionPanel ? (
            <motion.div key="companion" className="h-full" {...TAB_CONTENT}>
              {companionPanel}
            </motion.div>
          ) : null}
        </AnimatePresence>
      </div>
    </div>
  )
}

function TabButton({
  active,
  onClick,
  children,
  testId
}: {
  active: boolean
  onClick: () => void
  children: React.ReactNode
  testId?: string
}) {
  return (
    <motion.button
      type="button"
      data-testid={testId}
      onClick={onClick}
      className={[
        "relative flex-1 overflow-hidden rounded-xl px-3 py-2 text-xs font-semibold",
        active ? "text-silver-100" : "text-silver-600 hover:text-silver-300"
      ].join(" ")}
      whileHover={{ scale: 1.02 }}
      whileTap={{ scale: 0.96 }}
      transition={MICRO_SPRING}
    >
      {active ? (
        <motion.span
          layoutId="ritual-rail-tab-active"
          className="absolute inset-0 rounded-xl bg-white/[0.10]"
          transition={MICRO_SPRING}
        />
      ) : null}
      <span className="relative">{children}</span>
    </motion.button>
  )
}
