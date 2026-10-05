import { useNavigate } from "react-router-dom"
import { HeroSection } from "@/components/ui/hero-section-6"
import { FeaturesSection } from "@/components/ui/features-section"
import { Footer } from "@/components/layout/Footer"

export default function Home() {
  const navigate = useNavigate()
  const goSearch = (query: string) => navigate(`/search?q=${encodeURIComponent(query)}`)

  return (
    <>
      <HeroSection onSearch={goSearch} />
      <FeaturesSection />
      <Footer />
    </>
  )
}
