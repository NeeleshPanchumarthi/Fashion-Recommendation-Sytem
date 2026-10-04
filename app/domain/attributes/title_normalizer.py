import html
import re
from typing import Dict

def normalize_title(title: str) -> Dict[str, str]:
    """Normalize a product title.

    Returns a dict with:
        - original: the raw title (unchanged)
        - normalized: the cleaned title
    """
    original = title
    # Unescape HTML entities
    cleaned = html.unescape(title)
    # Trim and collapse whitespace
    cleaned = cleaned.strip()
    cleaned = re.sub(r"\s+", " ", cleaned)
    # Remove punctuation at start/end (preserving internal punctuation and '&')
    cleaned = re.sub(r"^[^\w&]+|[^\w&]+$", "", cleaned)
    # Lowercase for normalization
    normalized = cleaned.lower()
    return {"original": original, "normalized": normalized}
