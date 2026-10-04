import { Link } from "react-router-dom"
import { Star, Shirt, MessageSquareQuote } from "lucide-react"
import { Card, CardContent } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { ImageCarousel } from "./ImageCarousel"
import type { SearchResult } from "@/types/api"

const MAX_CARD_REVIEWS = 2

export function StarRating({ rating, size = "size-3.5" }: { rating: number; size?: string }) {
  return (
    <span className="flex items-center gap-1" aria-label={`${rating.toFixed(1)} out of 5 stars`}>
      <span className="flex">
        {[1, 2, 3, 4, 5].map((n) => (
          <Star
            key={n}
            className={`${size} ${rating >= n - 0.25 ? "fill-amber-400 text-amber-400" : rating >= n - 0.75 ? "fill-amber-200 text-amber-400" : "text-slate-300"}`}
          />
        ))}
      </span>
      <span className="text-sm font-medium text-slate-600">{rating.toFixed(1)}</span>
    </span>
  )
}

export function ProductCard({ product }: { product: SearchResult }) {
  const reviews = (product.review_highlights ?? []).slice(0, MAX_CARD_REVIEWS)

  return (
    <Card className="flex flex-col overflow-hidden transition-shadow hover:shadow-md">
      <Link to={`/product/${product.product_id}`} state={{ product }} className="block border-b border-slate-100">
        <ImageCarousel images={product.images} alt={product.title} />
      </Link>

      <CardContent className="flex flex-1 flex-col gap-2 p-4">
        <Link to={`/product/${product.product_id}`} state={{ product }}>
          <h3 className="line-clamp-2 text-sm font-medium text-slate-900 hover:text-violet-700" title={product.title}>
            {product.title}
          </h3>
        </Link>

        {product.average_rating != null && <StarRating rating={product.average_rating} />}

        {reviews.length > 0 ? (
          <ul className="space-y-1.5">
            {reviews.map((review, i) => (
              <li key={i} className="flex gap-1.5 text-xs text-slate-500">
                <MessageSquareQuote className="mt-0.5 size-3 shrink-0 text-slate-400" />
                <span className="line-clamp-2">{review}</span>
              </li>
            ))}
          </ul>
        ) : (
          <p className="text-xs text-slate-400">No reviews yet</p>
        )}

        <div className="mt-auto flex flex-wrap gap-2 pt-2">
          <Button asChild variant="outline" size="sm" className="min-w-[6.5rem] flex-1">
            <Link to={`/product/${product.product_id}`} state={{ product }}>
              View Details
            </Link>
          </Button>
          <Button asChild variant="secondary" size="sm" className="min-w-[6.5rem] flex-1">
            <Link to="/try-on" state={{ product }}>
              <Shirt className="size-3.5" />
              Try On
            </Link>
          </Button>
        </div>
      </CardContent>
    </Card>
  )
}
