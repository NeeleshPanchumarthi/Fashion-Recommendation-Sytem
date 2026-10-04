import { MessageSquareQuote } from "lucide-react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import type { SearchResult } from "@/types/api"

// Only renders fields that actually exist on SearchResult. No fabricated
// percentage bars for "fit" / "comfort" / "fabric" -- the backend doesn't
// return that breakdown, so this component doesn't invent one.
export function ReviewInsights({ product }: { product: SearchResult }) {
  const highlights = product.review_highlights ?? []

  if (highlights.length === 0) {
    return (
      <Card>
        <CardContent className="py-6 text-center text-sm text-slate-500">
          No review data available for this product yet.
        </CardContent>
      </Card>
    )
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-base">
          <MessageSquareQuote className="size-4 text-violet-600" />
          What customers say
        </CardTitle>
      </CardHeader>
      <CardContent>
        <ul className="space-y-2">
          {highlights.map((h, i) => (
            <li key={i} className="rounded-lg bg-slate-50 p-3 text-sm italic text-slate-600">
              &ldquo;{h}&rdquo;
            </li>
          ))}
        </ul>
      </CardContent>
    </Card>
  )
}
