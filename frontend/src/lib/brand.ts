// Brand + home-page content in one place, so renaming or swapping the hero
// photo is a one-file change.

export const BRAND_NAME = "Vestira"

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
  "black leather jacket for men",
  "dress for a summer wedding",
  "white sneakers for women",
  "party shirt for college",
]

// Result tabs (All Products / Men / Women / Kids / Accessories). Visual
// only for now -- filtering by tab is a planned feature.
export const CATEGORY_TABS = ["All Products", "Men", "Women", "Kids", "Accessories"] as const
export type CategoryTab = (typeof CATEGORY_TABS)[number]
