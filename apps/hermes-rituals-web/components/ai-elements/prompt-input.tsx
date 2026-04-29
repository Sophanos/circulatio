"use client"

import { type FormEvent, type ReactNode } from "react"

import { cn } from "@/lib/utils"

export function PromptInput({
  value,
  placeholder,
  disabled,
  onChange,
  onSubmit,
  children,
  className
}: {
  value: string
  placeholder?: string
  disabled?: boolean
  onChange: (value: string) => void
  onSubmit: () => void
  children?: ReactNode
  className?: string
}) {
  const handleSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    onSubmit()
  }

  return (
    <form
      onSubmit={handleSubmit}
      className={cn(
        "rounded-2xl border border-white/10 bg-black/35 p-2 backdrop-blur-2xl",
        className
      )}
    >
      <textarea
        value={value}
        disabled={disabled}
        rows={3}
        onChange={(event) => onChange(event.currentTarget.value)}
        placeholder={placeholder}
        className="min-h-20 w-full resize-none rounded-xl border-0 bg-transparent px-3 py-2 text-sm leading-6 text-silver-100 outline-none placeholder:text-silver-600 disabled:opacity-50"
      />
      <div className="flex flex-wrap items-center justify-between gap-2 px-1 pb-1">
        {children}
      </div>
    </form>
  )
}

export function PromptInputActions({ children }: { children: ReactNode }) {
  return <div className="flex flex-wrap items-center gap-2">{children}</div>
}
