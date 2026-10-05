import { useEffect, useRef, useState, type DragEvent } from "react"
import { Check, Download, ImagePlus, LoaderCircle, RotateCcw, ShieldCheck, Sparkles } from "lucide-react"
import { Dialog } from "@/components/ui/dialog"
import { Button } from "@/components/ui/button"
import { cn } from "@/lib/utils"
import { getRememberedPhoto, rememberPhoto, useTryOn, type Photo } from "@/hooks/useTryOn"
import { GARMENT_NOUN, GENERATING_LINES, STEPS, estimateProgress, headline } from "./tryOnCopy"
import type { GarmentType, SearchResult, TryOnStage } from "@/types/api"

const MAX_PHOTO_MB = 10
const LINE_ROTATE_MS = 2600

interface TryOnDialogProps {
  product: SearchResult
  garmentType: GarmentType
  onClose: () => void
}

// Upload a photo -> watch live progress -> see yourself wearing the product.
export function TryOnDialog({ product, garmentType, onClose }: TryOnDialogProps) {
  const [photo, setPhoto] = useState<Photo | null>(getRememberedPhoto)
  const [photoError, setPhotoError] = useState<string | null>(null)
  const { phase, job, error, start, reset } = useTryOn()
  const garmentImage = product.images[0]
  const photoUrl = photo?.url ?? null

  const choosePhoto = (file: File | undefined) => {
    if (!file) return
    if (!file.type.startsWith("image/")) return setPhotoError("Please choose an image file (JPEG, PNG or WebP).")
    if (file.size > MAX_PHOTO_MB * 1024 * 1024) return setPhotoError(`Please choose a photo under ${MAX_PHOTO_MB} MB.`)
    setPhotoError(null)
    setPhoto(rememberPhoto(file))
  }

  const generate = () => photo && start(photo.file, garmentImage, garmentType)
  const tryAnotherPhoto = () => {
    reset()
    setPhoto(rememberPhoto(null))
  }

  return (
    <Dialog open onClose={onClose} title="Virtual try-on">
      {phase === "idle" && (
        <UploadStep
          product={product}
          garmentType={garmentType}
          photoUrl={photoUrl}
          photoError={photoError}
          onChoose={choosePhoto}
          onGenerate={generate}
        />
      )}
      {(phase === "starting" || phase === "running") && photoUrl && (
        <ProgressStep
          photoUrl={photoUrl}
          garmentImage={garmentImage}
          garmentType={garmentType}
          stage={phase === "starting" ? "queued" : (job?.stage ?? "queued")}
          queuePosition={job?.queue_position}
        />
      )}
      {phase === "done" && job?.result_image && photoUrl && (
        <ResultStep
          photoUrl={photoUrl}
          resultUrl={job.result_image}
          fileName={`try-on-${product.product_id}.webp`}
          onAnotherPhoto={tryAnotherPhoto}
          onClose={onClose}
        />
      )}
      {phase === "failed" && (
        <div className="flex flex-col items-center gap-4 py-10 text-center">
          <p className="font-display text-2xl text-ink">{headline("failed", garmentType)}</p>
          <p className="max-w-md text-sm text-slate-500">{error}</p>
          <div className="flex gap-2">
            <Button variant="outline" onClick={tryAnotherPhoto}>
              Use another photo
            </Button>
            <Button onClick={generate} disabled={!photo}>
              <RotateCcw />
              Try again
            </Button>
          </div>
        </div>
      )}
    </Dialog>
  )
}

// -- Step 1: choose a photo ---------------------------------------------------

