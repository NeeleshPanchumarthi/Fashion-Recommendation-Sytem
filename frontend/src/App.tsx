import { Routes, Route } from "react-router-dom"
import { Navbar } from "@/components/layout/Navbar"
import { Footer } from "@/components/layout/Footer"
import Home from "@/pages/Home"
import SearchResults from "@/pages/SearchResults"
import ProductDetails from "@/pages/ProductDetails"
import AIFeatures from "@/pages/AIFeatures"
import ImageSearch from "@/pages/ImageSearch"
import TryOn from "@/pages/TryOn"
import NotFound from "@/pages/NotFound"

export default function App() {
  return (
    <div className="flex min-h-screen flex-col">
      <Navbar />
      <main className="flex-1">
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/search" element={<SearchResults />} />
          <Route path="/product/:id" element={<ProductDetails />} />
          <Route path="/ai" element={<AIFeatures />} />
          <Route path="/image-search" element={<ImageSearch />} />
          <Route path="/try-on" element={<TryOn />} />
          <Route path="*" element={<NotFound />} />
        </Routes>
      </main>
      <Footer />
    </div>
  )
}
