import type { PresentationArtifact, SessionShell } from "@/lib/artifact-contract"

function splitHeadline(title: string) {
  const words = title.split(" ")
  const splitPoint = Math.max(2, Math.ceil(words.length / 2))
  return {
    start: words.slice(0, splitPoint).join(" "),
    end: words.slice(splitPoint).join(" ")
  }
}

export function SessionHeader({
  artifact,
  session
}: {
  artifact: PresentationArtifact
  session?: SessionShell
}) {
  const headline = splitHeadline(artifact.title)

  return (
    <section className="mx-auto max-w-[1440px] px-5 pt-16 pb-20 md:px-10 md:pt-24 md:pb-28 lg:px-14 lg:pt-32 lg:pb-36">
      <div className="grid gap-10 lg:grid-cols-[1.08fr_0.92fr] lg:items-end">
        <div>
          <p className="mb-6 text-xs font-medium tracking-[0.24em] uppercase text-graphite-500">
            {artifact.mode} artifact
          </p>
          <h1 className="max-w-[11.5ch] text-[clamp(4.25rem,9vw,10rem)] font-semibold leading-[0.84] tracking-[-0.09em] text-graphite-950">
            {headline.start}
            {" "}
            <span
              className="mx-3 inline-block h-[0.82em] w-[1.85em] rounded-full align-[-0.16em] bg-cover bg-center grayscale contrast-125"
              style={{ backgroundImage: `url(${artifact.coverImageUrl})` }}
            />
            {" "}
            {headline.end}
          </h1>
          <p className="mt-8 max-w-3xl text-lg leading-8 tracking-[-0.03em] text-graphite-600">
            {artifact.summary}
          </p>
          <div className="mt-8 flex flex-wrap gap-6 text-sm text-graphite-600">
            <div>
              <div className="text-xs font-medium tracking-[0.18em] uppercase text-graphite-500">
                Session
              </div>
              <div className="mt-1">{artifact.sessionId ?? "mock-session"}</div>
            </div>
            <div>
              <div className="text-xs font-medium tracking-[0.18em] uppercase text-graphite-500">
                Journey
              </div>
              <div className="mt-1">{artifact.journeyId ?? "not linked yet"}</div>
            </div>
            <div>
              <div className="text-xs font-medium tracking-[0.18em] uppercase text-graphite-500">
                Continuity
              </div>
              <div className="mt-1">{session?.phase ?? "rendered artifact"}</div>
            </div>
          </div>
        </div>

        <div className="media-card gsap-hover-physics overflow-hidden rounded-[2.4rem]">
          <div
            className="relative aspect-[1.06/1] bg-cover bg-center grayscale contrast-125"
            style={{ backgroundImage: `url(${artifact.coverImageUrl})` }}
          >
            <div className="absolute inset-0 bg-[radial-gradient(circle_at_top,rgba(255,255,255,0.12),transparent_42%),linear-gradient(180deg,rgba(16,19,23,0)_0%,rgba(16,19,23,0.6)_100%)]" />
            <div className="absolute bottom-0 left-0 right-0 p-8 text-silver-100 md:p-10">
              <p className="text-xs font-medium tracking-[0.22em] uppercase text-silver-400">
                Thread-aware artifact
              </p>
              <p className="mt-4 max-w-md text-sm leading-7 text-silver-200">
                {session?.continuity ??
                  "The artifact stays anchored to the same held material across ritual, broadcast, and cinema surfaces."}
              </p>
            </div>
          </div>
        </div>
      </div>
    </section>
  )
}
