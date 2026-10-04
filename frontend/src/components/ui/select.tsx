import * as React from "react"
import { ChevronDown } from "lucide-react"
import { cn } from "@/lib/utils"

// Lightweight native <select>, styled to match the rest of the UI kit.
// Avoids pulling in @radix-ui/react-select for what is otherwise a plain
// dropdown (category/sort pickers).
const Select = React.forwardRef<HTMLSelectElement, React.SelectHTMLAttributes<HTMLSelectElement>>(
  ({ className, children, ...props }, ref) => (
    <div className="relative">
      <select
        ref={ref}
        className={cn(
          "h-10 w-full appearance-none rounded-lg border border-slate-200 bg-white px-3 pr-9 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-500/40",
          className
        )}
        {...props}
      >
        {children}
      </select>
      <ChevronDown className="pointer-events-none absolute right-3 top-1/2 size-4 -translate-y-1/2 text-slate-400" />
    </div>
  )
)
Select.displayName = "Select"

export { Select }
