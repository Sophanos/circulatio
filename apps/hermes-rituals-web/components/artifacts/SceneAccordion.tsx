"use client"

import { useState } from "react"

import type { PresentationArtifact } from "@/lib/artifact-contract"
import { cn } from "@/lib/utils"

export function SceneAccordion({ artifact }: { artifact: PresentationArtifact }) {
  const scenes = artifact.scenes ?? []
  const [activeId, setActiveId] = useState(scenes[0]?.id)

  return (
    <div className="grid gap-4 lg:grid-cols-3">
      {scenes.map((scene) => {
        const active = scene.id === activeId
        return (
          <button
            key={scene.id}
            type="button"
            onMouseEnter={() => setActiveId(scene.id)}
            onFocus={() => setActiveId(scene.id)}
            onClick={() => setActiveId(scene.id)}
            className={cn(
              "group media-card gsap-hover-physics min-h-[26rem] text-left transition-all duration-700",
              active ? "lg:col-span-2" : "lg:col-span-1"
            )}
          >
            <div
              className="absolute inset-0 bg-cover bg-center grayscale contrast-125 transition-transform duration-700 group-hover:scale-105"
              style={{ backgroundImage: `url(${scene.imageUrl})` }}
            />
            <div className="absolute inset-0 bg-[linear-gradient(180deg,rgba(16,19,23,0.1)_0%,rgba(16,19,23,0.78)_100%)]" />
            <div className="absolute inset-x-0 bottom-0 p-6 text-silver-100 md:p-8">
              <p className="text-xs font-medium tracking-[0.22em] uppercase text-silver-400">
                Scene
              </p>
              <h3 className="mt-3 max-w-sm text-3xl font-semibold tracking-[-0.05em] text-silver-50">
                {scene.title}
              </h3>
              <p className="mt-4 max-w-xl text-sm leading-7 text-silver-200">
                {scene.prompt}
              </p>
            </div>
          </button>
        )
      })}
    </div>
  )
}
