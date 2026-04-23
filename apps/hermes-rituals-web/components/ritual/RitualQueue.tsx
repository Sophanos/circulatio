import { Disc3, ListMusic } from "lucide-react"

import type { RitualMusicQueue } from "@/lib/artifact-contract"

function serviceLabel(service?: RitualMusicQueue["service"]) {
  switch (service) {
    case "apple_music":
      return "Apple Music"
    case "local_render":
      return "Local render"
    case "host_curated":
    default:
      return "Host curated"
  }
}

export function RitualQueue({
  queue,
  activeSectionId
}: {
  queue?: RitualMusicQueue
  activeSectionId?: string
}) {
  if (!queue) {
    return (
      <div className="rounded-2xl border border-white/10 bg-white/[0.04] p-4 text-sm text-silver-400 backdrop-blur-xl">
        Attach a ritual mix to surface Apple Music or local soundtrack cues here.
      </div>
    )
  }

  return (
    <div className="flex flex-col gap-3">
      <section className="rounded-2xl border border-white/10 bg-white/[0.05] p-4 backdrop-blur-xl">
        <div className="flex items-start gap-3">
          {queue.artworkUrl ? (
            <img
              src={queue.artworkUrl}
              alt={queue.title}
              className="h-16 w-16 rounded-2xl object-cover"
            />
          ) : (
            <div className="flex h-16 w-16 items-center justify-center rounded-2xl bg-white/10 text-silver-200">
              <Disc3 className="size-6" />
            </div>
          )}
          <div className="min-w-0 flex-1">
            <div className="mb-2 flex items-center gap-2">
              <span className="rounded-full bg-white/10 px-2.5 py-1 text-[10px] font-medium uppercase tracking-[0.16em] text-silver-300">
                {serviceLabel(queue.service)}
              </span>
              <span className="text-[10px] font-medium uppercase tracking-[0.16em] text-silver-500">
                {queue.tracks.length} tracks
              </span>
            </div>
            <h3 className="truncate text-base font-medium text-silver-100">{queue.title}</h3>
            {queue.subtitle && (
              <p className="mt-1 text-sm text-silver-400">{queue.subtitle}</p>
            )}
            {queue.mixNote && (
              <p className="mt-3 text-sm leading-relaxed text-silver-300">{queue.mixNote}</p>
            )}
          </div>
        </div>
      </section>

      <section className="flex flex-col gap-2">
        {queue.tracks.map((track, index) => {
          const active = track.sectionId && track.sectionId === activeSectionId

          return (
            <div
              key={track.id}
              className={[
                "flex items-center gap-3 rounded-2xl border px-3 py-3 transition-colors",
                active
                  ? "border-white/15 bg-white/[0.10] text-silver-100"
                  : "border-white/5 bg-white/[0.03] text-silver-300"
              ].join(" ")}
            >
              {track.artworkUrl ? (
                <img
                  src={track.artworkUrl}
                  alt={track.album ?? track.title}
                  className="h-11 w-11 shrink-0 rounded-xl object-cover"
                />
              ) : (
                <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-white/8 text-silver-400">
                  <ListMusic className="size-4.5" />
                </div>
              )}

              <div className="min-w-0 flex-1">
                <div className="flex items-center gap-2">
                  <span className="text-[11px] font-medium uppercase tracking-[0.16em] text-silver-500">
                    {String(index + 1).padStart(2, "0")}
                  </span>
                  {active && (
                    <span className="rounded-full bg-white/10 px-2 py-0.5 text-[10px] font-medium uppercase tracking-[0.16em] text-silver-200">
                      Now
                    </span>
                  )}
                </div>
                <p className="truncate text-sm font-medium text-current">{track.title}</p>
                <p className="truncate text-xs text-silver-500">
                  {track.artist}
                  {track.album ? ` • ${track.album}` : ""}
                </p>
              </div>

              {track.durationLabel && (
                <span className="shrink-0 text-xs tabular-nums text-silver-500">
                  {track.durationLabel}
                </span>
              )}
            </div>
          )
        })}
      </section>
    </div>
  )
}
