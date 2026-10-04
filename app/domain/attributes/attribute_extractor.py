"""Aggregated attribute extractor module.

Combines individual attribute extractors (gender, category, color, style, size)
into a unified interface for enriching product titles.
"""

from __future__ import annotations

from typing import Any, Dict

from .category_extractor import extract_category
from .color_extractor import extract_color
from .gender_extractor import extract_gender
from .size_extractor import extract_size
from .style_extractor import extract_style


def extract_all_attributes(title: str) -> Dict[str, Any]:
    """Extract all supported attributes from a raw product title.

    Returns
    -------
    Dict[str, Any]
        A dictionary containing keys: gender, category, color, style, size.
    """
    return {
        "gender": extract_gender(title),
        "category": extract_category(title),
        "color": extract_color(title),
        "style": extract_style(title),
        "size": extract_size(title),
    }
