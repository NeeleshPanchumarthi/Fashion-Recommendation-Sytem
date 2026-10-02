import os
import pandas as pd
from datetime import datetime

# Create data directory if it doesn't exist
os.makedirs("data", exist_ok=True)

# Generate dummy metadata
metadata = [
    {
        "parent_asin": "B01D234567",
        "title": "Men's Classic Red T-Shirt Cotton Large",
        "average_rating": 4.5,
        "rating_number": 120,
        "image_url": "http://example.com/red-tshirt.jpg",
        "description": "A very comfortable classic red cotton t-shirt for men."
    },
    {
        "parent_asin": "B02E345678",
        "title": "Women's Elegant Black Dress Size M",
        "average_rating": 4.8,
        "rating_number": 340,
        "image_url": "http://example.com/black-dress.jpg",
        "description": "Elegant formal black dress for evening parties."
    },
    {
        "parent_asin": "B03F456789",
        "title": "Unisex Sporty Blue Sneakers",
        "average_rating": 3.9,
        "rating_number": 85,
        "image_url": "http://example.com/blue-sneakers.jpg",
        "description": "Comfortable sporty sneakers suitable for running and casual wear."
    }
]

df_meta = pd.DataFrame(metadata)
df_meta.to_parquet("data/metadata.parquet", index=False)

# Generate dummy reviews
reviews = [
    {
        "asin": "B01D234567_1",
        "parent_asin": "B01D234567",
        "rating": 5,
        "title": "Great shirt!",
        "text": "The color is vibrant and it fits perfectly. Very comfortable.",
        "user_id": "U1001",
        "timestamp": int(datetime.now().timestamp()),
        "verified_purchase": True
    },
    {
        "asin": "B01D234567_2",
        "parent_asin": "B01D234567",
        "rating": 2,
        "title": "Too small",
        "text": "It shrank after the first wash. Would not recommend.",
        "user_id": "U1002",
        "timestamp": int(datetime.now().timestamp()),
        "verified_purchase": True
    },
    {
        "asin": "B02E345678_1",
        "parent_asin": "B02E345678",
        "rating": 5,
        "title": "Beautiful dress",
        "text": "I wore this to a gala and received so many compliments. Stunning!",
        "user_id": "U1003",
        "timestamp": int(datetime.now().timestamp()),
        "verified_purchase": True
    },
    {
        "asin": "B03F456789_1",
        "parent_asin": "B03F456789",
        "rating": 4,
        "title": "Good for the price",
        "text": "They are decent sneakers. Not the best quality, but good for daily use.",
        "user_id": "U1004",
        "timestamp": int(datetime.now().timestamp()),
        "verified_purchase": False
    }
]

df_reviews = pd.DataFrame(reviews)
df_reviews.to_parquet("data/reviews.parquet", index=False)

print("Successfully generated dummy data/metadata.parquet and data/reviews.parquet!")
