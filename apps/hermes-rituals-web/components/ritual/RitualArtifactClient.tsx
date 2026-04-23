"use client"

import { useCallback, useRef, useState } from "react"
import { ArrowLeft, Volume2, VolumeX } from "lucide-react"
import { useRouter } from "next/navigation"

import { RitualPlayer, type RitualPlayerHandle } from "@/components/ritual/RitualPlayer"
import { RitualRail } from "@/components/ritual/RitualRail"
import type {
  ArtifactChannels,
  PresentationArtifact,
  RitualSection,
  SessionShell
} from "@/lib/artifact-contract"

export function RitualArtifactClient({
  artifact,
  session
}: {
  artifact: PresentationArtifact
  session?: SessionShell
}) {
  const router = useRouter()
  const playerRef = useRef<RitualPlayerHandle>(null)
  const [currentMs, setCurrentMs] = useState(0)
  const [sections, setSections] = useState<RitualSection[]>(
    artifact.ritualSections ?? []
  )
  const [channels, setChannels] = useState<ArtifactChannels>(
    artifact.channels ?? {}
  )

  const handleToggleSectionMute = useCallback(
    (sectionId: string, muted: boolean) => {
      setSections((prev) =>
        prev.map((s) => (s.id === sectionId ? { ...s, muted } : s))
      )
    },
    []
  )

  const handleToggleChannelMute = useCallback(
    (name: string, muted: boolean) => {
      setChannels((prev) => ({
        ...prev,
        [name]: {
          ...prev[name as keyof ArtifactChannels],
          muted
        }
      }))
    },
    []
  )

  const handleSeek = useCallback((ms: number) => {
    playerRef.current?.seek(ms)
  }, [])

  const isMuted = sections.some(
    (s) => currentMs >= s.startMs && currentMs < s.endMs && s.muted
  )

  return (
    <div className="page-shell relative flex h-[100dvh] flex-col overflow-hidden bg-graphite-950 text-silver-50">
      {/* Full-bleed artwork background */}
      {artifact.coverImageUrl && (
        <div
          className="pointer-events-none absolute inset-0"
          style={{
            backgroundImage: `url(${artifact.coverImageUrl})`,
            backgroundSize: "cover",
            backgroundPosition: "center",
            filter: "blur(80px) saturate(0.6) brightness(0.35)",
            transform: "scale(1.15)"
          }}
        />
      )}
      <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_top,rgba(16,19,23,0.4),transparent_60%),radial-gradient(circle_at_bottom_right,rgba(16,19,23,0.5),transparent_50%)]" />

      {/* Top chrome */}
      <header className="relative z-20 flex items-center justify-between gap-4 px-5 py-4 md:px-8">
        <div className="flex items-center gap-3">
          <button
            type="button"
            onClick={() => router.back()}
            className="flex size-9 items-center justify-center rounded-full bg-white/10 text-white/80 backdrop-blur-sm transition-colors hover:bg-white/20"
            aria-label="Go back"
          >
            <ArrowLeft className="size-4" />
          </button>
          <div className="flex flex-col">
            <span className="text-[10px] font-medium uppercase tracking-wider text-silver-400">
              {artifact.mode}
            </span>
            <span className="max-w-[40vw] truncate text-sm font-medium text-silver-100">
              {artifact.title}
            </span>
          </div>
        </div>
        <div className="flex items-center gap-3">
          {session && (
            <span className="hidden text-xs text-silver-400 md:block">
              {session.continuity}
            </span>
          )}
          <div className="flex size-8 items-center justify-center rounded-full bg-white/10 text-silver-300 backdrop-blur-sm">
            {isMuted ? <VolumeX className="size-3.5" /> : <Volume2 className="size-3.5" />}
          </div>
        </div>
      </header>

      {/* Main layout */}
      <main className="relative z-10 flex min-h-0 flex-1 flex-col md:flex-row">
        {/* Left stage */}
        <section className="relative flex min-h-0 flex-1 flex-col">
          <RitualPlayer
            ref={playerRef}
            artifact={artifact}
            sections={sections}
            onTimeUpdate={setCurrentMs}
          />
        </section>

        {/* Right rail */}
        <aside className="hidden w-full shrink-0 border-l border-white/5 bg-black/20 backdrop-blur-md md:block md:w-[380px] lg:w-[420px]">
          <div className="flex h-full flex-col p-5">
            <RitualRail
              artifact={artifact}
              currentMs={currentMs}
              sections={sections}
              channels={channels}
              onToggleSectionMute={handleToggleSectionMute}
              onToggleChannelMute={handleToggleChannelMute}
              onSeek={handleSeek}
            />
          </div>
        </aside>

        {/* Mobile rail as bottom panel */}
        <div className="shrink-0 border-t border-white/5 bg-black/30 backdrop-blur-md md:hidden">
          <div className="max-h-[40vh] p-4">
            <RitualRail
              artifact={artifact}
              currentMs={currentMs}
              sections={sections}
              channels={channels}
              onToggleSectionMute={handleToggleSectionMute}
              onToggleChannelMute={handleToggleChannelMute}
              onSeek={handleSeek}
            />
          </div>
        </div>
      </main>
    </div>
  )
}
