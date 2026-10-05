import { Link, NavLink } from "react-router-dom"
import { Search } from "lucide-react"
import { cn } from "@/lib/utils"
import { BRAND_NAME } from "@/lib/brand"

const links = [
  { to: "/", label: "Home", end: true },
  { to: "/search", label: "Shop", end: false },
]

// Plain bar: transparent with white text over the home hero (`overlay`),
// white with a hairline border on every other page.
export function Navbar({ overlay = false }: { overlay?: boolean }) {
  return (
    <header
      className={cn(
        "z-40 w-full",
        overlay ? "absolute inset-x-0 top-0 text-white" : "sticky top-0 border-b border-neutral-200 bg-white/90 text-ink backdrop-blur"
      )}
    >
      <div className="mx-auto grid h-16 max-w-7xl grid-cols-[1fr_auto_1fr] items-center px-6 sm:px-10">
        <nav className="flex items-center gap-6">
          {links.map((link) => (
            <NavLink
              key={link.to}
              to={link.to}
              end={link.end}
              className={({ isActive }) =>
                cn(
                  "text-[13px] tracking-wide transition-opacity",
                  isActive ? "opacity-100" : "opacity-60 hover:opacity-100"
                )
              }
            >
              {link.label}
            </NavLink>
          ))}
        </nav>

        <Link to="/" className={cn("font-display text-2xl tracking-tight", overlay ? "text-white" : "text-brand-700")}>
          {BRAND_NAME.toLowerCase()}
        </Link>

        <div className="flex justify-end">
          <Link to="/search" aria-label="Search" className="opacity-70 transition-opacity hover:opacity-100">
            <Search className="size-[18px]" strokeWidth={1.5} />
          </Link>
        </div>
      </div>
    </header>
  )
}
