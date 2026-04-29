"use client"

import { type ReactNode } from "react"

import { cn } from "@/lib/utils"

export function Message({
  role,
  children,
  className
}: {
  role: "user" | "assistant" | "system"
  children: ReactNode
  className?: string
}) {
  return (
    <div
      className={cn(
        "rounded-2xl border px-4 py-3 text-sm leading-6 backdrop-blur-xl",
        role === "user"
          ? "border-white/10 bg-white/[0.08] text-silver-100"
          : role === "assistant"
            ? "border-white/5 bg-black/25 text-silver-200"
            : "border-white/5 bg-white/[0.03] text-silver-500",
        className
      )}
    >
      {children}
    </div>
  )
}

export function MessageLabel({ children }: { children: ReactNode }) {
  return (
    <div className="mb-1.5 text-[10px] font-medium uppercase tracking-[0.14em] text-silver-600">
      {children}
    </div>
  )
}

export function MessageText({ children }: { children: ReactNode }) {
  return <div className="whitespace-pre-wrap break-words">{children}</div>
}
