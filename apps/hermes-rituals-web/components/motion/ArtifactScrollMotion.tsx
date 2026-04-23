"use client"

import * as React from "react"
import { useGSAP } from "@gsap/react"
import gsap from "gsap"
import { ScrollTrigger } from "gsap/ScrollTrigger"

gsap.registerPlugin(ScrollTrigger, useGSAP)

export function ArtifactScrollMotion({ children }: React.PropsWithChildren) {
  const scope = React.useRef<HTMLDivElement | null>(null)

  useGSAP(
    () => {
      const cards = gsap.utils.toArray<HTMLElement>(".gsap-media-card")

      cards.forEach((card) => {
        gsap.fromTo(
          card,
          { scale: 0.92, opacity: 0.55, filter: "brightness(0.82)" },
          {
            scale: 1,
            opacity: 1,
            filter: "brightness(1)",
            ease: "power3.out",
            scrollTrigger: {
              trigger: card,
              start: "top 88%",
              end: "bottom 24%",
              scrub: 0.8
            }
          }
        )
      })

      const cleanups: Array<() => void> = []
      const hoverTargets = gsap.utils.toArray<HTMLElement>(".gsap-hover-physics")

      hoverTargets.forEach((target) => {
        const xTo = gsap.quickTo(target, "x", { duration: 0.42, ease: "power3.out" })
        const yTo = gsap.quickTo(target, "y", { duration: 0.42, ease: "power3.out" })
        const rotateTo = gsap.quickTo(target, "rotate", { duration: 0.42, ease: "power3.out" })

        const handleMove = (event: MouseEvent) => {
          const bounds = target.getBoundingClientRect()
          const x = event.clientX - bounds.left - bounds.width / 2
          const y = event.clientY - bounds.top - bounds.height / 2
          xTo(x * 0.02)
          yTo(y * 0.025)
          rotateTo(x * 0.008)
        }

        const handleLeave = () => {
          xTo(0)
          yTo(0)
          rotateTo(0)
        }

        target.addEventListener("mousemove", handleMove)
        target.addEventListener("mouseleave", handleLeave)
        cleanups.push(() => {
          target.removeEventListener("mousemove", handleMove)
          target.removeEventListener("mouseleave", handleLeave)
        })
      })

      return () => cleanups.forEach((cleanup) => cleanup())
    },
    { scope }
  )

  return <div ref={scope}>{children}</div>
}
