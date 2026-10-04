import { Link } from "react-router-dom"
import { ImagePlus, Shirt, Search } from "lucide-react"
import { PageContainer } from "@/components/layout/PageContainer"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { ComingSoonBadge } from "@/components/ai/ComingSoonCard"

const FEATURES = [
  {
    to: "/search",
    icon: Search,
    title: "Natural Language Search",
    desc: "Describe what you want in plain words -- live now, powered by hybrid dense search + reranking.",
    live: true,
  },
  {
    to: "/image-search",
    icon: ImagePlus,
    title: "Image-Based Search",
    desc: "Upload a photo and find visually similar products.",
    live: false,
  },
  {
    to: "/try-on",
    icon: Shirt,
    title: "Virtual Try-On",
    desc: "See how an item looks on you before you buy.",
    live: false,
  },
]

export default function AIFeatures() {
  return (
    <PageContainer>
      <h1 className="mb-2 text-2xl font-semibold text-slate-900">AI Features</h1>
      <p className="mb-8 text-slate-500">What's live today, and what's coming next.</p>

      <div className="grid gap-6 sm:grid-cols-3">
        {FEATURES.map((f) => (
          <Card key={f.to}>
            <CardHeader>
              <div className="mb-2 flex items-center justify-between">
                <f.icon className="size-6 text-violet-600" />
                {!f.live && <ComingSoonBadge />}
              </div>
              <CardTitle className="text-base">{f.title}</CardTitle>
            </CardHeader>
            <CardContent>
              <p className="mb-4 text-sm text-slate-500">{f.desc}</p>
              <Button asChild variant={f.live ? "default" : "outline"} size="sm" className="w-full">
                <Link to={f.to}>{f.live ? "Try it" : "Preview"}</Link>
              </Button>
            </CardContent>
          </Card>
        ))}
      </div>
    </PageContainer>
  )
}
