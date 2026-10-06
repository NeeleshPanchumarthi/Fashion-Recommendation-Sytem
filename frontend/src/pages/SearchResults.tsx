import { useEffect, useMemo, useState } from "react"
import { useSearchParams } from "react-router-dom"
import { SlidersHorizontal, AlertCircle } from "lucide-react"
import { PageContainer } from "@/components/layout/PageContainer"
import { SearchBar } from "@/components/search/SearchBar"
import { CategoryTabs } from "@/components/search/CategoryTabs"
import { ProductGrid } from "@/components/products/ProductGrid"
import { FilterPanel } from "@/components/filters/FilterPanel"
import { Sheet } from "@/components/ui/sheet"
import { useSearch } from "@/hooks/useSearch"
import { useFilters } from "@/hooks/useFilters"
import { CATEGORY_TABS, inTab, parseTab, type CategoryTab } from "@/lib/brand"

export default function SearchResults() {
  const [params, setParams] = useSearchParams()
  const query = params.get("q") ?? ""
  const tab = parseTab(params.get("tab"))
  const { data, loading, error, search } = useSearch()
  const [mobileFiltersOpen, setMobileFiltersOpen] = useState(false)

  const results = data?.results ?? []
  const { filters, setFilters, filtered: ratingFiltered, reset } = useFilters(results)

  const counts = useMemo(
    () =>
      Object.fromEntries(
        CATEGORY_TABS.map(({ slug }) => [slug, ratingFiltered.filter((r) => inTab(r, slug)).length])
      ) as Record<CategoryTab, number>,
    [ratingFiltered]
  )
  const filtered = useMemo(() => ratingFiltered.filter((r) => inTab(r, tab)), [ratingFiltered, tab])

  // The tab lives in the URL (?q=...&tab=men) so it survives refresh/back/share.
  const go = (q: string, nextTab: CategoryTab) => setParams(nextTab === "all" ? { q } : { q, tab: nextTab })

  // A gender tab can be empty because retrieval only returns what the query
  // matched (kids' items only when asked for). Offer a one-click re-search.
  const searchGender = data?.filters?.gender
  const tabLabel = CATEGORY_TABS.find((t) => t.slug === tab)?.label ?? ""
  const canRefine = (tab === "men" || tab === "women" || tab === "kids") && !searchGender

  useEffect(() => {
    if (query) search(query)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [query])

  const filterPanel = (
    <FilterPanel filters={filters} setFilters={setFilters} appliedFilters={data?.filters} onReset={reset} />
  )

  return (
    <PageContainer className="pt-10">
      <div className="mb-12 max-w-2xl">
        <SearchBar key={query} defaultValue={query} onSearch={(q) => go(q, tab)} autoFocus={!query} />
      </div>

      {error && (
        <div className="mb-8 flex items-center gap-2 border-l-2 border-brand-600 bg-neutral-50 px-4 py-3 text-sm text-neutral-700">
          <AlertCircle className="size-4 shrink-0 text-brand-600" />
          {error}
        </div>
      )}

      {data?.message && (
        <div className="mb-8 flex items-center gap-2 border-l-2 border-brand-600 bg-neutral-50 px-4 py-3 text-sm text-neutral-700">
          <AlertCircle className="size-4 shrink-0 text-brand-600" />
          {data.message}
        </div>
      )}

      <div className="mb-10">
        <p className="text-[11px] uppercase tracking-[0.25em] text-neutral-400">
          {!query ? "Search" : loading ? "Searching" : `${filtered.length} result${filtered.length === 1 ? "" : "s"}`}
        </p>
        <h1 className="mt-2 font-display text-3xl leading-tight text-ink sm:text-4xl">
          {query ? query : "What are you looking for?"}
        </h1>
        {data?.translated_query && (
          <p className="mt-2 text-sm text-neutral-500">Showing results for &ldquo;{data.translated_query}&rdquo;</p>
        )}
        <div className="mt-6 flex items-center justify-between gap-4 border-b border-neutral-200 pb-3">
          <CategoryTabs value={tab} onChange={(t) => go(query, t)} counts={counts} />
          <button
            className="flex items-center gap-1.5 text-[13px] text-neutral-500 hover:text-ink lg:hidden"
            onClick={() => setMobileFiltersOpen(true)}
          >
            <SlidersHorizontal className="size-3.5" />
            Filters
          </button>
        </div>
      </div>

      <div className="grid gap-10 lg:grid-cols-[220px_1fr]">
        <aside className="hidden lg:block">{filterPanel}</aside>

        <Sheet open={mobileFiltersOpen} onClose={() => setMobileFiltersOpen(false)} title="Filters">
          {filterPanel}
        </Sheet>

        {!query ? (
          <div />
        ) : !loading && !error && filtered.length === 0 && results.length > 0 && tab !== "all" ? (
          <div className="flex flex-col items-center justify-center gap-3 rounded-2xl bg-tile py-20 text-center">
            <p className="font-display text-2xl text-ink">Nothing in {tabLabel} for this search</p>
            {canRefine ? (
              <button
                className="text-sm text-brand-600 underline underline-offset-4"
                onClick={() => go(`${tab} ${query}`, tab)}
              >
                Search {tabLabel.toLowerCase()} for &ldquo;{query}&rdquo;
              </button>
            ) : (
              <p className="max-w-sm text-sm text-slate-500">
                {searchGender ? `This search is already limited to ${String(searchGender)}.` : "Try another tab."}
              </p>
            )}
          </div>
        ) : (
          <ProductGrid products={filtered} loading={loading} />
        )}
      </div>
    </PageContainer>
  )
}
