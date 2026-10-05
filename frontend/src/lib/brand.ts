// Brand + home-page content in one place, so renaming or swapping the hero
// photo is a one-file change.

export const BRAND_NAME = "StyleIQ"

// Free to use under the Unsplash License (photo by Maksym Tymchyk). Loaded
// from Unsplash's CDN; replace with a local file in /public to self-host.
export const HERO_IMAGE = {
  src: "https://images.unsplash.com/photo-1614252368727-99517bc90d7b?auto=format&fit=crop&w=2000&q=80",
  credit: "Maksym Tymchyk",
  creditUrl: "https://unsplash.com/photos/man-in-brown-leather-jacket-wearing-black-sunglasses-bE6OvxczIc8",
}

// Quick searches shown in the hero, in place of the reference design's
// category list. Each one runs a real search.
export const SUGGESTED_SEARCHES = [
  "smart casual outfit for the office",
  "dress for a summer wedding",
  "black leather jacket for men",
  "white sneakers for women",
]

// Result tabs (All Products / Men / Women / Kids / Accessories). The slug is
// what goes in the URL (?tab=men); the tab filters the results client-side.
export const CATEGORY_TABS = [
  { slug: "all", label: "All Products" },
  { slug: "men", label: "Men" },
  { slug: "women", label: "Women" },
  { slug: "kids", label: "Kids" },
  { slug: "footwear", label: "Footwear" },
  { slug: "accessories", label: "Accessories" },
] as const
export type CategoryTab = (typeof CATEGORY_TABS)[number]["slug"]

// Unisex items show under both Men and Women; footwear and accessories get
// their own tab and also stay under their gender tab and All Products.
export function inTab(
  r: { gender?: string | null; is_accessory?: boolean; is_footwear?: boolean },
  tab: CategoryTab
): boolean {
  switch (tab) {
    case "all":
      return true
    case "footwear":
      return !!r.is_footwear
    case "accessories":
      return !!r.is_accessory
    case "kids":
      return r.gender === "kids"
    default:
      return r.gender === tab || r.gender === "unisex"
  }
}

export function parseTab(value: string | null): CategoryTab {
  return CATEGORY_TABS.find((t) => t.slug === value)?.slug ?? "all"
}
