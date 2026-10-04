// STUB: the backend has no virtual try-on endpoint yet. Same contract as
// imageSearchApi.ts -- always rejects with a clear "not implemented" error.
export interface TryOnResult {
  resultImageUrl: never
}

export const tryOnApi = {
  async generate(_userPhoto: File, _productId: string): Promise<TryOnResult> {
    return Promise.reject(
      new Error("Virtual try-on is not implemented on the backend yet.")
    )
  },
}
