import { useCallback, useState } from "react"
import { imageSearchApi } from "@/services/imageSearchApi"

// Backs the "Coming Soon" Image Search page. The upload/preview flow is
// fully real; only the final API call is a stub that always errors, so the
// page naturally lands on its "not available yet" state instead of faking
// a result.
export function useImageSearch() {
  const [preview, setPreview] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const selectFile = useCallback((file: File | null) => {
    setError(null)
    if (!file) {
      setPreview(null)
      return
    }
    setPreview(URL.createObjectURL(file))
  }, [])

  const submit = useCallback(async (file: File) => {
    setLoading(true)
    setError(null)
    try {
      await imageSearchApi.search(file)
    } catch (err) {
      setError(err instanceof Error ? err.message : "Image search isn't available yet.")
    } finally {
      setLoading(false)
    }
  }, [])

  return { preview, loading, error, selectFile, submit }
}
