import { BRAND_NAME } from "@/lib/brand"

export function Footer() {
  return (
    <footer className="theme-fixed bg-brand-900 text-brand-100">
      <div className="mx-auto flex max-w-7xl flex-col gap-3 px-4 py-10 sm:flex-row sm:items-end sm:justify-between sm:px-8">
        <div>
          <p className="font-display text-3xl text-white">{BRAND_NAME.toLowerCase()}</p>
          <p className="mt-1 text-sm text-brand-200">Describe the outfit you want. We'll find it.</p>
        </div>
      </div>
    </footer>
  )
}
