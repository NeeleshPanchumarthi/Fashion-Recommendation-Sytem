// Product search: POST /api/search (app/api/routes/search.py).
import { apiClient } from "./apiClient"
import type { SearchRequest, SearchResponse } from "@/types/api"

export const recommendationApi = {
  search(params: SearchRequest): Promise<SearchResponse> {
    return apiClient.post<SearchResponse>("/api/search", params)
  },
}
