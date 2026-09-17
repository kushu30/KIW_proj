import csv
from pathlib import Path

from core.exceptions import DatasetLoadError

DATA_DIR = Path(__file__).resolve().parent.parent / "data"


def _load_csv(path: Path) -> list[dict]:
    if not path.exists():
        raise DatasetLoadError(f"dataset file not found: {path}")

    with path.open(newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    if not rows:
        raise DatasetLoadError(f"dataset file is empty: {path}")

    return rows


def load_opportunities() -> list[dict]:
    """Read data/opportunities.csv into raw dicts, no cleaning or normalization."""
    return _load_csv(DATA_DIR / "opportunities.csv")


def load_sample_queries() -> list[dict]:
    """Read data/sample_queries.csv into raw dicts, no cleaning or normalization."""
    return _load_csv(DATA_DIR / "sample_queries.csv")
