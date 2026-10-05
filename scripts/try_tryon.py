"""Try the virtual try-on Space (Leffa) on one person photo and one garment.

    python scripts/try_tryon.py                                  # sample person + sample top
    python scripts/try_tryon.py --person me.jpg                  # your own photo
    python scripts/try_tryon.py --garment dress --person me.jpg  # a sample dress
    python scripts/try_tryon.py --garment-url <image url> --type lower_body

Writes the result to data/tryon/. Uses HF_TOKEN from .env when set.
"""

from __future__ import annotations

import argparse
import shutil
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import io  # noqa: E402
import tempfile  # noqa: E402
import urllib.request  # noqa: E402

from gradio_client import Client, handle_file  # noqa: E402
from PIL import Image, ImageOps  # noqa: E402

from app.core.config import PROJECT_ROOT, get_settings  # noqa: E402

# A front-facing person photo from Leffa's own examples (VITON-HD dataset).
SAMPLE_PERSON = "https://huggingface.co/franciszzj/Leffa/resolve/main/examples/person1/01350_00.jpg"

# Products from data/metadata.parquet (MAIN images): name -> (url, garment type).
SAMPLE_GARMENTS = {
    "top": ("https://m.media-amazon.com/images/I/41NVNs6JKxL._AC_.jpg", "upper_body"),        # B07Q6YM1D8 t-shirt (clean flat-lay)
    "dress": ("https://m.media-amazon.com/images/I/411CWuk2NdL._AC_.jpg", "dresses"),         # B09VC1M2HX dress
    "jeans": ("https://m.media-amazon.com/images/I/41g7bxQjoIL._AC_.jpg", "lower_body"),      # B01N7LW9YA jeans
}

GARMENT_TYPES = ("upper_body", "lower_body", "dresses")

# Leffa works at 768x1024. A photo of any other shape gets letterboxed with
# white bars, which shrinks the person and blurs the result.
MODEL_SIZE = (768, 1024)


def prepare_person(source: str, center_x: float) -> str:
    """Crop the person photo to 3:4 portrait around center_x (0-1), resize, save to a temp file."""
    if source.startswith(("http://", "https://")):
        image = Image.open(io.BytesIO(urllib.request.urlopen(source, timeout=30).read()))
    else:
        image = Image.open(source)
    image = ImageOps.exif_transpose(image).convert("RGB")  # phone photos store rotation in EXIF

    width, height = image.size
    target_ratio = MODEL_SIZE[0] / MODEL_SIZE[1]
    if width / height > target_ratio:
        # Too wide (e.g. a landscape photo): keep full height, cut the sides.
        crop_w = round(height * target_ratio)
        left = min(max(round(width * center_x - crop_w / 2), 0), width - crop_w)
        image = image.crop((left, 0, left + crop_w, height))
    else:
        # Too tall: keep full width, cut from the bottom (keeps the head in frame).
        image = image.crop((0, 0, width, round(width / target_ratio)))

    image = image.resize(MODEL_SIZE, Image.Resampling.LANCZOS)
    path = Path(tempfile.gettempdir()) / "tryon_person.jpg"
    image.save(path, quality=95)  # re-encoding also drops EXIF (e.g. GPS location)
    return str(path)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--person", default=SAMPLE_PERSON, help="person photo: local path or URL")
    parser.add_argument("--garment", choices=sorted(SAMPLE_GARMENTS), default="top", help="sample garment")
    parser.add_argument("--garment-url", help="any garment image URL (overrides --garment)")
    parser.add_argument("--type", choices=GARMENT_TYPES, help="garment type (required with --garment-url)")
    parser.add_argument("--steps", type=int, default=30, help="inference steps (fewer = faster, rougher)")
    parser.add_argument(
        "--center-x", type=float, default=0.5,
        help="horizontal position of the person in the photo, 0=left edge 1=right edge (for cropping)",
    )
    args = parser.parse_args()

    if args.garment_url:
        if not args.type:
            parser.error("--type is required with --garment-url")
        garment_url, garment_type = args.garment_url, args.type
    else:
        garment_url, garment_type = SAMPLE_GARMENTS[args.garment]
        garment_type = args.type or garment_type

    settings = get_settings()
    token = settings.HF_TOKEN.get_secret_value() or None
    print(f"Space: {settings.TRYON_SPACE} ({'with' if token else 'WITHOUT'} HF token)")
    print(f"Garment: {garment_type} {garment_url}")

    person_path = prepare_person(args.person, args.center_x)

    client = Client(settings.TRYON_SPACE, token=token, verbose=False)
    started = time.monotonic()
    image_path, _mask, _densepose = client.predict(
        src_image_path=handle_file(person_path),
        ref_image_path=handle_file(garment_url),
        ref_acceleration=False,
        step=args.steps,
        scale=2.5,
        seed=42,
        # Leffa has two checkpoints: VITON-HD (tops) and DressCode (all three types).
        vt_model_type="viton_hd" if garment_type == "upper_body" else "dress_code",
        vt_garment_type=garment_type,
        vt_repaint=False,
        api_name="/leffa_predict_vt",
    )
    elapsed = time.monotonic() - started

    out_dir = PROJECT_ROOT / "data" / "tryon"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{garment_type}_{int(time.time())}{Path(image_path).suffix or '.png'}"
    shutil.copy(image_path, out_path)
    print(f"Done in {elapsed:.0f}s -> {out_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
