"""Check that the configured Pinecone key and index work.

    python scripts/check_pinecone.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.config import get_settings  # noqa: E402
from app.core.exceptions import AppError  # noqa: E402
from app.dependencies import build_vector_repository  # noqa: E402


def main() -> int:
    settings = get_settings()
    try:
        info = build_vector_repository(settings).ping()
    except AppError as exc:
        print(f"Pinecone check failed: {exc.message}", file=sys.stderr)
        return 1
    print(f"Pinecone OK: index '{info['index']}' holds {info['vector_count']} vectors")
    return 0


if __name__ == "__main__":
    sys.exit(main())
