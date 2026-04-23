export function CaptionOverlay({ text, muted }: { text: string; muted?: boolean }) {
  return (
    <div className="pointer-events-none absolute inset-x-0 bottom-0 z-10 px-6 pb-8 pt-24">
      <div className="caption-gradient absolute inset-0" />
      <p
        className={[
          "relative z-10 mx-auto max-w-2xl text-balance text-center text-xl font-medium leading-snug tracking-tight transition-all duration-500 md:text-2xl lg:text-3xl",
          muted ? "text-silver-400 opacity-40" : "text-silver-50"
        ].join(" ")}
      >
        {text}
      </p>
    </div>
  )
}
