import { useCallback, useRef, useState } from "react"
import { recommendationApi } from "@/services/recommendationApi"
import { ApiError } from "@/services/apiClient"
import type { SearchResponse } from "@/types/api"

interface UseSearchState {
  data: SearchResponse | null
  loading: boolean
  error: string | null
}

export function useSearch() {
  const [state, setState] = useState<UseSearchState>({
    data: null,
    loading: false,
    error: null,
  })
  // Only the latest search may update state. StrictMode runs effects twice
  // in dev, and a user can re-search before the previous one returns; a
  // slower, older response must not overwrite (or error over) the newer one.
  const latestRequest = useRef(0)

  const search = useCallback(async (query: string, topK?: number) => {
    if (!query.trim()) return
    const requestId = ++latestRequest.current
    setState({ data: null, loading: true, error: null })
    try {
      const data = await recommendationApi.search({ query, top_k: topK })
      if (requestId !== latestRequest.current) return
      setState({ data, loading: false, error: null })
    } catch (err) {
      if (requestId !== latestRequest.current) return
      const message = err instanceof ApiError ? err.message : "Something went wrong. Please try again."
      setState({ data: null, loading: false, error: message })
    }
  }, [])

  return { ...state, search }
}
