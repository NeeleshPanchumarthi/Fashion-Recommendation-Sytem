import { cn } from "@/lib/utils"
import { CATEGORY_TABS, type CategoryTab } from "@/lib/brand"

// Pill tabs above the results grid (All Products / Men / Women / Kids /
// Accessories). Selection is tracked but doesn't filter yet -- results
// don't carry a gender/category field; wiring this up is a planned feature.
export function CategoryTabs({ value, onChange }: { value: CategoryTab; onChange: (tab: CategoryTab) => void }) {
  return (
    <div role="tablist" aria-label="Product categories" className="flex flex-wrap gap-2">
      {CATEGORY_TABS.map((tab) => (
        <button
          key={tab}
          role="tab"
          aria-selected={tab === value}
          onClick={() => onChange(tab)}
          className={cn(
            "rounded-full border px-4 py-1.5 text-sm transition-colors",
            tab === value
              ? "border-ink bg-ink text-white"
              : "border-slate-200 bg-white text-slate-600 hover:border-slate-400 hover:text-ink"
          )}
        >
          {tab}
        </button>
      ))}
    </div>
  )
}
