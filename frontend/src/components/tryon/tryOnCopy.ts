// Words shown while a try-on runs. The backend reports real stages
// (uploading, in the GPU queue, generating...); the model itself gives no
// finer progress, so during "generating" we rotate garment-specific lines.
import type { GarmentType, TryOnStage } from "@/types/api"

export const GARMENT_NOUN: Record<GarmentType, string> = {
  upper_body: "top",
  lower_body: "bottoms",
  dresses: "dress",
}

// The activity log: one row per backend stage, in order.
export const STEPS: { stage: TryOnStage; label: string }[] = [
  { stage: "queued", label: "Preparing your photo" },
  { stage: "uploading", label: "Sending photos to the fitting room" },
  { stage: "waiting_for_gpu", label: "Waiting for a free stylist" },
  { stage: "generating", label: "Tailoring the outfit to you" },
  { stage: "finishing", label: "Adding the finishing touches" },
]

export const GENERATING_LINES: Record<GarmentType, string[]> = {
  upper_body: [
    "Mapping your shoulders and posture",
    "Draping the fabric over your torso",
    "Matching the sleeves to your arms",
    "Lining up the neckline",
    "Recreating prints and logos",
    "Adding natural folds and shadows",
  ],
  lower_body: [
    "Measuring your waist and hips",
    "Fitting the waistband",
    "Tailoring the leg length",
    "Matching the fabric texture",
    "Adding natural creases",
    "Blending light and shadows",
  ],
  dresses: [
    "Mapping your silhouette",
    "Fitting the dress to your shoulders",
    "Cinching the waistline",
    "Letting the hem fall naturally",
    "Matching the print and colours",
    "Adding soft folds and shadows",
  ],
}

export function headline(stage: TryOnStage, garment: GarmentType, queuePosition?: number | null): string {
  const noun = GARMENT_NOUN[garment]
  switch (stage) {
    case "queued":
      return "Getting your photo ready…"
    case "uploading":
      return `Sending you and the ${noun} to the fitting room…`
    case "waiting_for_gpu":
      return queuePosition ? `The fitting room is busy. You're #${queuePosition} in line…` : "Waiting for a free stylist…"
    case "generating":
      return `Fitting the ${noun} to you…`
    case "finishing":
      return "Almost there, polishing your look…"
    case "done":
      return "Here's your look!"
    case "failed":
      return "That didn't work out"
  }
}

// An honest-but-smooth progress estimate: each stage has a band, and inside
// "generating" (about 15s, no real progress reported) we ease toward its end.
const BANDS: Record<TryOnStage, [number, number]> = {
  queued: [3, 8],
  uploading: [8, 18],
  waiting_for_gpu: [18, 25],
  generating: [25, 88],
  finishing: [88, 97],
  done: [100, 100],
  failed: [0, 0],
}
const GENERATING_TYPICAL_SECONDS = 15

export function estimateProgress(stage: TryOnStage, secondsInStage: number): number {
  const [from, to] = BANDS[stage]
  const typical = stage === "generating" ? GENERATING_TYPICAL_SECONDS : 4
  const eased = 1 - Math.exp(-secondsInStage / typical) // approaches 1, never reaches it
  return from + (to - from) * eased
}
