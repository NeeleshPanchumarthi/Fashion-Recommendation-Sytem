import { Sparkles } from "lucide-react"
import { Badge } from "@/components/ui/badge"

export function ComingSoonBadge() {
  return (
    <Badge variant="warning" className="gap-1">
      <Sparkles className="size-3" />
      Coming Soon
    </Badge>
  )
}
