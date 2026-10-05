import { useEffect, useRef, useState, type ReactNode } from "react"
import { Link } from "react-router-dom"
import { ArrowRight, CalendarDays, MessageSquareText, ScanLine, ShieldCheck, Shirt, Sparkles, Star, Upload } from "lucide-react"
import { cn } from "@/lib/utils"
import { Button } from "@/components/ui/button"
import { BRAND_NAME } from "@/lib/brand"

// Free to use under the Unsplash License.
const IMAGES = {
  context: "https://images.unsplash.com/photo-1496747611176-843222e1e57c?auto=format&fit=crop&w=1200&q=80",
  tryOn: "https://images.unsplash.com/photo-1483985988355-763728e1935b?auto=format&fit=crop&w=1200&q=80",
}

// Fades and lifts its children in once they scroll into view.
function Reveal({ children, className }: { children: ReactNode; className?: string }) {
  const ref = useRef<HTMLDivElement>(null)
  const [shown, setShown] = useState(false)

  useEffect(() => {
    const el = ref.current
    if (!el) return
    const io = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) {
          setShown(true)
          io.disconnect()
        }
      },
      { threshold: 0.15 }
    )
    io.observe(el)
    return () => io.disconnect()
  }, [])

  return (
    <div
      ref={ref}
      className={cn("transition-all duration-700 ease-out", shown ? "translate-y-0 opacity-100" : "translate-y-8 opacity-0", className)}
    >
      {children}
    </div>
  )
}

interface Feature {
  id: string
  eyebrow: string
  title: string
  body: string
  image: string
  imageAlt: string
  points: { icon: typeof Star; title: string; text: string }[]
  cta: ReactNode
  badge: { icon: typeof Star; text: string }
}

const FEATURES: Feature[] = [
  {
    id: "features",
    eyebrow: "Contextual recommendations",
    title: "Describe the occasion, not the product.",
    body: `Traditional search matches keywords. ${BRAND_NAME} understands intent: the event, the season, the dress code and your own taste, and returns outfits that suit the whole picture.`,
    image: IMAGES.context,
    imageAlt: "Woman in a floral summer dress by the sea",
    badge: { icon: CalendarDays, text: "“Dress for a summer wedding”" },
    points: [
      { icon: MessageSquareText, title: "Natural-language search", text: "Ask the way you would ask a stylist. No filters or exact terms needed." },
      { icon: Sparkles, title: "Occasion and season aware", text: "Results reflect the setting, from the office to a beach ceremony." },
      { icon: Star, title: "Backed by real reviews", text: "Customer feedback is summarised so you can judge fit and quality at a glance." },
    ],
    cta: (
      <Button asChild size="lg">
        <Link to="/search?q=dress%20for%20a%20summer%20wedding">
          Try a search <ArrowRight />
        </Link>
      </Button>
    ),
  },
  {
    id: "try-on",
    eyebrow: "Virtual try-on",
    title: "See it on you before you decide.",
    body: "Upload a single photo and preview any garment on yourself. Judge colour, cut and proportion with confidence, without a fitting room.",
    image: IMAGES.tryOn,
    imageAlt: "Woman in a burgundy coat holding shopping bags",
    badge: { icon: ScanLine, text: "Fitted to your photo" },
    points: [
      { icon: Upload, title: "One photo, any product", text: "Start the try-on directly from a product card in your results." },
      { icon: Shirt, title: "Tops, bottoms and dresses", text: "Garment-aware rendering keeps prints, fabric and drape true to the product." },
      { icon: ShieldCheck, title: "Buy with confidence", text: "A realistic preview helps you choose the right piece the first time." },
    ],
    cta: (
      <Button asChild size="lg">
        <Link to="/search">
          Browse and try on <ArrowRight />
        </Link>
      </Button>
    ),
  },
]

export function FeaturesSection() {
  return (
    <div className="bg-white">
      <div className="mx-auto max-w-6xl px-6 py-24 sm:py-28">
        <Reveal className="mx-auto max-w-2xl text-center">
          <p className="text-[11px] uppercase tracking-[0.3em] text-brand-600">Why {BRAND_NAME}</p>
          <h2 className="mt-4 text-balance font-display text-4xl leading-tight sm:text-5xl">Styling that starts with how you live.</h2>
          <p className="mt-5 text-neutral-600">
            Two capabilities work together: one finds the right outfit for the moment, the other shows how it looks on you.
          </p>
        </Reveal>

        <div className="mt-20 space-y-24 sm:space-y-32">
          {FEATURES.map((feature, i) => (
            <section
              key={feature.id}
              id={feature.id}
              className="grid scroll-mt-24 items-center gap-10 lg:grid-cols-2 lg:gap-16"
            >
              <Reveal className={cn(i % 2 === 1 && "lg:order-2")}>
                <div className="relative">
                  <div className="aspect-[4/5] overflow-hidden rounded-3xl bg-tile">
                    <img
                      src={feature.image}
                      alt={feature.imageAlt}
                      loading="lazy"
                      className="h-full w-full object-cover transition-transform duration-700 hover:scale-105"
                    />
                  </div>
                  <div className="absolute bottom-5 left-5 flex items-center gap-2 rounded-full bg-white/90 px-4 py-2 text-sm shadow-lg backdrop-blur">
                    <feature.badge.icon className="size-4 text-brand-600" />
                    {feature.badge.text}
                  </div>
                </div>
              </Reveal>

              <Reveal>
                <p className="text-[11px] uppercase tracking-[0.3em] text-brand-600">{feature.eyebrow}</p>
                <h3 className="mt-4 text-balance font-display text-3xl leading-tight sm:text-4xl">{feature.title}</h3>
                <p className="mt-5 text-neutral-600">{feature.body}</p>

                <ul className="mt-8 space-y-5">
                  {feature.points.map((point) => (
                    <li key={point.title} className="flex gap-4">
                      <span className="flex size-10 shrink-0 items-center justify-center rounded-xl bg-brand-50 text-brand-600">
                        <point.icon className="size-5" strokeWidth={1.75} />
                      </span>
                      <div>
                        <p className="font-medium">{point.title}</p>
                        <p className="mt-0.5 text-sm text-neutral-600">{point.text}</p>
                      </div>
                    </li>
                  ))}
                </ul>

                <div className="mt-10">{feature.cta}</div>
              </Reveal>
            </section>
          ))}
        </div>
      </div>
    </div>
  )
}
