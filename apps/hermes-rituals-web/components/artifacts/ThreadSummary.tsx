import type { PresentationArtifact, SessionShell } from "@/lib/artifact-contract"

export function ThreadSummary({
  artifact,
  session
}: {
  artifact: PresentationArtifact
  session?: SessionShell
}) {
  return (
    <article className="media-card gsap-media-card h-full p-8 md:p-10">
      <p className="text-xs font-medium tracking-[0.22em] uppercase text-graphite-500">
        Thread continuity
      </p>
      <h3 className="mt-4 max-w-xl text-4xl font-semibold leading-[0.94] tracking-[-0.06em] text-graphite-950">
        {artifact.threadSummary ?? session?.continuity ?? artifact.summary}
      </h3>
      <p className="mt-6 max-w-2xl text-sm leading-7 text-graphite-600">
        {session?.holdAcknowledgement ??
          "Fresh material is preserved first. Patterning and interpretation stay downstream and explicit."}
      </p>

      <div className="mt-10 grid gap-5 md:grid-cols-2">
        <div className="rounded-[1.5rem] border border-graphite-950/8 bg-silver-100/80 p-5">
          <p className="text-xs font-medium tracking-[0.18em] uppercase text-graphite-500">
            Continuity
          </p>
          <p className="mt-3 text-sm leading-7 text-graphite-700">
            {session?.continuity ??
              "The same artifact can reopen later from a stable URL without rebuilding symbolic context in the browser."}
          </p>
        </div>
        <div className="rounded-[1.5rem] border border-graphite-950/8 bg-silver-100/80 p-5">
          <p className="text-xs font-medium tracking-[0.18em] uppercase text-graphite-500">
            Alive lately
          </p>
          <ul className="mt-3 space-y-2 text-sm text-graphite-700">
            {(session?.aliveToday ?? []).map((item) => (
              <li key={item} className="flex items-center gap-2">
                <span className="h-1.5 w-1.5 rounded-full bg-graphite-950/55" />
                {item}
              </li>
            ))}
          </ul>
        </div>
      </div>
    </article>
  )
}
