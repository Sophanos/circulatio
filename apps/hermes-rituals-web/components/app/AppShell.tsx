import type { PropsWithChildren } from "react"

import { TopNav } from "@/components/app/TopNav"

export function AppShell({ children }: PropsWithChildren) {
  return (
    <div className="page-shell min-h-screen">
      <TopNav />
      <main className="overflow-x-hidden">{children}</main>
    </div>
  )
}
