import * as React from "react"
import { X } from "lucide-react"
import { cn } from "@/lib/utils"

// Minimal slide-over drawer (mobile filters). No portal/focus-trap library
// -- purpose-built for this app's one use case.
interface SheetProps {
  open: boolean
  onClose: () => void
  title?: string
  children: React.ReactNode
}

export function Sheet({ open, onClose, title, children }: SheetProps) {
  if (!open) return null
  return (
    <div className="fixed inset-0 z-50 flex justify-end">
      <div className="absolute inset-0 bg-black/40" onClick={onClose} aria-hidden />
      <div
        className={cn(
          "relative h-full w-full max-w-sm bg-white shadow-xl",
          "animate-in slide-in-from-right duration-200"
        )}
      >
        <div className="flex items-center justify-between border-b border-slate-200 p-4">
          <h2 className="font-semibold">{title}</h2>
          <button onClick={onClose} className="rounded-md p-1.5 hover:bg-slate-100" aria-label="Close">
            <X className="size-5" />
          </button>
        </div>
        <div className="h-[calc(100%-57px)] overflow-y-auto p-4">{children}</div>
      </div>
    </div>
  )
}