function UploadStep({
  product,
  garmentType,
  photoUrl,
  photoError,
  onChoose,
  onGenerate,
}: {
  product: SearchResult
  garmentType: GarmentType
  photoUrl: string | null
  photoError: string | null
  onChoose: (file: File | undefined) => void
  onGenerate: () => void
}) {
  const inputRef = useRef<HTMLInputElement>(null)
  const [dragging, setDragging] = useState(false)
  const fullBody = garmentType !== "upper_body"

  const onDrop = (e: DragEvent) => {
    e.preventDefault()
    setDragging(false)
    onChoose(e.dataTransfer.files[0])
  }

  return (
    <div className="grid gap-6 sm:grid-cols-[1fr_1.1fr]">
      <div>
        <input
          ref={inputRef}
          type="file"
          accept="image/jpeg,image/png,image/webp"
          className="hidden"
          onChange={(e) => onChoose(e.target.files?.[0])}
        />
        <button
          onClick={() => inputRef.current?.click()}
          onDragOver={(e) => {
            e.preventDefault()
            setDragging(true)
          }}
          onDragLeave={() => setDragging(false)}
          onDrop={onDrop}
          className={cn(
            "group relative mx-auto flex aspect-[3/4] w-full max-w-60 items-center sm:max-w-none justify-center overflow-hidden rounded-2xl border-2 border-dashed transition-colors",
            dragging ? "border-brand-500 bg-brand-50" : "border-slate-200 bg-tile hover:border-slate-400"
          )}
        >
          {photoUrl ? (
            <>
              {/* object-top matches the server's crop: centred sideways, head kept in frame. */}
              <img src={photoUrl} alt="Your photo" className="size-full object-cover object-top" />
              <span className="absolute inset-x-3 bottom-3 rounded-full bg-black/60 py-1.5 text-xs text-white opacity-0 transition-opacity group-hover:opacity-100">
                Change photo
              </span>
            </>
          ) : (
            <span className="flex flex-col items-center gap-2 px-6 text-slate-500">
              <ImagePlus className="size-9 text-slate-400" />
              <span className="text-sm font-medium text-ink">Add a photo of yourself</span>
              <span className="text-xs">Tap to upload or take one, or drag it here</span>
            </span>
          )}
        </button>
        {photoError && <p className="mt-2 text-xs text-brand-600">{photoError}</p>}
      </div>

      <div className="flex flex-col gap-5">
        <div className="flex items-center gap-3 rounded-2xl bg-tile p-3">
          <img src={product.images[0]} alt="" className="size-16 rounded-xl bg-white object-contain dark:bg-[#f4f3f1]" />
          <p className="line-clamp-2 text-sm text-ink">{product.title}</p>
        </div>

        <div>
          <p className="mb-2 text-sm font-medium text-ink">For the best fit</p>
          <ul className="space-y-1.5 text-sm text-slate-600">
            <li>• {fullBody ? "Full-length photo, head to feet" : "Waist-up or full-length photo"}</li>
            <li>• Face the camera, arms relaxed at your sides</li>
            <li>• Plain background and good light</li>
            <li>• Portrait photos work best</li>
          </ul>
        </div>

        <p className="flex items-start gap-2 text-xs text-slate-500">
          <ShieldCheck className="mt-0.5 size-4 shrink-0 text-slate-400" />
          Your photo is only used to create this preview. It isn't saved, and the result is deleted after 15 minutes.
        </p>

        <Button size="lg" className="mt-auto" disabled={!photoUrl} onClick={onGenerate}>
          <Sparkles />
          Try on this {GARMENT_NOUN[garmentType]}
        </Button>
      </div>
    </div>
  )
}

// -- Step 2: live progress ----------------------------------------------------

