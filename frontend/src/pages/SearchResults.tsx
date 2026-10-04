import { useEffect, useState } from "react"
import { useSearchParams } from "react-router-dom"
import { SlidersHorizontal, AlertCircle } from "lucide-react"
import { PageContainer } from "@/components/layout/PageContainer"
import { SearchBar } from "@/components/search/SearchBar"
import { ProductGrid } from "@/components/products/ProductGrid"
import { FilterPanel } from "@/components/filters/FilterPanel"
import { Sheet } from "@/components/ui/sheet"
import { Button } from "@/components/ui/button"
import { useSearch } from "@/hooks/useSearch"
import { useFilters } from "@/hooks/useFilters"

export default function SearchResults() {
  const [params, setParams] = useSearchParams()
  const query = params.get("q") ?? ""
  const { data, loading, error, search } = useSearch()
  const [mobileFiltersOpen, setMobileFiltersOpen] = useState(false)

  const results = data?.results ?? []
  const { filters, setFilters, filtered, reset } = useFilters(results)

  useEffect(() => {
    if (query) search(query)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [query])

  const runSearch = (q: string) => {
    setParams({ q })
  }

  return (
    <PageContainer>
      <div className="mb-6">
        <SearchBar defaultValue={query} onSearch={runSearch} />
      </div>

      {error && (
        <div className="mb-6 flex items-center gap-2 rounded-xl border border-rose-200 bg-rose-50 p-4 text-sm text-rose-700">
          <AlertCircle className="size-4 shrink-0" />
          {error}
        </div>
      )}

      <div className="flex items-center justify-between pb-4">
        <p className="text-sm text-slate-500">
          {loading ? "Searching..." : `${filtered.length} result${filtered.length === 1 ? "" : "s"}`}
          {query && !loading && (
            <>
              {" "}
              for <span className="font-medium text-slate-700">&ldquo;{query}&rdquo;</span>
            </>
          )}
        </p>
        <Button variant="outline" size="sm" className="lg:hidden" onClick={() => setMobileFiltersOpen(true)}>
          <SlidersHorizontal className="size-3.5" />
          Filters
        </Button>
      </div>

      <div className="grid gap-8 lg:grid-cols-[240px_1fr]">
        <aside className="hidden lg:block">
          <FilterPanel
            filters={filters}
            setFilters={setFilters}
            appliedFilters={data?.filters}
            onReset={reset}
          />
        </aside>

        <Sheet open={mobileFiltersOpen} onClose={() => setMobileFiltersOpen(false)} title="Filters">
          <FilterPanel
            filters={filters}
            setFilters={setFilters}
            appliedFilters={data?.filters}
            onReset={reset}
          />
        </Sheet>

        <ProductGrid products={filtered} loading={loading} />
      </div>
    </PageContainer>
  )
}
