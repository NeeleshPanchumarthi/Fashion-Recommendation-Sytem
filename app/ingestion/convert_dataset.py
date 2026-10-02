import pandas as pd
from pathlib import Path
import argparse

def convert_jsonl_to_parquet(jsonl_path: Path, parquet_path: Path):
    """Read a JSONL file into a DataFrame and write it as Parquet.

    Args:
        jsonl_path: Path to the source .jsonl file.
        parquet_path: Destination .parquet file.
    """
    if not jsonl_path.exists():
        raise FileNotFoundError(f"Source file not found: {jsonl_path}")
    df = pd.read_json(jsonl_path, lines=True)
    df.to_parquet(parquet_path, index=False)
    print(f"Converted {jsonl_path.name} -> {parquet_path.name}")

def main(dataset_dir: Path, output_dir: Path):
    """Convert dataset JSONL files to Parquet files expected by the pipeline.

    The dataset directory should contain two files:
      - meta_*.jsonl : product metadata
      - *.jsonl      : reviews (excluding the meta file)
    The script writes `metadata.parquet` and `reviews.parquet` into the output directory.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    # Identify metadata file (starts with 'meta_')
    meta_file = next(dataset_dir.glob('meta_*.jsonl'), None)
    if not meta_file:
        raise FileNotFoundError("Metadata JSONL file not found (expected pattern meta_*.jsonl)")
    # Identify reviews file (first .jsonl that is not the meta file)
    review_file = next(p for p in dataset_dir.glob('*.jsonl') if p != meta_file)

    convert_jsonl_to_parquet(meta_file, output_dir / 'metadata.parquet')
    convert_jsonl_to_parquet(review_file, output_dir / 'reviews.parquet')

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Convert raw JSONL dataset to Parquet files for the ingestion pipeline.")
    parser.add_argument("--dataset-dir", type=Path, default=Path(r"C:/Users/neele/Documents/Prodapt/Dataset"),
                        help="Directory containing the raw JSONL dataset files.")
    parser.add_argument("--output-dir", type=Path, default=Path(r"C:/Users/neele/Documents/Prodapt/fashion_rec/data"),
                        help="Directory where metadata.parquet and reviews.parquet will be written.")
    args = parser.parse_args()
    main(args.dataset_dir, args.output_dir)
