import { useRef, useState, type MouseEvent, type TouchEvent } from "react"
import { ChevronLeft, ChevronRight, ImageOff } from "lucide-react"
import { cn } from "@/lib/utils"

interface ImageCarouselProps {
  images: string[] | null | undefined
  alt: string
  aspect?: string // tailwind aspect-ratio class, e.g. "aspect-[3/4]"
  className?: string
}

const SWIPE_THRESHOLD_PX = 40

// Slides through the large images the backend picked (MAIN, then PT01 and
// any front/back/left/right/top/bottom/side shots). Images are contained,
// not cropped, so the whole garment is always visible. A product with a
// single photo renders no controls.
export function ImageCarousel({ images, alt, aspect = "aspect-[3/4]", className }: ImageCarouselProps) {
  const [index, setIndex] = useState(0)
  const [failed, setFailed] = useState<Set<number>>(new Set())
  const touchStartX = useRef<number | null>(null)
  const list = images ?? []

  if (list.length === 0 || failed.size === list.length) {
    return (
      <div className={cn(aspect, "flex items-center justify-center bg-tile text-slate-300", className)}>
        <ImageOff className="size-10" />
      </div>
    )
  }

  const goTo = (i: number) => setIndex((i + list.length) % list.length)

  const onArrow = (e: MouseEvent, delta: number) => {
    // The carousel sits inside a <Link>; don't navigate when sliding.
    e.preventDefault()
    e.stopPropagation()
    goTo(index + delta)
  }

  const onTouchStart = (e: TouchEvent) => {
    touchStartX.current = e.touches[0].clientX
  }

  const onTouchEnd = (e: TouchEvent) => {
    if (touchStartX.current == null) return
    const dx = e.changedTouches[0].clientX - touchStartX.current
    touchStartX.current = null
    if (Math.abs(dx) > SWIPE_THRESHOLD_PX) goTo(index + (dx < 0 ? 1 : -1))
  }

  return (
    <div
      className={cn("group/carousel relative overflow-hidden bg-tile dark:bg-[#f4f3f1]", aspect, className)}
      onTouchStart={onTouchStart}
      onTouchEnd={onTouchEnd}
    >
      <div
        className="flex h-full transition-transform duration-300 ease-out"
        style={{ transform: `translateX(-${index * 100}%)` }}
      >
        {list.map((src, i) => (
          <div key={src} className="flex h-full w-full shrink-0 items-center justify-center bg-tile p-6 dark:bg-[#f4f3f1]">
            {failed.has(i) ? (
              <ImageOff className="size-10 text-slate-300" />
            ) : (
              <img
                src={src}
                alt={`${alt} (image ${i + 1} of ${list.length})`}
                className="max-h-full max-w-full object-contain mix-blend-multiply"
                loading={i === 0 ? "eager" : "lazy"}
                draggable={false}
                onError={() => setFailed((prev) => new Set(prev).add(i))}
              />
            )}
          </div>
        ))}
      </div>

      {list.length > 1 && (
        <>
          <button
            onClick={(e) => onArrow(e, -1)}
            aria-label="Previous image"
            className="absolute left-1.5 top-1/2 -translate-y-1/2 rounded-full bg-white/90 p-1.5 shadow-md transition-opacity hover:bg-white md:opacity-0 md:group-hover/carousel:opacity-100"
          >
            <ChevronLeft className="size-4 text-slate-700" />
          </button>
          <button
            onClick={(e) => onArrow(e, 1)}
            aria-label="Next image"
            className="absolute right-1.5 top-1/2 -translate-y-1/2 rounded-full bg-white/90 p-1.5 shadow-md transition-opacity hover:bg-white md:opacity-0 md:group-hover/carousel:opacity-100"
          >
            <ChevronRight className="size-4 text-slate-700" />
          </button>

          <div className="absolute bottom-2 left-1/2 flex -translate-x-1/2 gap-1.5 rounded-full bg-ink/25 px-2 py-1">
            {list.map((_, i) => (
              <button
                key={i}
                onClick={(e) => {
                  e.preventDefault()
                  e.stopPropagation()
                  goTo(i)
                }}
                aria-label={`Show image ${i + 1}`}
                className={cn(
                  "size-1.5 rounded-full transition-all",
                  i === index ? "w-3 bg-ink" : "bg-white"
                )}
              />
            ))}
          </div>
        </>
      )}
    </div>
  )
}
