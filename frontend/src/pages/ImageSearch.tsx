import { useRef } from "react"
import { Upload, AlertCircle, ImageOff } from "lucide-react"
import { PageContainer } from "@/components/layout/PageContainer"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { ComingSoonBadge } from "@/components/ai/ComingSoonCard"
import { useImageSearch } from "@/hooks/useImageSearch"

export default function ImageSearch() {
  const { preview, loading, error, selectFile, submit } = useImageSearch()
  const inputRef = useRef<HTMLInputElement>(null)

  const handleFile = (file: File | null) => {
    selectFile(file)
    if (file) submit(file)
  }

  return (
    <PageContainer className="flex flex-col items-center">
      <div className="mb-6 flex items-center gap-2">
        <h1 className="text-2xl font-semibold text-slate-900">Image-Based Search</h1>
        <ComingSoonBadge />
      </div>

      <Card className="w-full max-w-lg">
        <CardHeader>
          <CardTitle className="text-base">Upload a photo</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <button
            onClick={() => inputRef.current?.click()}
            className="flex aspect-video w-full flex-col items-center justify-center gap-2 rounded-xl border-2 border-dashed border-slate-200 bg-slate-50 text-slate-400 transition-colors hover:border-violet-300 hover:text-violet-500"
          >
            {preview ? (
              <img src={preview} alt="Preview" className="h-full w-full rounded-xl object-cover" />
            ) : (
              <>
                <Upload className="size-8" />
                <span className="text-sm">Click to upload an image</span>
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

          {loading && <p className="text-center text-sm text-slate-500">Analyzing image...</p>}

          {error && (
            <div className="flex items-start gap-2 rounded-xl border border-amber-200 bg-amber-50 p-4 text-sm text-amber-800">
              <AlertCircle className="mt-0.5 size-4 shrink-0" />
              <div>
                <p className="font-medium">Image search isn't available yet</p>
                <p className="text-amber-700/80">
                  This feature is still in development. In the meantime, try describing what
                  you're looking for in words on the Search page.
                </p>
              </div>
            </div>
          )}

          {!preview && !error && (
            <div className="flex items-center gap-2 text-xs text-slate-400">
              <ImageOff className="size-3.5" />
              No image selected yet
            </div>
          )}
        </CardContent>
      </Card>
    </PageContainer>
  )
}
