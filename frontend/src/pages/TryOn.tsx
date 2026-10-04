import { useRef } from "react"
import { useLocation } from "react-router-dom"
import { Upload, AlertCircle } from "lucide-react"
import { PageContainer } from "@/components/layout/PageContainer"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { ComingSoonBadge } from "@/components/ai/ComingSoonCard"
import { useTryOn } from "@/hooks/useTryOn"
import type { SearchResult } from "@/types/api"

export default function TryOn() {
  const location = useLocation()
  const product = (location.state as { product?: SearchResult } | null)?.product
  const { preview, loading, error, selectFile, submit } = useTryOn()
  const inputRef = useRef<HTMLInputElement>(null)

  const handleFile = (file: File | null) => {
    selectFile(file)
    if (file) submit(file, product?.product_id ?? "unknown")
  }

  return (
    <PageContainer className="flex flex-col items-center">
      <div className="mb-6 flex items-center gap-2">
        <h1 className="text-2xl font-semibold text-slate-900">Virtual Try-On</h1>
        <ComingSoonBadge />
      </div>

      {product && <p className="mb-6 text-sm text-slate-500">For: {product.title}</p>}

      <Card className="w-full max-w-lg">
        <CardHeader>
          <CardTitle className="text-base">Upload your photo</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <button
            onClick={() => inputRef.current?.click()}
            className="flex aspect-[3/4] w-full flex-col items-center justify-center gap-2 rounded-xl border-2 border-dashed border-slate-200 bg-slate-50 text-slate-400 transition-colors hover:border-violet-300 hover:text-violet-500"
          >
            {preview ? (
              <img src={preview} alt="Preview" className="h-full w-full rounded-xl object-cover" />
            ) : (
              <>
                <Upload className="size-8" />
                <span className="text-sm">Click to upload a photo</span>
              </>
            )}
          </button>
          <input
            ref={inputRef}
            type="file"
            accept="image/*"
            className="hidden"
            onChange={(e) => handleFile(e.target.files?.[0] ?? null)}
          />

          {loading && <p className="text-center text-sm text-slate-500">Generating preview...</p>}

          {error && (
            <div className="flex items-start gap-2 rounded-xl border border-amber-200 bg-amber-50 p-4 text-sm text-amber-800">
              <AlertCircle className="mt-0.5 size-4 shrink-0" />
              <div>
                <p className="font-medium">Virtual try-on isn't available yet</p>
                <p className="text-amber-700/80">
                  This feature is still in development and will let you preview items on your own
                  photo once it ships.
                </p>
              </div>
            </div>
          )}
        </CardContent>
      </Card>
    </PageContainer>
  )
}
