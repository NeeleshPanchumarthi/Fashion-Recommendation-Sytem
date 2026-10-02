from data_loader import validate_dataset


META_PATH = (
    r"C:\Users\neele\Documents\Prodapt"
    r"\fashion_rec\data\metadata.parquet"
)

REVIEWS_PATH = (
    r"C:\Users\neele\Documents\Prodapt"
    r"\fashion_rec\data\reviews.parquet"
)


print("=" * 70)
print("TESTING DATASET VALIDATION")
print("=" * 70)


validate_dataset(
    META_PATH,
    REVIEWS_PATH
)