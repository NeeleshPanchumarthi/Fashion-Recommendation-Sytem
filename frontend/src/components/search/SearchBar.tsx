import { useState, type FormEvent } from "react"
import { ArrowRight, Search } from "lucide-react"

interface SearchBarProps {
  defaultValue?: string
  onSearch: (query: string) => void
  autoFocus?: boolean
}

export function SearchBar({ defaultValue = "", onSearch, autoFocus }: SearchBarProps) {
  const [value, setValue] = useState(defaultValue)

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault()
    if (value.trim()) onSearch(value.trim())
  }

  return (
    <form
      onSubmit={handleSubmit}
      className="flex w-full items-center gap-3 rounded-full border border-slate-200 bg-white py-1.5 pl-5 pr-1.5 transition-shadow focus-within:border-brand-200 focus-within:shadow-lg focus-within:shadow-brand-900/5"
    >
      <Search className="size-5 shrink-0 text-slate-400" strokeWidth={1.6} />
      <input
        value={value}
        onChange={(e) => setValue(e.target.value)}
        placeholder="Describe the outfit you want — e.g. red floral dress for a summer wedding"
        aria-label="Describe the outfit you want"
        autoFocus={autoFocus}
        className="h-11 min-w-0 flex-1 bg-transparent text-[15px] placeholder:text-slate-400 focus:outline-none"
      />
      <button
        type="submit"
        className="flex h-11 shrink-0 items-center gap-2 rounded-full bg-brand-600 px-5 text-sm font-medium text-white transition-colors hover:bg-brand-700"
      >
        <span className="hidden sm:inline">Search</span>
        <ArrowRight className="size-4" />
      </button>
    </form>
  )
}
