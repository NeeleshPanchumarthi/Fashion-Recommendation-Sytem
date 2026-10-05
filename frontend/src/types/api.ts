// Mirrors the real backend schemas exactly (app/schemas/search.py).
// Do not add fields the backend doesn't return.

export interface SearchResult {
  product_id: string
  title: string
  images: string[] // large-size URLs, main image first (see app/domain/product.py)
  average_rating?: number | null
  review_highlights?: string[] | null
  // Try-on garment type; null when the product can't be tried on (shoes, hats...).
  garment_type?: GarmentType | null
  // Drive the Men / Women / Kids / Accessories tabs (see app/domain/sections.py).
  gender?: "men" | "women" | "kids" | "unisex" | null
  is_accessory?: boolean
  is_footwear?: boolean
}

export type GarmentType = "upper_body" | "lower_body" | "dresses"

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

// app/schemas/tryon.py
export type TryOnStage =
  | "queued"
  | "uploading"
  | "waiting_for_gpu"
  | "generating"
  | "finishing"
  | "done"
  | "failed"

export interface TryOnJob {
  job_id: string
  stage: TryOnStage
  garment_type: GarmentType
  queue_position?: number | null
  elapsed_seconds: number
  result_image?: string | null // data: URL once stage is "done"
  error?: string | null // user-facing reason once stage is "failed"
}
