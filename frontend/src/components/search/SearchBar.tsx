import { useState, type FormEvent } from "react"
import { ArrowRight, Search } from "lucide-react"

interface SearchBarProps {
  defaultValue?: string
  onSearch: (query: string) => void
  autoFocus?: boolean
}

// Underlined field, no filled button: present but not loud.
export function SearchBar({ defaultValue = "", onSearch, autoFocus }: SearchBarProps) {
  const [value, setValue] = useState(defaultValue)

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault()
    if (value.trim()) onSearch(value.trim())
  }

  return (
    <form
      onSubmit={handleSubmit}
      className="flex w-full items-center gap-3 border-b border-neutral-300 pb-2.5 transition-colors focus-within:border-ink"
    >
      <Search className="size-[18px] shrink-0 text-neutral-400" strokeWidth={1.5} />
      <input
        value={value}
        onChange={(e) => setValue(e.target.value)}
        placeholder="Describe the outfit you want"
        aria-label="Describe the outfit you want"
        autoFocus={autoFocus}
        className="min-w-0 flex-1 bg-transparent text-base text-ink placeholder:text-neutral-400 focus:outline-none"
      />
      <button type="submit" aria-label="Search" className="text-neutral-400 transition-colors hover:text-ink">
        <ArrowRight className="size-[18px]" strokeWidth={1.5} />
      </button>
    </form>
  )
}
