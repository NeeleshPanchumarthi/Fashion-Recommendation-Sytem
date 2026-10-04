import { useEffect, useState } from "react"
import { useLocation, useParams, Link } from "react-router-dom"
import { Shirt, ArrowLeft, Info } from "lucide-react"
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
    <PageContainer>
      <Link to="/search" className="mb-6 inline-flex items-center gap-1 text-sm text-slate-500 hover:text-slate-700">
        <ArrowLeft className="size-3.5" />
        Back to results
      </Link>

      <div className="grid gap-8 lg:grid-cols-2">
        <ImageCarousel
          images={product.images}
          alt={product.title}
          aspect="aspect-square"
          className="rounded-2xl border border-slate-100"
        />

        <div className="flex flex-col gap-4">
          <h1 className="text-2xl font-semibold text-slate-900">{product.title}</h1>

          {product.average_rating != null && <StarRating rating={product.average_rating} size="size-4" />}

          <div className="flex gap-3 pt-2">
            <Button asChild size="lg" className="flex-1">
              <Link to="/try-on" state={{ product }}>
                <Shirt className="size-4" />
                Try On
              </Link>
            </Button>
          </div>
        </div>
      </div>

      <div className="mt-10 max-w-2xl">
        <ReviewInsights product={product} />
      </div>

      {similar.length > 0 && (
        <div className="mt-12">
          <h2 className="mb-4 text-lg font-semibold text-slate-900">Similar products</h2>
          <ProductGrid products={similar} loading={similarLoading} />
        </div>
      )}
    </PageContainer>
  )
}
