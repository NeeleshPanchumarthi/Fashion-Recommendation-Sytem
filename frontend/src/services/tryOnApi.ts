// Virtual try-on (app/api/tryon.py). A try-on takes 20-60s, so it's a
// job: start() returns at once and getJob() is polled for progress.
import { apiClient } from "./apiClient"
import type { GarmentType, TryOnJob } from "@/types/api"

export const tryOnApi = {
  start(photo: File, garmentImageUrl: string, garmentType: GarmentType): Promise<TryOnJob> {
    const form = new FormData()
    form.append("person_image", photo)
    form.append("garment_image_url", garmentImageUrl)
    form.append("garment_type", garmentType)
    return apiClient.postForm<TryOnJob>("/api/try-on", form)
  },

  getJob(jobId: string): Promise<TryOnJob> {
    return apiClient.get<TryOnJob>(`/api/try-on/${jobId}`)
  },
}
