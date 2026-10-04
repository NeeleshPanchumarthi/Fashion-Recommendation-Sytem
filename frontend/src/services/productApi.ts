// IMPORTANT: the backend exposes no GET /product/:id endpoint -- only
// POST /api/v1/search. There is no way to fetch a single product by id
// from the server. "Product details" are therefore the SearchResult the
// user clicked, carried via router navigation state (see pages/ProductDetails).
//
// "Find similar" re-uses the existing /search endpoint with a query built
// from the product's own title -- it does not invent a new
// backend capability, it composes the one that already exists.
import { recommendationApi } from "./recommendationApi"
import type { SearchResult } from "@/types/api"

export const productApi = {
  async findSimilar(product: SearchResult, excludeId: string): Promise<SearchResult[]> {
    const query = product.title
    const res = await recommendationApi.search({ query, top_k: 8 })
    return res.results.filter((r) => r.product_id !== excludeId)
  },
}
