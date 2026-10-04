// The ONLY real backend endpoint: POST /api/v1/search (app/api/search.py).
import { apiClient } from "./apiClient"
import type { SearchRequest, SearchResponse } from "@/types/api"

export const recommendationApi = {
  search(params: SearchRequest): Promise<SearchResponse> {
    return apiClient.post<SearchResponse>("/api/v1/search", params)
  },
}
