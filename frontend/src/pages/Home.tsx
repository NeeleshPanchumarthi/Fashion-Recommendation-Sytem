import { useNavigate } from "react-router-dom"
import { Navbar } from "@/components/layout/Navbar"
import { HeroSearch } from "@/components/search/HeroSearch"
import { BRAND_NAME, HERO_IMAGE } from "@/lib/brand"

const HEADLINE = ["Find the Outfit", "for Every", "Occasion"]

// Letters of the brand watermark that get the red accent (like the
// reference design's accented middle letters).
const ACCENT_LETTERS = new Set([2, 3])

export default function Home() {
  const navigate = useNavigate()
  const goSearch = (query: string) => navigate(`/search?q=${encodeURIComponent(query)}`)
  const letters = BRAND_NAME.toLowerCase().split("")

  return (
    <section className="relative isolate flex min-h-[640px] h-[100svh] flex-col overflow-hidden bg-ink text-white">
      {/* Background figure, slowly settling in */}
      <img
        src={HERO_IMAGE.src}
        alt=""
        className="animate-hero-zoom absolute inset-0 -z-20 h-full w-full object-cover object-[65%_center]"
      />
      {/* Darken the left (headline) and bottom (watermark + search) */}
      <div className="absolute inset-0 -z-10 bg-gradient-to-r from-ink/95 via-ink/55 to-ink/10" />
      <div className="absolute inset-x-0 bottom-0 -z-10 h-2/3 bg-gradient-to-t from-ink via-ink/60 to-transparent" />
      {/* Soft red glow, echoing the reference's neon light */}
      <div className="animate-glow absolute -right-24 top-1/4 -z-10 size-[28rem] rounded-full bg-brand-600/40 blur-[120px]" />

      <Navbar overlay />

      <div className="mx-auto flex w-full max-w-7xl flex-1 flex-col px-6 sm:px-10">
        <h1 className="mt-[22vh] font-display text-5xl leading-[1.05] sm:text-6xl lg:text-7xl">
          {HEADLINE.map((line, i) => (
            <span key={line} className="animate-rise block" style={{ animationDelay: `${200 + i * 140}ms` }}>
              {line}
            </span>
          ))}
        </h1>
        <p
          className="animate-rise mt-5 max-w-md text-[15px] leading-relaxed text-white/70"
          style={{ animationDelay: "650ms" }}
        >
          Describe what you have in mind — the occasion, colour or fit — and we'll match it with real
          products and what customers say about them.
        </p>

        <div className="mt-auto flex flex-col gap-8 pb-10 lg:flex-row lg:items-end lg:justify-between">
          {/* Brand watermark */}
          <p
            aria-hidden
            className="select-none pb-[0.12em] pr-[0.1em] font-script text-[clamp(4.5rem,15vw,13rem)] font-medium italic leading-[0.85] tracking-tight"
          >
            {letters.map((letter, i) => (
              <span
                key={i}
                className={`animate-blur-in inline-block ${ACCENT_LETTERS.has(i) ? "text-brand-600" : "text-white/90"}`}
                style={{ animationDelay: `${300 + i * 90}ms`, ["--final-blur" as string]: "1.5px" }}
              >
                {letter}
              </span>
            ))}
          </p>

          <HeroSearch onSearch={goSearch} />
        </div>
      </div>
    </section>
  )
}
