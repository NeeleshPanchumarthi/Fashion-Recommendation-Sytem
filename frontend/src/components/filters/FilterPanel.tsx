import { Select } from "@/components/ui/select"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { RotateCcw } from "lucide-react"
import type { ClientFilters } from "@/hooks/useFilters"

interface FilterPanelProps {
  filters: ClientFilters
  setFilters: (f: ClientFilters) => void
  appliedFilters?: Record<string, unknown> | null
  onReset: () => void
}

const RATING_OPTIONS = [4.5, 4, 3.5, 3]

export function FilterPanel({ filters, setFilters, appliedFilters, onReset }: FilterPanelProps) {
  const appliedEntries = Object.entries(appliedFilters ?? {}).filter(([, v]) => v != null)

  return (
    <div className="space-y-6">
      {appliedEntries.length > 0 && (
        <div>
          <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-400">
            Understood from your query
          </p>
          <div className="flex flex-wrap gap-1.5">
            {appliedEntries.map(([key, value]) => (
              <Badge key={key} variant="default">
                {key.replace(/_/g, " ")}: {String(value)}
              </Badge>
            ))}
          </div>
        </div>
      )}

      <div>
        <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-400">
          Refine these results
        </p>
        <div className="space-y-3">
          <div>
            <label className="mb-1 block text-sm text-slate-600">Minimum rating</label>
            <Select
              value={filters.minRating ?? ""}
              onChange={(e) =>
                setFilters({ ...filters, minRating: e.target.value ? Number(e.target.value) : null })
              }
            >
              <option value="">Any rating</option>
              {RATING_OPTIONS.map((r) => (
                <option key={r} value={r}>
                  {r}+ stars
                </option>
              ))}
            </Select>
          </div>
        </div>
      </div>

      <Button variant="ghost" size="sm" onClick={onReset} className="w-full">
        <RotateCcw className="size-3.5" />
        Reset refinements
      </Button>

      <p className="text-xs text-slate-400">
        Size is understood from your search text and applied automatically. Price isn't filtered
        on, since most products don't list one.
      </p>
    </div>
  )
}
