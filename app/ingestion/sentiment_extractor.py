"""Local sentiment extractor using nlptown/bert-base-multilingual-uncased-sentiment.

The model outputs a star rating (1–5 stars). We map this to three labels:
    1–2 stars  →  negative
    3 stars    →  neutral
    4–5 stars  →  positive

The transformers pipeline is loaded once per process and cached as a
module-level singleton so that repeated calls don't reload the weights.

Device selection is automatic: if a CUDA GPU is visible (e.g. on a Colab
GPU runtime), the pipeline runs on it; otherwise it falls back to CPU
exactly as before. This is detected once at load time, not per call.
"""

from __future__ import annotations

import logging
from typing import List

logger = logging.getLogger(__name__)


def _detect_device() -> int:
    """Return the transformers pipeline device index: 0 for the first CUDA
    GPU if one is available, -1 for CPU. Importing torch here (rather than
    at module level) keeps this file loadable even in environments where
    torch isn't installed yet / is being installed."""
    try:
        import torch
        if torch.cuda.is_available():
            name = torch.cuda.get_device_name(0)
            logger.info("CUDA GPU detected: %s -- sentiment model will run on GPU", name)
            return 0
    except Exception as exc:
        logger.info("No usable CUDA GPU (%s) -- sentiment model will run on CPU", exc)
    return -1

# ---------------------------------------------------------------------------
# Model config
# ---------------------------------------------------------------------------

SENTIMENT_MODEL = "nlptown/bert-base-multilingual-uncased-sentiment"

# Pinecone / transformers-pipeline batch size (tune to GPU/CPU memory)
_BATCH_SIZE = 32

# Module-level singleton – populated on first call to _get_pipeline()
_pipeline = None


def _get_pipeline():
    """Lazily load and cache the transformers sentiment pipeline."""
    global _pipeline
    if _pipeline is None:
        try:
            from transformers import pipeline as hf_pipeline
            logger.info("Loading local sentiment model: %s …", SENTIMENT_MODEL)
            _pipeline = hf_pipeline(
                "text-classification",
                model=SENTIMENT_MODEL,
                tokenizer=SENTIMENT_MODEL,
                truncation=True,
                max_length=512,
                batch_size=_BATCH_SIZE,
                top_k=1,          # return only the top label per input
                device=_detect_device(),
            )
            logger.info("Sentiment model loaded successfully.")
        except Exception as exc:
            logger.error("Failed to load sentiment model: %s", exc)
            raise
    return _pipeline


# ---------------------------------------------------------------------------
# Star-label → sentiment mapping
# ---------------------------------------------------------------------------

def _star_label_to_sentiment(label: str) -> str:
    """Map model output label (e.g. '4 stars') to positive/neutral/negative."""
    label = label.lower().strip()
    # The model outputs labels like "1 star", "2 stars", "3 stars", etc.
    for star_count in ("1", "2", "3", "4", "5"):
        if star_count in label:
            n = int(star_count)
            if n <= 2:
                return "negative"
            elif n == 3:
                return "neutral"
            else:
                return "positive"
    # Fallback if label format changes
    return "neutral"


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def classify_batch(texts: List[str]) -> List[str]:
    """Classify a list of review texts and return sentiment labels.

    Parameters
    ----------
    texts : list of raw review strings

    Returns
    -------
    list of "positive" | "neutral" | "negative" (same order as input)
    """
    pipe = _get_pipeline()
    sentiments: List[str] = []

    # Process in batches; transformers pipeline handles its own batching
    # but we chunk to surface progress logs.
    total = len(texts)
    for start in range(0, total, _BATCH_SIZE * 4):
        chunk = texts[start: start + _BATCH_SIZE * 4]
        try:
            # Each result is a list-of-list when top_k=1
            results = pipe(chunk)
            for res in results:
                # res is [{"label": "4 stars", "score": 0.9}]
                label = res[0]["label"] if isinstance(res, list) else res["label"]
                sentiments.append(_star_label_to_sentiment(label))
        except Exception as exc:
            logger.error("Batch sentiment error (chunk start=%d): %s", start, exc)
            # Fall back to neutral for the whole chunk
            sentiments.extend(["neutral"] * len(chunk))

        logger.info("Sentiment: %d / %d reviews classified", len(sentiments), total)

    return sentiments


def extract_sentiment(text: str) -> str:
    """Classify a single review text.  Convenience wrapper around classify_batch."""
    if not text or not str(text).strip():
        return "neutral"
    results = classify_batch([str(text).strip()])
    return results[0] if results else "neutral"