import { useMemo, useState } from "react"
import type { SearchResult } from "@/types/api"

// CLIENT-SIDE refinement over an already-returned result set. These are
// NOT re-sent to the backend -- the backend's own filters (gender,
// category, color, style, size, price, min_rating, sentiment) are already
// applied server-side during /search and come back in `response.filters`.
// Results only carry title/images/rating/reviews, so rating is the one
// field we can refine on here.
export interface ClientFilters {
  minRating: number | null
}

const EMPTY: ClientFilters = { minRating: null }

export function useFilters(results: SearchResult[]) {
  const [filters, setFilters] = useState<ClientFilters>(EMPTY)

  const filtered = useMemo(() => {
    return results.filter((r) => {
      if (filters.minRating && (r.average_rating ?? 0) < filters.minRating) return false
      return true
    })
  }, [results, filters])

  const reset = () => setFilters(EMPTY)

  return { filters, setFilters, filtered, reset }
}
