// Mirrors the real backend schemas exactly (app/schemas/*.py).
// Do not add fields the backend doesn't return.

export interface SearchResult {
  product_id: string
  title: string
  images: string[] // large-size URLs, main image first (see app/search/images.py)
  average_rating?: number | null
  review_highlights?: string[] | null
}

export interface SearchResponse {
  query: string
  detected_language?: string | null
  // Applied filters, e.g. { gender: "women", color: "red", min_rating: 4 }.
  // size CAN appear here (it's used server-side for filtering) even though
  // individual products in `results` don't carry a size field. Price never
  // does: it isn't stored in Pinecone.
  filters?: Record<string, unknown> | null
  results: SearchResult[]
}

export interface SearchRequest {
  query: string
  vector?: number[]
  top_k?: number
}
