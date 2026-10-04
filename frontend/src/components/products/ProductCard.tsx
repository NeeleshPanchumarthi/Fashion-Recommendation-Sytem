import { Link } from "react-router-dom"
import { Star, MessageSquareQuote, ArrowUpRight } from "lucide-react"
import { ImageCarousel } from "./ImageCarousel"
import type { SearchResult } from "@/types/api"

const MAX_CARD_REVIEWS = 2

export function StarRating({ rating, size = "size-3.5" }: { rating: number; size?: string }) {
  return (
    <span className="flex items-center gap-1.5" aria-label={`${rating.toFixed(1)} out of 5 stars`}>
      <span className="text-base font-semibold text-brand-600">{rating.toFixed(1)}</span>
      <span className="flex">
        {[1, 2, 3, 4, 5].map((n) => (
          <Star
            key={n}
            className={`${size} ${rating >= n - 0.25 ? "fill-brand-600 text-brand-600" : rating >= n - 0.75 ? "fill-brand-200 text-brand-600" : "text-slate-300"}`}
          />
        ))}
      </span>
    </span>
  )
}

export function ProductCard({ product }: { product: SearchResult }) {
  const reviews = (product.review_highlights ?? []).slice(0, MAX_CARD_REVIEWS)
  const detailsLink = { to: `/product/${product.product_id}`, state: { product } }

  return (
    <article className="group flex flex-col">
      <Link {...detailsLink} className="block overflow-hidden rounded-2xl bg-tile">
        <ImageCarousel
          images={product.images}
          alt={product.title}
          className="transition-transform duration-500 group-hover:scale-[1.03]"
        />
      </Link>

      <div className="flex flex-1 flex-col gap-1.5 pt-3">
        {product.average_rating != null && <StarRating rating={product.average_rating} />}

        <Link {...detailsLink}>
          <h3 className="line-clamp-2 font-display text-[17px] leading-snug text-ink transition-colors hover:text-brand-700" title={product.title}>
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
          className="mt-auto inline-flex w-fit items-center gap-1 pt-2 text-sm font-medium text-ink underline-offset-4 transition-colors hover:text-brand-700 hover:underline"
        >
          View details
          <ArrowUpRight className="size-3.5" />
        </Link>
      </div>
    </article>
  )
}
