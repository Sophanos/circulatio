export default async function LivePage({
  params
}: {
  params: Promise<{ sessionId: string }>
}) {
  const { sessionId } = await params

  return (
    <section className="mx-auto max-w-[1080px] px-5 py-20 md:px-10 md:py-28 lg:px-14 lg:py-36">
      <div className="media-card p-8 md:p-10">
        <p className="text-xs font-medium tracking-[0.22em] uppercase text-graphite-500">
          Live mode
        </p>
        <h1 className="mt-4 max-w-xl text-5xl font-semibold leading-[0.92] tracking-[-0.06em] text-graphite-950">
          Reserved for thread-aware live follow-up.
        </h1>
        <p className="mt-5 max-w-2xl text-sm leading-7 text-graphite-600">
          `live` remains intentionally separate from ritual playback in v1. Session placeholder:
          {" "}
          {sessionId}
        </p>
      </div>
    </section>
  )
}
