import { useEffect, useState } from "react"
import { Moon, Sun } from "lucide-react"

type Theme = "light" | "dark"

const systemTheme = (): Theme => (matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light")
const stored = (): Theme | null => {
  try {
    const t = localStorage.getItem("theme")
    return t === "light" || t === "dark" ? t : null
  } catch {
    return null
  }
}

// Floating light/dark switch. Follows the browser setting until the visitor
// picks a theme, after which their choice is remembered.
export function ThemeToggle() {
  const [theme, setTheme] = useState<Theme>(() => stored() ?? systemTheme())
  const [chosen, setChosen] = useState(() => stored() !== null)

  useEffect(() => {
    document.documentElement.classList.toggle("dark", theme === "dark")
  }, [theme])

  useEffect(() => {
    if (chosen) return
    const mq = matchMedia("(prefers-color-scheme: dark)")
    const onChange = () => setTheme(systemTheme())
    mq.addEventListener("change", onChange)
    return () => mq.removeEventListener("change", onChange)
  }, [chosen])

  const toggle = () => {
    const next: Theme = theme === "dark" ? "light" : "dark"
    setTheme(next)
    setChosen(true)
    try {
      localStorage.setItem("theme", next)
    } catch {
      /* storage unavailable: keep the choice for this session only */
    }
  }

  return (
    <button
      onClick={toggle}
      aria-label={theme === "dark" ? "Switch to light mode" : "Switch to dark mode"}
      className="fixed bottom-5 left-5 z-50 flex size-11 items-center justify-center rounded-full border border-neutral-200 bg-white/90 text-ink shadow-lg backdrop-blur transition-transform hover:scale-105 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-500"
    >
      {theme === "dark" ? <Sun className="size-5" strokeWidth={1.5} /> : <Moon className="size-5" strokeWidth={1.5} />}
    </button>
  )
}
