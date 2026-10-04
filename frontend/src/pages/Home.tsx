import { useNavigate } from "react-router-dom"
import { SearchBar } from "@/components/search/SearchBar"
import { ExampleQueries } from "@/components/search/ExampleQueries"
import { PageContainer } from "@/components/layout/PageContainer"
import { Sparkles, Zap, ShieldCheck } from "lucide-react"

const FEATURES = [
  { icon: Sparkles, title: "Natural language search", desc: "Describe what you want in plain English -- color, occasion, budget, fit." },
  { icon: Zap, title: "Hybrid AI ranking", desc: "Dense vector retrieval plus cross-encoder reranking surfaces the best matches first." },
  { icon: ShieldCheck, title: "Real review intelligence", desc: "Sentiment and highlights pulled from actual customer reviews, never fabricated." },
]

export default function Home() {
  const navigate = useNavigate()

  const goSearch = (query: string) => {
    if (!query.trim()) return
    navigate(`/search?q=${encodeURIComponent(query)}`)
  }

  return (
    <div>
      <section className="relative overflow-hidden bg-gradient-to-br from-violet-50 via-white to-pink-50 py-20">
        <PageContainer className="flex flex-col items-center gap-6 text-center">
          <Badge />
          <h1 className="max-w-2xl text-4xl font-semibold tracking-tight text-slate-900 sm:text-5xl">
            Find fashion with <span className="text-violet-600">AI-powered</span> search
          </h1>
          <p className="max-w-xl text-lg text-slate-500">
            Describe what you're looking for, and let semantic search and review intelligence do
            the rest.
          </p>
          <div className="w-full max-w-2xl">
            <SearchBar onSearch={goSearch} autoFocus />
          </div>
          <ExampleQueries onPick={goSearch} />
        </PageContainer>
      </section>

      <PageContainer className="grid gap-6 py-16 sm:grid-cols-3">
        {FEATURES.map((f) => (
          <div key={f.title} className="rounded-2xl border border-slate-200 bg-white p-6">
            <f.icon className="mb-3 size-6 text-violet-600" />
            <h3 className="mb-1 font-semibold text-slate-900">{f.title}</h3>
            <p className="text-sm text-slate-500">{f.desc}</p>
          </div>
        ))}
      </PageContainer>
    </div>
  )
}

function Badge() {
  return (
    <span className="inline-flex items-center gap-1.5 rounded-full border border-violet-200 bg-violet-50 px-3 py-1 text-xs font-medium text-violet-700">
      <Sparkles className="size-3" />
      Powered by hybrid vector search
    </span>
  )
}
