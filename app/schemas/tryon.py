"""HTTP contracts for /api/try-on (start a job, then poll it)."""

from __future__ import annotations

import base64
from typing import Optional

from pydantic import BaseModel, Field

from app.domain.tryon import TryOnJob, TryOnStage


class TryOnJobResponse(BaseModel):
    job_id: str
    stage: TryOnStage = Field(..., description="queued | uploading | waiting_for_gpu | generating | finishing | done | failed")
    garment_type: str = Field(..., description="upper_body | lower_body | dresses")
    queue_position: Optional[int] = Field(None, description="Place in the GPU queue while stage is waiting_for_gpu")
    elapsed_seconds: float = Field(..., description="Seconds since the job started")
    result_image: Optional[str] = Field(None, description="Generated image as a data: URL, once stage is done")
    error: Optional[str] = Field(None, description="User-facing reason, once stage is failed")

    @classmethod
    def from_job(cls, job: TryOnJob) -> "TryOnJobResponse":
        result = None
        if job.result_image is not None:
            result = f"data:{job.result_mime_type};base64,{base64.b64encode(job.result_image).decode('ascii')}"
        return cls(
            job_id=job.job_id,
            stage=job.stage,
            garment_type=job.garment_type,
            queue_position=job.queue_position,
            elapsed_seconds=round(job.elapsed_seconds, 1),
            result_image=result,
            error=job.error,
        )
