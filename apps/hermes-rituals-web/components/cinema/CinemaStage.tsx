"use client"

import { useEffect, useMemo, useState } from "react"

import { CaptionOverlay } from "@/components/ritual/CaptionOverlay"
import { StaticWaveform } from "@/components/ui/waveform"
import type { PresentationArtifact } from "@/lib/artifact-contract"
import { buildWaveformData } from "@/lib/mock-media"

export function CinemaStage({ artifact }: { artifact: PresentationArtifact }) {
  const [currentScene, setCurrentScene] = useState(0)
  const scenes = artifact.scenes ?? []
  const waveform = useMemo(
    () => buildWaveformData(artifact.transcript ?? artifact.summary, 90),
    [artifact.summary, artifact.transcript]
  )

  useEffect(() => {
    if (scenes.length < 2) return
    const interval = window.setInterval(() => {
      setCurrentScene((current) => (current + 1) % scenes.length)
    }, 4200)
    return () => window.clearInterval(interval)
  }, [scenes.length])

  const activeScene = scenes[currentScene] ?? scenes[0]

  return (
    <section className="grid gap-6 lg:grid-cols-[1.12fr_0.88fr]">
      <div className="media-card-dark gsap-media-card overflow-hidden">
        <div
          className="relative min-h-[36rem] bg-cover bg-center grayscale contrast-125"
          style={{ backgroundImage: `url(${activeScene?.imageUrl ?? artifact.coverImageUrl})` }}
        >
          <div className="absolute inset-0 bg-[radial-gradient(circle_at_top,rgba(255,255,255,0.12),transparent_34%),linear-gradient(180deg,rgba(16,19,23,0.18)_0%,rgba(16,19,23,0.88)_100%)]" />
          <div className="absolute inset-x-0 top-0 p-6 md:p-8">
            <p className="text-xs font-medium tracking-[0.22em] uppercase text-silver-400">
              Cinema stage
            </p>
          </div>
          <CaptionOverlay text={artifact.captions?.[currentScene]?.text ?? artifact.summary} />
        </div>
      </div>

      <div className="space-y-5">
        <article className="media-card gsap-media-card p-8">
          <p className="text-xs font-medium tracking-[0.22em] uppercase text-graphite-500">
            Scene deck
          </p>
          <div className="mt-5 space-y-3">
            {scenes.map((scene, index) => (
              <button
                key={scene.id}
                type="button"
                onClick={() => setCurrentScene(index)}
                className={`w-full rounded-[1.35rem] border p-4 text-left transition-colors ${
                  index === currentScene
                    ? "border-graphite-950 bg-graphite-950 text-silver-50"
                    : "border-graphite-950/8 bg-silver-100/75 text-graphite-950"
                }`}
              >
                <div className="text-sm font-medium">{scene.title}</div>
                <div className="mt-2 text-sm leading-7 opacity-75">{scene.prompt}</div>
              </button>
            ))}
          </div>
        </article>

        <article className="media-card gsap-media-card p-8">
          <p className="text-xs font-medium tracking-[0.22em] uppercase text-graphite-500">
            Timeline
          </p>
          <StaticWaveform data={waveform} height={120} barColor="#171b1f" className="mt-5 w-full" />
          <p className="mt-5 text-sm leading-7 text-graphite-600">
            Remotion-ready stage scaffold: scene cards, caption layer, and a restrained export affordance
            without moving narrative planning into the client.
          </p>
        </article>
      </div>
    </section>
  )
}
