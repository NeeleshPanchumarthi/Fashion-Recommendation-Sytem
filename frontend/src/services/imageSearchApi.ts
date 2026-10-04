// STUB: the backend has no image-search endpoint yet. This interface is
// shaped like a real API call so the Image Search page's hook can be
// swapped to a real implementation later without touching the UI. It must
// never pretend to succeed -- it always rejects, clearly labeled as
// not-yet-implemented, so the page can show its "Coming Soon" state.
export interface ImageSearchResult {
  // Placeholder shape mirroring SearchResponse, for future reference.
  results: never[]
}

export const imageSearchApi = {
  async search(_image: File): Promise<ImageSearchResult> {
    return Promise.reject(
      new Error("Image-based search is not implemented on the backend yet.")
    )
  },
}
