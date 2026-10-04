import { useState, type FormEvent } from "react"
import { Search, ImagePlus } from "lucide-react"
import { Input } from "@/components/ui/input"
import { Button } from "@/components/ui/button"
import { Link } from "react-router-dom"

interface SearchBarProps {
  defaultValue?: string
  onSearch: (query: string) => void
  autoFocus?: boolean
}

export function SearchBar({ defaultValue = "", onSearch, autoFocus }: SearchBarProps) {
  const [value, setValue] = useState(defaultValue)

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault()
    onSearch(value)
  }

  return (
    <form onSubmit={handleSubmit} className="flex w-full items-center gap-2">
      <div className="relative flex-1">
        <Search className="pointer-events-none absolute left-3.5 top-1/2 size-5 -translate-y-1/2 text-slate-400" />
        <Input
          value={value}
          onChange={(e) => setValue(e.target.value)}
          placeholder="Try: red floral dress for a summer wedding, under $80..."
          autoFocus={autoFocus}
          className="h-14 pl-11 pr-4 text-base"
        />
      </div>
      <Button type="submit" size="lg" className="h-14">
        Search
      </Button>
      <Button asChild type="button" variant="outline" size="icon" className="h-14 w-14 shrink-0">
        <Link to="/image-search" aria-label="Search by image" title="Search by image">
          <ImagePlus className="size-5" />
        </Link>
      </Button>
    </form>
  )
}
