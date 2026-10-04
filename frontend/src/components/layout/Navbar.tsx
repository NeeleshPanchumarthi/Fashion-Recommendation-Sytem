import { Link, NavLink } from "react-router-dom"
import { Search } from "lucide-react"
import { cn } from "@/lib/utils"
import { BRAND_NAME } from "@/lib/brand"

const links = [
  { to: "/", label: "Home", end: true },
  { to: "/search", label: "Shop", end: false },
]

// Floating white pill, as in the reference design. `overlay` positions it
// over the home hero; otherwise it sticks to the top of normal pages.
export function Navbar({ overlay = false }: { overlay?: boolean }) {
  return (
    <header
      className={cn(
        "z-40 w-full px-4 sm:px-8",
        overlay ? "absolute inset-x-0 top-0 pt-5 animate-rise" : "sticky top-0 bg-white/80 pt-4 pb-3 backdrop-blur-md"
      )}
    >
      <div
        className={cn(
          "mx-auto grid max-w-7xl grid-cols-[1fr_auto_1fr] items-center rounded-full bg-white px-5 py-3 sm:px-7",
          overlay ? "shadow-lg shadow-black/20" : "border border-slate-200"
        )}
      >
        <nav className="flex items-center gap-1 sm:gap-4">
          {links.map((link) => (
            <NavLink
              key={link.to}
              to={link.to}
              end={link.end}
              className={({ isActive }) =>
                cn(
                  "text-sm transition-colors",
                  isActive ? "font-medium text-ink" : "text-neutral-500 hover:text-ink"
                )
              }
            >
              {link.label}
            </NavLink>
          ))}
        </nav>

        <Link to="/" className="font-display text-2xl tracking-tight text-brand-700 sm:text-[1.7rem]">
          {BRAND_NAME.toLowerCase()}
        </Link>

        <div className="flex justify-end">
          <Link
            to="/search"
            aria-label="Search"
            className="rounded-full p-2 text-ink transition-colors hover:bg-slate-100"
          >
            <Search className="size-5" strokeWidth={1.6} />
          </Link>
        </div>
      </div>
    </header>
  )
}