function ProgressStep({
  photoUrl,
  garmentImage,
  garmentType,
  stage,
  queuePosition,
}: {
  photoUrl: string
  garmentImage: string
  garmentType: GarmentType
  stage: TryOnStage
  queuePosition?: number | null
}) {
  const [now, setNow] = useState(() => Date.now())
  const [startedAt] = useState(now)
  const [stageSince, setStageSince] = useState({ stage, at: now })

  // Restart the in-stage clock when the stage changes (adjust-state-during-render pattern).
  if (stageSince.stage !== stage) setStageSince({ stage, at: now })

  useEffect(() => {
    const id = window.setInterval(() => setNow(Date.now()), 200)
    return () => window.clearInterval(id)
  }, [])

  const secondsInStage = Math.max(0, (now - stageSince.at) / 1000)
  // Stage bands only go up, so the bar never moves backwards.
  const progress = estimateProgress(stage, secondsInStage)
  const elapsed = Math.floor((now - startedAt) / 1000)

  const lines = GENERATING_LINES[garmentType]
  const line = lines[Math.floor((secondsInStage * 1000) / LINE_ROTATE_MS) % lines.length]
  const current = STEPS.findIndex((s) => s.stage === stage)

  return (
    <div className="grid gap-6 sm:grid-cols-[1fr_1.1fr]">
      <div className="relative mx-auto aspect-[3/4] w-full max-w-60 overflow-hidden rounded-2xl bg-tile sm:max-w-none">
        <img src={photoUrl} alt="Your photo" className="size-full object-cover object-top opacity-80 blur-[1px]" />
        <div className="animate-scan absolute inset-x-0 h-24 bg-gradient-to-b from-transparent via-white/50 to-transparent" />
        <img
          src={garmentImage}
          alt=""
          className="absolute right-3 bottom-3 size-20 rounded-xl border-2 border-white bg-white object-contain shadow-lg"
        />
      </div>

      <div className="flex flex-col gap-5" aria-live="polite">
        <div>
          <p key={stage} className="animate-rise font-display text-2xl leading-tight text-ink">
            {headline(stage, garmentType, queuePosition)}
          </p>
          {stage === "generating" && (
            <p key={line} className="animate-rise mt-1.5 text-sm text-slate-500">
              {line}…
            </p>
          )}
        </div>

        <div>
          <div className="h-1.5 overflow-hidden rounded-full bg-slate-100">
            <div
              className="h-full rounded-full bg-brand-600 transition-[width] duration-300 ease-out"
              style={{ width: `${progress}%` }}
            />
          </div>
          <div className="mt-1.5 flex justify-between text-xs text-slate-400">
            <span>{Math.round(progress)}%</span>
            <span>{elapsed}s · usually 20–40s</span>
          </div>
        </div>

        <ol className="space-y-2.5">
          {STEPS.map((step, i) => {
            const state = i < current ? "done" : i === current ? "active" : "pending"
            return (
              <li key={step.stage} className="flex items-center gap-3 text-sm">
                <span
                  className={cn(
                    "flex size-6 shrink-0 items-center justify-center rounded-full",
                    state === "done" && "bg-ink text-white",
                    state === "active" && "bg-brand-50 text-brand-600",
                    state === "pending" && "bg-slate-100"
                  )}
                >
                  {state === "done" && <Check className="size-3.5" />}
                  {state === "active" && <LoaderCircle className="size-3.5 animate-spin" />}
                </span>
                <span className={cn(state === "pending" ? "text-slate-400" : "text-ink", state === "active" && "font-medium")}>
                  {step.label}
                  {step.stage === "waiting_for_gpu" && state === "active" && queuePosition ? ` (#${queuePosition} in line)` : ""}
                </span>
              </li>
            )
          })}
        </ol>
      </div>
    </div>
  )
}

// -- Step 3: the result -------------------------------------------------------

function ResultStep({
  photoUrl,
  resultUrl,
  fileName,
  onAnotherPhoto,
  onClose,
}: {
  photoUrl: string
  resultUrl: string
  fileName: string
  onAnotherPhoto: () => void
  onClose: () => void
}) {
  return (
    <div className="flex flex-col gap-5">
      <div className="grid grid-cols-2 gap-3">
        <figure>
          <div className="aspect-[3/4] overflow-hidden rounded-2xl bg-tile">
            <img src={photoUrl} alt="Your photo" className="size-full object-cover object-top" />
          </div>
          <figcaption className="mt-1.5 text-center text-xs text-slate-500">You</figcaption>
        </figure>
        <figure>
          <div className="animate-blur-in aspect-[3/4] overflow-hidden rounded-2xl bg-tile">
            <img src={resultUrl} alt="You wearing the product" className="size-full object-cover" />
          </div>
          <figcaption className="mt-1.5 text-center text-xs font-medium text-ink">Wearing it</figcaption>
        </figure>
      </div>
      <p className="text-center text-xs text-slate-400">
        AI-generated preview. Fit, colour and details may differ from the real product.
      </p>
      <div className="flex flex-wrap justify-center gap-2">
        <Button variant="outline" onClick={onAnotherPhoto}>
          <RotateCcw />
          Try another photo
        </Button>
        <Button variant="outline" asChild>
          <a href={resultUrl} download={fileName}>
            <Download />
            Download
          </a>
        </Button>
        <Button onClick={onClose}>Done</Button>
      </div>
    </div>
  )
}
