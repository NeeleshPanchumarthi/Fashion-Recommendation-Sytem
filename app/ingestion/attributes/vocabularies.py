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
