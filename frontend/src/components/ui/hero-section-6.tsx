import { useState, type FormEvent } from "react"
import { Link } from "react-router-dom"
import { ArrowRight, Check, Menu, Search, SendHorizonal, X } from "lucide-react"
import { Button } from "@/components/ui/button"
import { BRAND_NAME, HERO_IMAGE, SUGGESTED_SEARCHES } from "@/lib/brand"

const menuItems = [
  { name: "Features", href: "#features" },
  { name: "Shop", href: "/search" },
]

const highlights = ["Understands occasion, season and style", "Preview any outfit on yourself", "Gender-balanced, review-backed results"]

function NavItem({ href, children, className }: { href: string; children: React.ReactNode; className?: string }) {
  return href.startsWith("#") ? (
    <a href={href} className={className}>
      {children}
    </a>
  ) : (
    <Link to={href} className={className}>
      {children}
    </Link>
  )
}

// Hero with the shared photo backdrop: responsive nav with an animated menu
// toggle, a announcement pill, headline, search form and value points.
export function HeroSection({ onSearch }: { onSearch: (query: string) => void }) {
  const [menuState, setMenuState] = useState(false)
  const [value, setValue] = useState("")

  const submit = (e: FormEvent) => {
    e.preventDefault()
    if (value.trim()) onSearch(value.trim())
  }

  return (
    <section className="theme-fixed relative isolate flex min-h-[100svh] flex-col overflow-hidden bg-ink text-white">
      <img
        src={HERO_IMAGE.src}
        alt=""
        className="animate-hero-zoom absolute inset-0 -z-20 h-full w-full object-cover object-[65%_center]"
      />
      <div className="absolute inset-0 -z-10 bg-gradient-to-r from-ink/90 via-ink/65 to-ink/20" />
      <div className="absolute inset-x-0 bottom-0 -z-10 h-1/2 bg-gradient-to-t from-ink/80 to-transparent" />

      <header>
        <nav data-state={menuState ? "active" : undefined} className="group absolute inset-x-0 top-0 z-20 w-full border-b border-dashed border-white/20">
          <div className="mx-auto max-w-6xl px-6">
            <div className="flex flex-wrap items-center justify-between gap-6 py-3 lg:gap-0 lg:py-4">
              <div className="flex w-full justify-between lg:w-auto">
                <Link to="/" aria-label="home" className="flex items-center font-display text-2xl tracking-tight">
                  {BRAND_NAME.toLowerCase()}
                </Link>

                <button
                  onClick={() => setMenuState(!menuState)}
                  aria-label={menuState ? "Close Menu" : "Open Menu"}
                  className="relative z-20 -m-2.5 -mr-4 block cursor-pointer p-2.5 lg:hidden"
                >
                  <Menu className="m-auto size-6 duration-200 group-data-[state=active]:rotate-180 group-data-[state=active]:scale-0 group-data-[state=active]:opacity-0" />
                  <X className="absolute inset-0 m-auto size-6 -rotate-180 scale-0 opacity-0 duration-200 group-data-[state=active]:rotate-0 group-data-[state=active]:scale-100 group-data-[state=active]:opacity-100" />
                </button>
              </div>

              <div className="mb-6 hidden w-full flex-wrap items-center justify-end space-y-8 rounded-3xl border border-white/15 bg-ink/90 p-6 shadow-2xl backdrop-blur group-data-[state=active]:block md:flex-nowrap lg:m-0 lg:flex lg:w-fit lg:gap-6 lg:space-y-0 lg:border-transparent lg:bg-transparent lg:p-0 lg:shadow-none lg:backdrop-blur-none lg:group-data-[state=active]:flex">
                <ul className="space-y-6 text-base lg:flex lg:gap-8 lg:space-y-0 lg:pr-4 lg:text-sm">
                  {menuItems.map((item) => (
                    <li key={item.name}>
                      <NavItem href={item.href} className="block text-white/70 duration-150 hover:text-white">
                        {item.name}
                      </NavItem>
                    </li>
                  ))}
                </ul>

              </div>
            </div>
          </div>
        </nav>
      </header>

      <main className="flex flex-1 items-center">
        <div className="mx-auto w-full max-w-6xl px-6 pb-16 pt-32 lg:pt-24">
          <div className="relative z-10 mx-auto max-w-xl text-center lg:mx-0 lg:w-3/5 lg:max-w-2xl lg:text-left">
            <a
              href="#try-on"
              className="animate-rise mx-auto flex w-fit items-center gap-2 rounded-lg border border-white/25 p-1 pr-3 backdrop-blur-sm lg:ml-0"
              style={{ animationDelay: "100ms" }}
            >
              <span className="rounded-[0.5rem] bg-brand-600 px-2 py-1 text-xs">New</span>
              <span className="text-sm">Virtual try-on is live</span>
              <span className="block h-4 w-px bg-white/30" />
              <ArrowRight className="size-4" />
            </a>

            <h1
              className="animate-rise mt-10 text-balance font-display text-4xl leading-[1.05] md:text-5xl xl:text-6xl"
              style={{ animationDelay: "250ms" }}
            >
              Find the outfit for every occasion.
            </h1>
            <p className="animate-rise mt-6 text-white/70" style={{ animationDelay: "350ms" }}>
              Describe the moment in your own words. {BRAND_NAME} finds what suits it, then lets you see it on you.
            </p>

            <form
              onSubmit={submit}
              className="animate-rise mx-auto my-10 max-w-md lg:mx-0"
              style={{ animationDelay: "450ms" }}
            >
              <div className="relative grid grid-cols-[1fr_auto] items-center rounded-2xl border border-white/25 bg-ink/50 pr-1 shadow shadow-black/20 backdrop-blur has-[input:focus]:ring-2 has-[input:focus]:ring-white/30">
                <Search className="pointer-events-none absolute inset-y-0 left-5 my-auto size-5 text-white/50" />
                <input
                  value={value}
                  onChange={(e) => setValue(e.target.value)}
                  placeholder="Describe the outfit you want"
                  aria-label="Describe the outfit you want"
                  className="h-14 w-full bg-transparent pl-12 text-white placeholder:text-white/45 focus:outline-none"
                  type="text"
                />
                <Button type="submit" aria-label="Search" className="rounded-xl">
                  <span className="hidden md:block">Search</span>
                  <SendHorizonal className="relative mx-auto size-5 md:hidden" strokeWidth={2} />
                </Button>
              </div>
              <p className="mt-3 flex flex-wrap justify-center gap-x-1 gap-y-1 text-[13px] text-white/45 lg:justify-start">
                <span className="mr-1">Try</span>
                {SUGGESTED_SEARCHES.slice(0, 3).map((query, i, arr) => (
                  <span key={query} className="flex items-center gap-x-1">
                    <button type="button" onClick={() => onSearch(query)} className="text-white/70 transition-colors hover:text-white">
                      {query}
                    </button>
                    {i < arr.length - 1 && <span aria-hidden>·</span>}
                  </span>
                ))}
              </p>
            </form>

            <ul className="animate-rise inline-block space-y-2 text-left text-sm text-white/80" style={{ animationDelay: "550ms" }}>
              {highlights.map((item) => (
                <li key={item} className="flex items-center gap-2">
                  <Check className="size-4 text-brand-200" />
                  {item}
                </li>
              ))}
            </ul>
          </div>
        </div>
      </main>
    </section>
  )
}
