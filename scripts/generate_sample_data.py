"""Write a tiny sample dataset (3 products, 4 reviews) in the real schema.

Useful for trying the ingestion worker without the full dataset:

    python scripts/generate_sample_data.py
    python -m workers.ingestion_worker --metadata-path data/sample/metadata.parquet \\
        --reviews-path data/sample/reviews.parquet --checkpoint-path data/sample/state.json

Writes to data/sample/ by default and never overwrites existing files
unless --force is given (so it can't clobber the real dataset).
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _images(name: str, *variants: str) -> list[dict]:
    return [
        {"variant": v, "thumb": f"https://example.com/{name}-{v}-thumb.jpg",
         "large": f"https://example.com/{name}-{v}.jpg", "hi_res": f"https://example.com/{name}-{v}-hires.jpg"}
        for v in variants
    ]


def build_sample() -> tuple[pd.DataFrame, pd.DataFrame]:
    metadata = pd.DataFrame([
        {"parent_asin": "B01D234567", "title": "Men's Classic Red T-Shirt Cotton Large", "average_rating": 4.5,
         "rating_number": 120, "images": _images("red-tshirt", "MAIN", "PT01"),
         "description": "A very comfortable classic red cotton t-shirt for men."},
        {"parent_asin": "B02E345678", "title": "Women's Elegant Black Dress Size M", "average_rating": 4.8,
         "rating_number": 340, "images": _images("black-dress", "MAIN", "PT01", "FRNT", "BACK"),
         "description": "Elegant formal black dress for evening parties."},
        {"parent_asin": "B03F456789", "title": "Unisex Sporty Blue Sneakers", "average_rating": 3.9,
         "rating_number": 85, "images": _images("blue-sneakers", "MAIN"),
         "description": "Comfortable sporty sneakers suitable for running and casual wear."},
    ])

    now_ms = int(time.time() * 1000)  # the real dataset stores epoch milliseconds
    reviews = pd.DataFrame([
        {"asin": "B01D234567_1", "parent_asin": "B01D234567", "rating": 5, "title": "Great shirt!",
         "text": "The color is vibrant and it fits perfectly. Very comfortable.", "user_id": "U1001",
         "timestamp": now_ms, "verified_purchase": True, "helpful_vote": 3},
        {"asin": "B01D234567_2", "parent_asin": "B01D234567", "rating": 2, "title": "Too small",
         "text": "It shrank after the first wash. Would not recommend.", "user_id": "U1002",
         "timestamp": now_ms, "verified_purchase": True, "helpful_vote": 1},
        {"asin": "B02E345678_1", "parent_asin": "B02E345678", "rating": 5, "title": "Beautiful dress",
         "text": "I wore this to a gala and received so many compliments. Stunning!", "user_id": "U1003",
         "timestamp": now_ms, "verified_purchase": True, "helpful_vote": 0},
        {"asin": "B03F456789_1", "parent_asin": "B03F456789", "rating": 4, "title": "Good for the price",
         "text": "They are decent sneakers. Not the best quality, but good for daily use.", "user_id": "U1004",
         "timestamp": now_ms, "verified_purchase": False, "helpful_vote": 0},
    ])
    return metadata, reviews


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--output-dir", type=Path, default=PROJECT_ROOT / "data" / "sample")
    parser.add_argument("--force", action="store_true", help="Overwrite existing files.")
    args = parser.parse_args()

    meta_path = args.output_dir / "metadata.parquet"
    reviews_path = args.output_dir / "reviews.parquet"
    existing = [p for p in (meta_path, reviews_path) if p.exists()]
    if existing and not args.force:
        print(f"Refusing to overwrite {', '.join(map(str, existing))} (pass --force).", file=sys.stderr)
        return 1

    metadata, reviews = build_sample()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    metadata.to_parquet(meta_path, index=False)
    reviews.to_parquet(reviews_path, index=False)
    print(f"Wrote {meta_path} and {reviews_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
