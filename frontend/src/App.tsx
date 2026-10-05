import { Outlet, Route, Routes } from "react-router-dom"
import { Navbar } from "@/components/layout/Navbar"
import { Footer } from "@/components/layout/Footer"
import { ThemeToggle } from "@/components/ui/theme-toggle"
import Home from "@/pages/Home"
import SearchResults from "@/pages/SearchResults"
import ProductDetails from "@/pages/ProductDetails"
import NotFound from "@/pages/NotFound"

// Standard pages: navbar + content + footer. The home page is a full-screen
// hero with its own overlaid navbar, so it sits outside this layout.
function PageLayout() {
  return (
    <div className="flex min-h-screen flex-col">
      <Navbar />
      <main className="flex-1">
        <Outlet />
      </main>
      <Footer />
    </div>
  )
}

export default function App() {
  return (
    <>
      <ThemeToggle />
      <Routes>
      <Route path="/" element={<Home />} />
      <Route element={<PageLayout />}>
        <Route path="/search" element={<SearchResults />} />
        <Route path="/product/:id" element={<ProductDetails />} />
        <Route path="*" element={<NotFound />} />
      </Route>
    </Routes>
    </>
  )
}
