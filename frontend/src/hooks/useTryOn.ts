import { useCallback, useState } from "react"
import { tryOnApi } from "@/services/tryOnApi"

export function useTryOn() {
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

  const submit = useCallback(async (file: File, productId: string) => {
    setLoading(true)
    setError(null)
    try {
      await tryOnApi.generate(file, productId)
    } catch (err) {
      setError(err instanceof Error ? err.message : "Virtual try-on isn't available yet.")
    } finally {
      setLoading(false)
    }
  }, [])

  return { preview, loading, error, selectFile, submit }
}
