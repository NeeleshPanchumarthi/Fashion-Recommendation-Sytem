const EXAMPLES = [
  "black leather jacket for men",
  "floral summer dress under $50",
  "highly rated running shoes",
  "casual white sneakers women",
]

export function ExampleQueries({ onPick }: { onPick: (query: string) => void }) {
  return (
    <div className="flex flex-wrap items-center justify-center gap-2">
      <span className="text-sm text-slate-400">Try:</span>
      {EXAMPLES.map((ex) => (
        <button
          key={ex}
          onClick={() => onPick(ex)}
          className="rounded-full border border-slate-200 bg-white px-3.5 py-1.5 text-sm text-slate-600 transition-colors hover:border-violet-300 hover:bg-violet-50 hover:text-violet-700"
        >
          {ex}
        </button>
      ))}
    </div>
  )
}
