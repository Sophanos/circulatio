"use client"

import type { PropsWithChildren } from "react"
import { usePathname } from "next/navigation"

import { TopNav } from "@/components/app/TopNav"

export function AppShell({ children }: PropsWithChildren) {
  const pathname = usePathname()
  const hideTopNav = ["/rituals/", "/broadcasts/", "/cinema/", "/live/"].some((prefix) =>
    pathname?.startsWith(prefix)
  )

  return (
    <div className={hideTopNav ? "min-h-screen" : "page-shell min-h-screen"}>
      {!hideTopNav && <TopNav />}
      <main className={hideTopNav ? "min-h-screen overflow-hidden" : "overflow-x-hidden"}>
        {children}
      </main>
    </div>
  )
}
