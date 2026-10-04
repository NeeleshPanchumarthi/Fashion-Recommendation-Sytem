import { useEffect, useState } from "react"
import { useLocation, useNavigate, useParams, Link } from "react-router-dom"
import { ArrowLeft, Info } from "lucide-react"
import { PageContainer } from "@/components/layout/PageContainer"
import { Button } from "@/components/ui/button"
import { ReviewInsights } from "@/components/reviews/ReviewInsights"
import { ProductGrid } from "@/components/products/ProductGrid"
import { ImageCarousel } from "@/components/products/ImageCarousel"
import { StarRating } from "@/components/products/ProductCard"
import { productApi } from "@/services/productApi"
import type { SearchResult } from "@/types/api"

export default function ProductDetails() {
  const { id } = useParams()
  const location = useLocation()
  const navigate = useNavigate()
  const product = (location.state as { product?: SearchResult } | null)?.product

  const [similar, setSimilar] = useState<SearchResult[]>([])
  const [similarLoading, setSimilarLoading] = useState(false)

  useEffect(() => {
    if (!product) return
    setSimilarLoading(true)
    productApi
      .findSimilar(product, product.product_id)
      .then(setSimilar)
      .catch(() => setSimilar([]))
      .finally(() => setSimilarLoading(false))
  }, [product])

  if (!product) {
    return (
      <PageContainer className="flex flex-col items-center gap-4 py-24 text-center">
        <Info className="size-10 text-slate-300" />
        <h1 className="text-xl font-semibold text-slate-800">We lost track of this product</h1>
        <p className="max-w-md text-sm text-slate-500">
          The backend doesn't have a lookup-by-id endpoint, so product details only load when you
          arrive here from a search result (id: <code className="text-slate-400">{id}</code>).
          Please search again.
        </p>
        <Button asChild>
          <Link to="/search">Back to search</Link>
        </Button>
      </PageContainer>
    )
  }

  return (
    <PageContainer className="pt-6">
      <button
        onClick={() => navigate(-1)}
        className="mb-6 inline-flex items-center gap-1.5 text-sm text-slate-500 transition-colors hover:text-brand-700"
      >
        <ArrowLeft className="size-3.5" />
        Back to results
      </button>

      <div className="grid gap-10 lg:grid-cols-2">
        <div className="animate-rise overflow-hidden rounded-3xl bg-tile">
          <ImageCarousel images={product.images} alt={product.title} aspect="aspect-square" />
        </div>

        <div className="animate-rise flex flex-col gap-5" style={{ animationDelay: "120ms" }}>
          <h1 className="font-display text-3xl leading-tight text-ink sm:text-4xl">{product.title}</h1>
          {product.average_rating != null && <StarRating rating={product.average_rating} size="size-4" />}
          <ReviewInsights product={product} />
        </div>
      </div>

      {(similarLoading || similar.length > 0) && (
        <div className="mt-16">
          <h2 className="mb-6 font-display text-3xl text-ink">You may also like</h2>
          <ProductGrid products={similar} loading={similarLoading} />
        </div>
      )}
    </PageContainer>
  )
}
