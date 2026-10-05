import { cn } from "@/lib/utils"
import { CATEGORY_TABS, type CategoryTab } from "@/lib/brand"

// Text tabs above the results grid. Each shows how many of the returned
// results belong to it; the page filters the grid by the selected tab.
export function CategoryTabs({
  value,
  onChange,
  counts,
}: {
  value: CategoryTab
  onChange: (tab: CategoryTab) => void
  counts: Record<CategoryTab, number>
}) {
  return (
    <div role="tablist" aria-label="Product categories" className="flex flex-wrap gap-x-6 gap-y-2">
      {CATEGORY_TABS.map(({ slug, label }) => (
        <button
          key={slug}
          role="tab"
          aria-selected={slug === value}
          onClick={() => onChange(slug)}
          className={cn(
            "border-b pb-1 text-[13px] transition-colors",
            slug === value ? "border-ink text-ink" : "border-transparent text-neutral-400 hover:text-ink"
          )}
        >
          {label}
          <span className="ml-1.5 text-[11px] tabular-nums text-neutral-400">{counts[slug]}</span>
        </button>
      ))}
    </div>
  )
}
