"use client"

import { type ReactNode } from "react"

import { cn } from "@/lib/utils"

export function Conversation({
  children,
  className
}: {
  children: ReactNode
  className?: string
}) {
  return (
    <div className={cn("flex min-h-0 flex-1 flex-col gap-3 overflow-y-auto", className)}>
      {children}
    </div>
  )
}

export function ConversationEmpty({ children }: { children: ReactNode }) {
  return (
    <div className="flex min-h-[160px] flex-1 items-center justify-center rounded-2xl border border-white/5 bg-white/[0.03] px-4 text-center text-sm leading-6 text-silver-400">
      {children}
    </div>
  )
}
