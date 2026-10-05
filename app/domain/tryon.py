"""Virtual try-on rules: which products can be tried on, and a job's lifecycle.

The try-on model (Leffa) dresses a person photo in a garment photo. It
handles three garment types; anything else (shoes, hats, bags...) has no
try-on. A job moves through stages the UI shows as progress:

    queued -> uploading -> waiting_for_gpu -> generating -> finishing -> done
    (any stage can end in failed)
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

from app.domain.attributes.category_extractor import extract_category

UPPER_BODY = "upper_body"
LOWER_BODY = "lower_body"
DRESSES = "dresses"
GARMENT_TYPES = (UPPER_BODY, LOWER_BODY, DRESSES)


_GARMENT_TYPE_BY_CATEGORY = {
    "shirt": UPPER_BODY,
    "t-shirt": UPPER_BODY,
    "blouse": UPPER_BODY,
    "hoodie": UPPER_BODY,
    "sweater": UPPER_BODY,
    "jacket": UPPER_BODY,
    "coat": UPPER_BODY,
    "pants": LOWER_BODY,
    "trousers": LOWER_BODY,
    "jeans": LOWER_BODY,
    "shorts": LOWER_BODY,
    "skirt": LOWER_BODY,
    "dress": DRESSES,
}


def garment_type_for(category: Optional[str], title: Optional[str] = None) -> Optional[str]:
    """The try-on garment type for a product, or None if it can't be tried on.

    Uses the indexed category, falling back to the title for products
    ingested before categories were extracted.
    """
    category = category or extract_category(title or "")
    return _GARMENT_TYPE_BY_CATEGORY.get((category or "").lower())


class TryOnStage(str, Enum):
    QUEUED = "queued"                    # waiting for a free worker in this service
    UPLOADING = "uploading"              # sending the photos to the model
    WAITING_FOR_GPU = "waiting_for_gpu"  # in the Space's queue (queue_position set)
    GENERATING = "generating"            # the model is running
    FINISHING = "finishing"              # downloading the result
    DONE = "done"
    FAILED = "failed"


@dataclass
class TryOnJob:
    garment_type: str
    job_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    stage: TryOnStage = TryOnStage.QUEUED
    queue_position: Optional[int] = None
    result_image: Optional[bytes] = None
    result_mime_type: str = "image/webp"
    error: Optional[str] = None
    created_at: float = field(default_factory=time.monotonic)
    finished_at: Optional[float] = None

    @property
    def finished(self) -> bool:
        return self.stage in (TryOnStage.DONE, TryOnStage.FAILED)

    @property
    def elapsed_seconds(self) -> float:
        return (self.finished_at or time.monotonic()) - self.created_at
