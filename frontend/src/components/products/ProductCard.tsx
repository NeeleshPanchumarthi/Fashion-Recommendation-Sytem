import { useState } from "react"
import { Link } from "react-router-dom"
import { Star, MessageSquareQuote, ArrowUpRight, Sparkles } from "lucide-react"
import { ImageCarousel } from "./ImageCarousel"
import { TryOnDialog } from "@/components/tryon/TryOnDialog"
import type { SearchResult } from "@/types/api"

const MAX_CARD_REVIEWS = 2

export function StarRating({ rating, size = "size-3.5" }: { rating: number; size?: string }) {
  return (
    <span className="flex items-center gap-1.5" aria-label={`${rating.toFixed(1)} out of 5 stars`}>
      <span className="text-sm font-medium text-ink">{rating.toFixed(1)}</span>
      <span className="flex">
        {[1, 2, 3, 4, 5].map((n) => (
          <Star
            key={n}
            className={`${size} ${rating >= n - 0.25 ? "fill-ink text-ink" : rating >= n - 0.75 ? "fill-neutral-300 text-ink" : "text-neutral-300"}`}
          />
        ))}
      </span>
    </span>
  )
}

export function ProductCard({ product }: { product: SearchResult }) {
  const reviews = (product.review_highlights ?? []).slice(0, MAX_CARD_REVIEWS)
  const detailsLink = { to: `/product/${product.product_id}`, state: { product } }
  const [tryingOn, setTryingOn] = useState(false)
  const garmentType = product.images.length > 0 ? product.garment_type : null

  return (
    <article className="group flex flex-col">
      <div className="relative">
        <Link {...detailsLink} className="block overflow-hidden rounded-2xl bg-tile">
          <ImageCarousel
            images={product.images}
            alt={product.title}
            className="transition-transform duration-500 group-hover:scale-[1.03]"
          />
        </Link>
        {garmentType && (
          <button
            onClick={() => setTryingOn(true)}
            className="absolute top-3 right-3 inline-flex items-center gap-1.5 rounded-full bg-white/95 px-3 py-1.5 text-xs font-medium text-ink shadow-md backdrop-blur transition-all hover:bg-ink hover:text-white focus-visible:opacity-100 sm:-translate-y-1 sm:opacity-0 sm:group-hover:translate-y-0 sm:group-hover:opacity-100 [@media(hover:none)]:translate-y-0 [@media(hover:none)]:opacity-100"
          >
            <Sparkles className="size-3.5" />
            Try on
          </button>
        )}
      </div>
      {tryingOn && garmentType && (
        <TryOnDialog product={product} garmentType={garmentType} onClose={() => setTryingOn(false)} />
      )}

      <div className="flex flex-1 flex-col gap-1.5 pt-3">
        {product.average_rating != null && <StarRating rating={product.average_rating} />}

        <Link {...detailsLink}>
          <h3 className="line-clamp-2 text-[15px] leading-snug text-ink transition-colors hover:text-neutral-500" title={product.title}>
            {product.title}
          </h3>
        </Link>

        {reviews.length > 0 ? (
          <ul className="mt-0.5 space-y-1">
            {reviews.map((review, i) => (
              <li key={i} className="flex gap-1.5 text-xs leading-relaxed text-slate-500">
                <MessageSquareQuote className="mt-0.5 size-3 shrink-0 text-slate-400" />
                <span className="line-clamp-2">{review}</span>
              </li>
            ))}
          </ul>
        ) : (
          <p className="text-xs text-slate-400">No reviews yet</p>
        )}

        <Link
          {...detailsLink}
          className="mt-auto inline-flex w-fit items-center gap-1 pt-2 text-[13px] text-neutral-500 underline-offset-4 transition-colors hover:text-ink hover:underline"
        >
          View details
          <ArrowUpRight className="size-3.5" />
        </Link>
      </div>
    </article>
  )
}
