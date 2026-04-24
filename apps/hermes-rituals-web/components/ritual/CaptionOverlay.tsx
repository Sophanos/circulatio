export function CaptionOverlay({
  text,
  muted,
  variant = "overlay"
}: {
  text: string
  muted?: boolean
  variant?: "overlay" | "inline"
}) {
  if (variant === "inline") {
    return (
      <p
        className={[
          "mx-auto max-w-xl text-balance text-center text-base font-medium leading-snug tracking-tight transition-all duration-500 md:text-lg",
          muted ? "text-silver-400 opacity-40" : "text-silver-50"
        ].join(" ")}
      >
        {text}
      </p>
    )
  }

  return (
    <div className="pointer-events-none absolute inset-x-0 bottom-0 z-10 px-6 pb-8 pt-24">
      <div className="caption-gradient absolute inset-0" />
      <p
        className={[
          "relative z-10 mx-auto max-w-xl text-balance text-center text-base font-medium leading-snug tracking-tight transition-all duration-500 md:text-lg lg:text-xl",
          muted ? "text-silver-400 opacity-40" : "text-silver-50"
        ].join(" ")}
      >
        {text}
      </p>
    </div>
  )
}
