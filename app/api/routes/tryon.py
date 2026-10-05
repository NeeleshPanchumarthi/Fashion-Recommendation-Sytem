"""Virtual try-on: POST /api/try-on starts a job, GET /api/try-on/{job_id} polls it."""

from __future__ import annotations

from fastapi import APIRouter, Depends, File, Form, UploadFile, status

from app.dependencies import get_tryon_service
from app.schemas.common import ErrorResponse
from app.schemas.tryon import TryOnJobResponse
from app.services.tryon_service import TryOnService

router = APIRouter(tags=["try-on"])


# Plain `def`: decoding and resizing the photo is CPU work, so FastAPI runs
# it in a worker thread. The try-on itself runs in the service's background pool.
@router.post(
    "/try-on",
    response_model=TryOnJobResponse,
    status_code=status.HTTP_202_ACCEPTED,
    responses={400: {"model": ErrorResponse}, 429: {"model": ErrorResponse}},
)
def start_try_on(
    person_image: UploadFile = File(..., description="Photo of the person (JPEG, PNG or WebP)"),
    garment_image_url: str = Form(..., description="Product image URL (the card's main image)"),
    garment_type: str = Form(..., description="upper_body | lower_body | dresses (from the search result)"),
    service: TryOnService = Depends(get_tryon_service),
) -> TryOnJobResponse:
    # Read at most one byte over the limit, so a huge upload isn't held in memory.
    photo = person_image.file.read(service.max_upload_bytes + 1)
    job = service.start(photo, garment_image_url, garment_type)
    return TryOnJobResponse.from_job(job)


@router.get(
    "/try-on/{job_id}",
    response_model=TryOnJobResponse,
    responses={404: {"model": ErrorResponse}},
)
def get_try_on_job(job_id: str, service: TryOnService = Depends(get_tryon_service)) -> TryOnJobResponse:
    return TryOnJobResponse.from_job(service.get(job_id))
