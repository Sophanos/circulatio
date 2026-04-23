import { SpeechCapture } from "@/components/capture/SpeechCapture"

export default function CapturePage() {
  return (
    <section className="mx-auto max-w-[1080px] px-5 py-20 md:px-10 md:py-28 lg:px-14 lg:py-36">
      <div className="mb-10">
        <p className="text-xs font-medium tracking-[0.22em] uppercase text-graphite-500">Capture</p>
        <h1 className="mt-4 max-w-[11ch] text-[clamp(4rem,8vw,8rem)] font-semibold leading-[0.86] tracking-[-0.09em] text-graphite-950">
          Wake and speak before the image thins.
        </h1>
      </div>
      <SpeechCapture />
    </section>
  )
}
