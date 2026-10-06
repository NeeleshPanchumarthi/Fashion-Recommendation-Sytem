"""Controlled vocabularies for attribute extraction modules.

The project keeps a small, explicit list of allowed values for each attribute.
These lists are used by the rule‑based extractors to map free‑form tokens to a
canonical tag. Keeping them in a single module makes it easy to maintain and
extend without touching the extractor logic.
"""

# Gender categories used by ``gender_extractor``
GENDERS = {
    "men",
    "women",
    "kids",
    "unisex",
}

# Product categories used by ``category_extractor``
CATEGORIES = {
    "shirt",
    "t-shirt",
    "dress",
    "pants",
    "trousers",
    "jeans",
    "jacket",
    "hoodie",
    "sweater",
    "shoes",
    "sneakers",
    "hat",
    "cap",
    "shorts",
    "skirt",
    "blouse",
    "coat",
}

# Colors used by ``color_extractor``
COLORS = {
    "black",
    "white",
    "red",
    "blue",
    "green",
    "yellow",
    "pink",
    "purple",
    "grey",
    "brown",
    "navy",
    "beige",
    "gold",
    "silver",
    "orange",
}

# Styles used by ``style_extractor``
STYLES = {
    "casual",
    "formal",
    "sporty",
    "vintage",
    "streetwear",
    "boho",
    "elegant",
    "chic",
    "classic",
    "retro",
    "party",
    "business",
}

# Sizes used by ``size_extractor``
SIZES = {
    "xs",
    "s",
    "m",
    "l",
    "xl",
    "xxl",
    "3xl",
}

# Broader fashion lexicon used ONLY by the search query guard (never for
# attribute tagging). It is a deterministic fallback for when the LLM is
# unavailable -- on its own it can't tell "wedding dress" from "wedding
# venues", which is why the LLM makes the real decision.
FASHION_TERMS = (
    CATEGORIES
    | COLORS
    | STYLES
    | SIZES
    | {
        # clothing
        "top", "tops", "tee", "tank", "polo", "kurta", "saree", "sari", "lehenga", "gown", "suit", "blazer",
        "cardigan", "vest", "leggings", "joggers", "sweatpants", "chinos", "denim", "jumpsuit", "romper",
        "overalls", "pajamas", "pyjamas", "lingerie", "bra", "underwear", "socks", "swimsuit", "bikini",
        "tuxedo", "uniform", "scarf", "shawl", "poncho", "parka", "raincoat", "windbreaker", "tracksuit",
        "activewear", "sportswear", "loungewear", "clothes", "clothing", "apparel", "outfit", "outfits",
        "wear", "wearing", "attire", "garment", "garments", "fashion", "wardrobe", "layer", "layers",
        # footwear
        "boots", "boot", "sandals", "sandal", "heels", "heel", "loafers", "flats", "slippers", "slipper",
        "footwear", "trainers", "oxfords", "pumps", "wedges", "clogs", "shoe", "sneaker",
        # accessories
        "bag", "bags", "handbag", "purse", "backpack", "wallet", "belt", "watch", "sunglasses", "glasses",
        "jewelry", "jewellery", "necklace", "earrings", "bracelet", "ring", "tie", "bowtie", "gloves",
        "beanie", "accessories", "accessory", "headband", "umbrella",
        # sizing / fit / material / look
        "size", "sizes", "fit", "fitted", "oversized", "slim", "loose", "petite", "plus", "cotton", "linen",
        "wool", "silk", "leather", "floral", "striped", "plaid", "printed", "lightweight",
        "style", "styles", "stylish", "trendy", "look", "looks",
        # occasions people dress for
        "wedding", "party", "prom", "interview", "office", "work", "workout", "gym", "beach", "date",
        "festival", "cocktail", "graduation", "travel", "winter", "summer", "spring", "autumn", "fall",
        # who it's for
        "men", "mens", "women", "womens", "kids", "boys", "girls", "unisex", "male", "female", "man", "woman",
    }
)
