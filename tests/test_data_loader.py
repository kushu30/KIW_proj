import pytest

from core.data_loader import _load_csv, load_opportunities
from core.exceptions import DatasetLoadError


def test_load_opportunities_returns_31_raw_rows():
    records = load_opportunities()
    assert len(records) == 31


def test_missing_file_raises(tmp_path):
    with pytest.raises(DatasetLoadError):
        _load_csv(tmp_path / "does_not_exist.csv")


def test_empty_file_raises(tmp_path):
    empty_file = tmp_path / "empty.csv"
    empty_file.write_text("")
    with pytest.raises(DatasetLoadError):
        _load_csv(empty_file)
