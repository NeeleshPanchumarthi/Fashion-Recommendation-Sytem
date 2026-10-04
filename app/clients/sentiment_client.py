"""Local review-sentiment model (nlptown/bert-base-multilingual-uncased-sentiment).

The model outputs a star rating (1–5 stars). We map this to three labels:
    1–2 stars  →  negative
    3 stars    →  neutral
    4–5 stars  →  positive

The transformers pipeline is loaded once per process, on first use. Device
selection is automatic: the first CUDA GPU if one is visible (e.g. a Colab
GPU runtime), otherwise CPU. Used only by the ingestion worker.
"""

from __future__ import annotations

import logging
import threading

logger = logging.getLogger(__name__)


def _detect_device() -> int:
    """Transformers pipeline device index: 0 for the first CUDA GPU, -1 for
    CPU. torch is imported here so this module loads even without it."""
    try:
        import torch

        if torch.cuda.is_available():
            logger.info("CUDA GPU detected: %s -- sentiment model will run on GPU", torch.cuda.get_device_name(0))
            return 0
    except Exception as exc:  # noqa: BLE001 -- any failure means CPU
        logger.info("No usable CUDA GPU (%s) -- sentiment model will run on CPU", exc)
    return -1


def star_label_to_sentiment(label: str) -> str:
    """Map model output label (e.g. '4 stars') to positive/neutral/negative."""
    label = label.lower().strip()
    for star_count in ("1", "2", "3", "4", "5"):
        if star_count in label:
            n = int(star_count)
            if n <= 2:
                return "negative"
            if n == 3:
                return "neutral"
            return "positive"
    return "neutral"  # label format changed


class SentimentClient:
    def __init__(self, model_name: str, batch_size: int = 32) -> None:
        self.model_name = model_name
        self.batch_size = batch_size
        self._pipeline = None
        self._lock = threading.Lock()

    def _get_pipeline(self):
        if self._pipeline is None:
            with self._lock:
                if self._pipeline is None:
                    from transformers import pipeline as hf_pipeline

                    logger.info("Loading sentiment model: %s", self.model_name)
                    self._pipeline = hf_pipeline(
                        "text-classification",
                        model=self.model_name,
                        tokenizer=self.model_name,
                        truncation=True,
                        max_length=512,
                        batch_size=self.batch_size,
                        top_k=1,  # only the top label per input
                        device=_detect_device(),
                    )
                    logger.info("Sentiment model loaded")
        return self._pipeline

    def classify(self, texts: list[str]) -> list[str]:
        """Classify review texts; returns one label per input, in order. A
        chunk that fails is labelled neutral rather than failing the batch."""
        pipe = self._get_pipeline()
        sentiments: list[str] = []
        total = len(texts)
        chunk_size = self.batch_size * 4  # chunked only to surface progress logs

        for start in range(0, total, chunk_size):
            chunk = texts[start : start + chunk_size]
            try:
                for res in pipe(chunk):
                    # res is [{"label": "4 stars", "score": 0.9}] when top_k=1
                    label = res[0]["label"] if isinstance(res, list) else res["label"]
                    sentiments.append(star_label_to_sentiment(label))
            except Exception as exc:  # noqa: BLE001
                logger.error("Sentiment batch failed (chunk start=%d): %s", start, exc)
                sentiments.extend(["neutral"] * len(chunk))
            logger.info("Sentiment: %d / %d reviews classified", len(sentiments), total)

        return sentiments
