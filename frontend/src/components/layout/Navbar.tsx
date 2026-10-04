import { Link, NavLink } from "react-router-dom"
import { Sparkles } from "lucide-react"
import { cn } from "@/lib/utils"

const links = [
  { to: "/", label: "Home" },
  { to: "/search", label: "Search" },
  { to: "/ai", label: "AI Features" },
]

export function Navbar() {
  return (
    <header className="sticky top-0 z-40 border-b border-slate-200 bg-white/80 backdrop-blur-md">
      <div className="mx-auto flex max-w-7xl items-center justify-between px-4 py-3 sm:px-6">
        <Link to="/" className="flex items-center gap-2 font-semibold text-slate-900">
          <span className="flex size-8 items-center justify-center rounded-lg bg-gradient-to-br from-violet-600 to-pink-500 text-white">
            <Sparkles className="size-4" />
          </span>
          <span className="text-lg tracking-tight">Vogue AI</span>
        </Link>
        <nav className="flex items-center gap-1">
          {links.map((link) => (
            <NavLink
              key={link.to}
              to={link.to}
              className={({ isActive }) =>
                cn(
                  "rounded-full px-3.5 py-2 text-sm font-medium transition-colors",
                  isActive ? "bg-violet-100 text-violet-700" : "text-slate-600 hover:bg-slate-100"
                )
              }
            >
              {link.label}
            </NavLink>
          ))}
        </nav>
      </div>
    </header>
  )
}
