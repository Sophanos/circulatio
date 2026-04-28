import Link from "next/link"

import { getAllArtifacts } from "@/lib/mock-artifacts"

export default function HomePage() {
  const artifacts = getAllArtifacts()

  return (
    <section className="mx-auto max-w-[1440px] px-5 py-20 md:px-10 md:py-28 lg:px-14 lg:py-36">
      <div className="grid gap-8 lg:grid-cols-[1.2fr_0.8fr] lg:items-end">
        <div>
          <p className="mb-5 text-xs font-medium tracking-[0.24em] uppercase text-graphite-500">
            Artifact Surface
          </p>
          <h1 className="max-w-[11.5ch] text-[clamp(4.25rem,9vw,10rem)] font-semibold leading-[0.84] tracking-[-0.09em] text-graphite-950">
            Ritual media for thread-aware symbolic playback.
          </h1>
          <p className="mt-8 max-w-3xl text-lg leading-8 tracking-[-0.03em] text-graphite-600">
            Built as a render layer on top of Circulatio and Hermes. The frontend stays artifact-first,
            typed, and manifest-backed while the symbolic intelligence remains in the backend.
          </p>
        </div>
        <div className="media-card p-8 sm:p-10">
          <p className="text-sm leading-7 text-graphite-600">
            V1 keeps ritual, broadcast, cinema, breath, meditation, image, and body as lenses
            inside one canonical artifact player, with legacy family routes preserved as redirects.
          </p>
        </div>
      </div>

      <div className="mt-16 grid gap-5 md:grid-cols-3">
        {artifacts.map((artifact) => (
          <Link
            key={artifact.id}
            href={`/artifacts/${artifact.id}`}
            className="media-card gsap-hover-physics p-6 transition-transform duration-700 ease-out hover:scale-[1.015]"
          >
            <p className="text-xs font-medium tracking-[0.22em] uppercase text-graphite-500">
              {artifact.mode}
            </p>
            <h2 className="mt-4 text-3xl font-semibold tracking-[-0.06em] text-graphite-950">
              {artifact.title}
            </h2>
            <p className="mt-4 text-sm leading-7 text-graphite-600">{artifact.summary}</p>
          </Link>
        ))}
      </div>
    </section>
  )
}
