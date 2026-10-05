import { useState, type FormEvent } from "react"
import { ArrowRight } from "lucide-react"
import { SUGGESTED_SEARCHES } from "@/lib/brand"

// Understated search for the home hero: an underlined field on the photo,
// with quick searches as small text links beneath it.
export function HeroSearch({ onSearch }: { onSearch: (query: string) => void }) {
  const [value, setValue] = useState("")

  const submit = (e: FormEvent) => {
    e.preventDefault()
    if (value.trim()) onSearch(value.trim())
  }

  return (
    <div className="w-full max-w-xl">
      <form
        onSubmit={submit}
        className="group flex items-center gap-3 border-b border-white/35 pb-3 transition-colors focus-within:border-white"
      >
        <input
          value={value}
          onChange={(e) => setValue(e.target.value)}
          placeholder="Describe the outfit you want"
          aria-label="Describe the outfit you want"
          className="min-w-0 flex-1 bg-transparent text-lg text-white placeholder:text-white/45 focus:outline-none"
        />
        <button type="submit" aria-label="Search" className="text-white/60 transition-colors hover:text-white">
          <ArrowRight className="size-5" strokeWidth={1.5} />
        </button>
      </form>

      <p className="mt-4 flex flex-wrap items-center gap-x-1 gap-y-1 text-[13px] text-white/45">
        <span className="mr-1">Try</span>
        {SUGGESTED_SEARCHES.map((query, i) => (
          <span key={query} className="flex items-center gap-x-1">
            <button onClick={() => onSearch(query)} className="text-white/70 transition-colors hover:text-white">
              {query}
            </button>
            {i < SUGGESTED_SEARCHES.length - 1 && <span aria-hidden>·</span>}
          </span>
        ))}
      </p>
    </div>
  )
}
