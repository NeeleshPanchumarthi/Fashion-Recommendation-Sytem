"""Review processing and aggregation.

This module processes raw reviews, extracts sentiment using the LLM,
and aggregates the sentiment at the product level (parent_asin) so it
can be joined with product metadata before embedding.
"""

import logging
import time
import pandas as pd
from typing import Optional
from .sentiment_extractor import extract_sentiment

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def process_reviews(df_reviews: pd.DataFrame, limit: Optional[int] = None) -> pd.DataFrame:
    """Process a dataframe of reviews to extract sentiment.
    
    Args:
        df_reviews: DataFrame containing at least 'parent_asin' and 'text'.
        limit: Optional limit for testing to process only N reviews.
        
    Returns:
        DataFrame with an added 'sentiment' column.
    """
    if limit is not None:
        df = df_reviews.head(limit).copy()
    else:
        df = df_reviews.copy()
        
    sentiments = []
    
    logger.info(f"Processing sentiment for {len(df)} reviews...")
    
    for idx, row in df.iterrows():
        text = str(row.get("text", ""))
        try:
            # Adding a tiny sleep to avoid hitting Groq API rate limits instantly
            time.sleep(0.3) 
            sentiment = extract_sentiment(text)
        except Exception as e:
            logger.error(f"Failed to extract sentiment for review {row.get('asin', idx)}: {e}")
            sentiment = "neutral"
            
        sentiments.append(sentiment)
        
        if len(sentiments) % 10 == 0:
            logger.info(f"Processed {len(sentiments)}/{len(df)} reviews")
            
    df["sentiment"] = sentiments
    return df

def aggregate_product_sentiment(df_processed_reviews: pd.DataFrame) -> pd.DataFrame:
    """Aggregate individual review sentiments to the product level.
    
    Args:
        df_processed_reviews: DataFrame output from `process_reviews`.
        
    Returns:
        DataFrame indexed by 'parent_asin' with an 'overall_sentiment' column.
    """
    if "sentiment" not in df_processed_reviews.columns:
        raise ValueError("The dataframe must contain a 'sentiment' column.")

    # Group by parent_asin and calculate the mode (most common sentiment)
    # This gives us a single overall sentiment string per product.
    agg_df = df_processed_reviews.groupby("parent_asin")["sentiment"].agg(
        lambda x: x.mode().iloc[0] if not x.mode().empty else "neutral"
    ).reset_index()
    
    agg_df.rename(columns={"sentiment": "overall_sentiment"}, inplace=True)
    return agg_df
