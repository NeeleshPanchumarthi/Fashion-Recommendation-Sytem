import { ProductCard } from "./ProductCard"
import { Skeleton } from "@/components/ui/skeleton"
import { SearchX } from "lucide-react"
import type { SearchResult } from "@/types/api"

export function ProductGrid({
  products,
  loading,
}: {
  products: SearchResult[]
  loading?: boolean
}) {
  if (loading) {
    return (
      <div className="grid grid-cols-2 gap-x-5 gap-y-10 sm:grid-cols-3 xl:grid-cols-4">
        {Array.from({ length: 8 }).map((_, i) => (
          <div key={i} className="space-y-3">
            <Skeleton className="aspect-[3/4] w-full rounded-2xl bg-tile" />
            <Skeleton className="h-4 w-3/4" />
            <Skeleton className="h-4 w-1/2" />
          </div>
        ))}
      </div>
    )
  }

  if (products.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center gap-3 rounded-2xl bg-tile py-20 text-center">
        <SearchX className="size-10 text-slate-300" />
        <p className="font-display text-2xl text-ink">No products matched that search</p>
        <p className="max-w-sm text-sm text-slate-500">
          Try removing a filter or rephrasing your query &mdash; e.g. fewer specific attributes
          at once.
        </p>
      </div>
    )
  }

  return (
    <div className="grid grid-cols-2 gap-x-5 gap-y-10 sm:grid-cols-3 xl:grid-cols-4">
      {products.map((p, i) => (
        <div key={p.product_id} className="animate-rise" style={{ animationDelay: `${Math.min(i, 11) * 60}ms` }}>
          <ProductCard product={p} />
        </div>
      ))}
    </div>
  )
}
