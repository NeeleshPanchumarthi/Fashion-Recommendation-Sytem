import { useEffect, useState } from "react"
import { useSearchParams } from "react-router-dom"
import { SlidersHorizontal, AlertCircle } from "lucide-react"
import { PageContainer } from "@/components/layout/PageContainer"
import { SearchBar } from "@/components/search/SearchBar"
import { CategoryTabs } from "@/components/search/CategoryTabs"
import { ProductGrid } from "@/components/products/ProductGrid"
import { FilterPanel } from "@/components/filters/FilterPanel"
import { Sheet } from "@/components/ui/sheet"
import { Button } from "@/components/ui/button"
import { useSearch } from "@/hooks/useSearch"
import { useFilters } from "@/hooks/useFilters"
import type { CategoryTab } from "@/lib/brand"

export default function SearchResults() {
  const [params, setParams] = useSearchParams()
  const query = params.get("q") ?? ""
  const { data, loading, error, search } = useSearch()
  const [mobileFiltersOpen, setMobileFiltersOpen] = useState(false)
  const [tab, setTab] = useState<CategoryTab>("All Products")

  const results = data?.results ?? []
  const { filters, setFilters, filtered, reset } = useFilters(results)

  useEffect(() => {
    if (query) search(query)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [query])

  const filterPanel = (
    <FilterPanel filters={filters} setFilters={setFilters} appliedFilters={data?.filters} onReset={reset} />
  )

  return (
    <PageContainer className="pt-6">
      <div className="mx-auto mb-10 max-w-3xl">
        <SearchBar key={query} defaultValue={query} onSearch={(q) => setParams({ q })} autoFocus={!query} />
      </div>

      {error && (
        <div className="mb-6 flex items-center gap-2 rounded-2xl border border-brand-200 bg-brand-50 p-4 text-sm text-brand-700">
          <AlertCircle className="size-4 shrink-0" />
          {error}
        </div>
      )}

      <div className="mb-8 flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
        <div>
          <h1 className="font-display text-4xl leading-tight text-ink sm:text-5xl">
            {query ? "Curated Styles for You" : "What are you looking for?"}
          </h1>
          <p className="mt-2 text-sm text-slate-500">
            {!query
              ? "Describe an outfit above to see matching products."
              : loading
                ? "Finding the best matches…"
                : `${filtered.length} result${filtered.length === 1 ? "" : "s"} for “${query}”`}
          </p>
        </div>
        <div className="flex items-center gap-2">
          <CategoryTabs value={tab} onChange={setTab} />
          <Button variant="outline" size="sm" className="rounded-full lg:hidden" onClick={() => setMobileFiltersOpen(true)}>
            <SlidersHorizontal className="size-3.5" />
            Filters
          </Button>
        </div>
      </div>

      <div className="grid gap-10 lg:grid-cols-[220px_1fr]">
        <aside className="hidden lg:block">{filterPanel}</aside>

        <Sheet open={mobileFiltersOpen} onClose={() => setMobileFiltersOpen(false)} title="Filters">
          {filterPanel}
        </Sheet>

        {query ? <ProductGrid products={filtered} loading={loading} /> : <div />}
      </div>
    </PageContainer>
  )
}
