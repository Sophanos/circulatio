"use client"

import { type ReactNode } from "react"

import { cn } from "@/lib/utils"

export function Tool({
  title,
  children,
  className
}: {
  title: string
  children: ReactNode
  className?: string
}) {
  return (
    <div className={cn("rounded-2xl border border-white/10 bg-white/[0.05] p-3", className)}>
      <div className="text-[10px] font-medium uppercase tracking-[0.14em] text-silver-500">
        {title}
      </div>
      <div className="mt-2">{children}</div>
    </div>
  )
}
