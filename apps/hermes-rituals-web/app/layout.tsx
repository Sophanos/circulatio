import "./globals.css"

import type { Metadata } from "next"
import type { PropsWithChildren } from "react"

import { AppShell } from "@/components/app/AppShell"

export const metadata: Metadata = {
  title: "Hermes Rituals",
  description: "Artifact-first frontend for Rituals, Broadcasts, and Cinema."
}

export default function RootLayout({ children }: PropsWithChildren) {
  return (
    <html lang="en" className="bg-silver-100">
      <body className="font-sans">
        <AppShell>{children}</AppShell>
      </body>
    </html>
  )
}
