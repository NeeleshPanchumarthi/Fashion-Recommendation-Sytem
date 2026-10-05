import { useCallback, useEffect, useRef, useState } from "react"
import { tryOnApi } from "@/services/tryOnApi"
import { ApiError } from "@/services/apiClient"
import type { GarmentType, TryOnJob } from "@/types/api"

const POLL_INTERVAL_MS = 1000
// The network can drop a poll now and then; only give up after several in a row.
const MAX_POLL_FAILURES = 4

// The user's photo is remembered in memory for this browser tab only (never
// stored), so trying on several products doesn't mean uploading it again.
export interface Photo {
  file: File
  url: string // object URL for previews
}

let rememberedPhoto: Photo | null = null

export function getRememberedPhoto(): Photo | null {
  return rememberedPhoto
}

export function rememberPhoto(file: File | null): Photo | null {
  if (rememberedPhoto) URL.revokeObjectURL(rememberedPhoto.url)
  rememberedPhoto = file ? { file, url: URL.createObjectURL(file) } : null
  return rememberedPhoto
}

export type TryOnPhase = "idle" | "starting" | "running" | "done" | "failed"

export function useTryOn() {
  const [phase, setPhase] = useState<TryOnPhase>("idle")
  const [job, setJob] = useState<TryOnJob | null>(null)
  const [error, setError] = useState<string | null>(null)
  const timer = useRef<number | undefined>(undefined)
  const runId = useRef(0) // ignores responses from a run that was reset or replaced

  const stopPolling = () => window.clearTimeout(timer.current)
  useEffect(() => stopPolling, [])

  const poll = useCallback((jobId: string, id: number) => {
    const tick = (failures: number) => {
      timer.current = window.setTimeout(async () => {
        try {
          const next = await tryOnApi.getJob(jobId)
          if (id !== runId.current) return
          setJob(next)
          if (next.stage === "done") setPhase("done")
          else if (next.stage === "failed") {
            setError(next.error || "The try-on couldn't be generated.")
            setPhase("failed")
          } else tick(0)
        } catch (err) {
          if (id !== runId.current) return
          const expired = err instanceof ApiError && err.status === 404
          if (!expired && failures + 1 < MAX_POLL_FAILURES) return tick(failures + 1)
          setError(err instanceof Error ? err.message : "Lost track of the try-on.")
          setPhase("failed")
        }
      }, POLL_INTERVAL_MS)
    }
    tick(0)
  }, [])

  const start = useCallback(
    async (photo: File, garmentImageUrl: string, garmentType: GarmentType) => {
      stopPolling()
      const id = ++runId.current
      setPhase("starting")
      setError(null)
      setJob(null)
      try {
        const started = await tryOnApi.start(photo, garmentImageUrl, garmentType)
        if (id !== runId.current) return
        setJob(started)
        setPhase("running")
        poll(started.job_id, id)
      } catch (err) {
        if (id !== runId.current) return
        setError(err instanceof Error ? err.message : "Couldn't start the try-on.")
        setPhase("failed")
      }
    },
    [poll]
  )

  const reset = useCallback(() => {
    stopPolling()
    runId.current++
    setPhase("idle")
    setJob(null)
    setError(null)
  }, [])

  return { phase, job, error, start, reset }
}
