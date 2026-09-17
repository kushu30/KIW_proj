import logging

from core.data_loader import load_opportunities
from core.domain import Opportunity, ValidationReport
from core.validator import validate_dataset

logger = logging.getLogger(__name__)

_opportunities: list[Opportunity] = []
_report: ValidationReport | None = None
_initialized = False


def initialize() -> None:
    """Load and validate the dataset once; safe to call more than once (Django autoreload)."""
    global _initialized, _opportunities, _report
    if _initialized:
        return

    raw_records = load_opportunities()
    _opportunities, _report = validate_dataset(raw_records)
    logger.info("dataset loaded: %d valid, %d invalid", _report.valid_count, _report.invalid_count)
    _initialized = True


def get_opportunities() -> list[Opportunity]:
    return _opportunities


def get_report() -> ValidationReport:
    return _report
