import { Select } from "@/components/ui/select"
import { RotateCcw } from "lucide-react"
import type { ClientFilters } from "@/hooks/useFilters"

interface FilterPanelProps {
  filters: ClientFilters
  setFilters: (f: ClientFilters) => void
  appliedFilters?: Record<string, unknown> | null
  onReset: () => void
}

const RATING_OPTIONS = [4.5, 4, 3.5, 3]

function SectionLabel({ children }: { children: string }) {
  return <p className="mb-3 text-[11px] font-semibold uppercase tracking-[0.14em] text-slate-400">{children}</p>
}

export function FilterPanel({ filters, setFilters, appliedFilters, onReset }: FilterPanelProps) {
  const appliedEntries = Object.entries(appliedFilters ?? {}).filter(([, v]) => v != null)

  return (
    <div className="space-y-8">
      {appliedEntries.length > 0 && (
        <div>
          <SectionLabel>Understood from your query</SectionLabel>
          <div className="flex flex-wrap gap-1.5">
            {appliedEntries.map(([key, value]) => (
              <span
                key={key}
                className="inline-flex items-center gap-1 rounded-full bg-brand-50 px-3 py-1 text-xs text-brand-700"
              >
                <span className="text-brand-700/60">{key.replace(/_/g, " ")}</span>
                <span className="font-medium">{String(value)}</span>
              </span>
            ))}
          </div>
        </div>
      )}

      <div>
        <SectionLabel>Refine these results</SectionLabel>
        <label className="mb-1.5 block text-sm text-slate-600">Minimum rating</label>
        <Select
          value={filters.minRating ?? ""}
          onChange={(e) => setFilters({ ...filters, minRating: e.target.value ? Number(e.target.value) : null })}
        >
          <option value="">Any rating</option>
          {RATING_OPTIONS.map((r) => (
            <option key={r} value={r}>
              {r}+ stars
            </option>
          ))}
        </Select>
        <button
          onClick={onReset}
          className="mt-3 inline-flex items-center gap-1.5 text-xs text-slate-500 transition-colors hover:text-brand-700"
        >
          <RotateCcw className="size-3" />
          Reset
        </button>
      </div>

      <p className="text-xs leading-relaxed text-slate-400">
        Size is understood from your search text and applied automatically. Price isn't filtered on, since
        most products don't list one.
      </p>
    </div>
  )
}
