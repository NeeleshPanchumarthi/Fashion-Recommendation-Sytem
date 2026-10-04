import { useState, type FormEvent } from "react"
import { ArrowRight } from "lucide-react"
import { SUGGESTED_SEARCHES } from "@/lib/brand"

// Search panel for the home hero: a white pill input, then quick searches
// styled like the reference design's category list (each turns into a
// white pill with an arrow on hover).
export function HeroSearch({ onSearch }: { onSearch: (query: string) => void }) {
  const [value, setValue] = useState("")

  const submit = (e: FormEvent) => {
    e.preventDefault()
    if (value.trim()) onSearch(value.trim())
  }

  return (
    <div className="w-full max-w-md">
      <form
        onSubmit={submit}
        className="animate-slide-in flex items-center gap-2 rounded-full bg-white py-1.5 pl-5 pr-1.5 shadow-xl shadow-black/30"
        style={{ animationDelay: "700ms" }}
      >
        <input
          value={value}
          onChange={(e) => setValue(e.target.value)}
          placeholder="Describe the outfit you want…"
          aria-label="Describe the outfit you want"
          className="min-w-0 flex-1 bg-transparent text-[15px] text-ink placeholder:text-slate-400 focus:outline-none"
        />
        <button
          type="submit"
          aria-label="Search"
          className="flex size-10 shrink-0 items-center justify-center rounded-full bg-brand-600 text-white transition-colors hover:bg-brand-700"
        >
          <ArrowRight className="size-4" />
        </button>
      </form>

      <ul className="mt-3 space-y-0.5">
        {SUGGESTED_SEARCHES.map((query, i) => (
          <li key={query} className="animate-slide-in" style={{ animationDelay: `${850 + i * 110}ms` }}>
            <button
              onClick={() => onSearch(query)}
              className="group flex w-full items-center justify-between rounded-full px-5 py-2 text-left font-display text-[15px] text-white transition-all duration-300 hover:bg-white hover:text-brand-700"
            >
              {query}
              <ArrowRight className="size-4 -translate-x-2 opacity-0 transition-all duration-300 group-hover:translate-x-0 group-hover:opacity-100" />
            </button>
          </li>
        ))}
      </ul>
    </div>
  )
}
