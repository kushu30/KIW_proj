import pytest

from core.data_loader import load_opportunities
from core.domain import LiquidityLevel, RiskLevel, Severity
from core.validator import (
    normalize_liquidity,
    normalize_risk,
    parse_amount,
    parse_return,
    parse_tenure,
    validate_dataset,
    validate_record,
)


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("25000", 25000.0),
        ("₹1,00,000", 100000.0),
        ("Rs. 2 lakh", 200000.0),
        ("₹5 lakh", 500000.0),
        ("₹1.5 lakh", 150000.0),
        ("garbage", None),
    ],
)
def test_parse_amount(raw, expected):
    assert parse_amount(raw) == expected


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("18 months", (18, 18)),
        ("12-24 months", (12, 24)),
        ("3 years", (36, 36)),
        ("24 months+", (24, None)),
        ("garbage", None),
    ],
)
def test_parse_tenure(raw, expected):
    assert parse_tenure(raw) == expected


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("9.2% p.a.", (9.2, 9.2, True)),
        ("15% p.a.", (15.0, 15.0, True)),
        ("14-18% p.a.", (14.0, 18.0, True)),
        ("10.1-11.0% p.a.", (10.1, 11.0, True)),
        ("Variable", (None, None, False)),
        ("garbage", (None, None, False)),
    ],
)
def test_parse_return(raw, expected):
    assert parse_return(raw) == expected


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("Low", RiskLevel.LOW),
        ("Moderate-High", RiskLevel.MODERATE_HIGH),
        ("Medium", None),
        ("Moderately High", None),
        ("garbage", None),
    ],
)
def test_normalize_risk(raw, expected):
    assert normalize_risk(raw) == expected


@pytest.mark.parametrize(
    "raw,expected",
    [("High", LiquidityLevel.HIGH), ("Medium", LiquidityLevel.MEDIUM), ("garbage", None)],
)
def test_normalize_liquidity(raw, expected):
    assert normalize_liquidity(raw) == expected


def _raw_row(**overrides) -> dict:
    row = {
        "opportunity_id": "OPP001",
        "name": "Test Opportunity",
        "provider": "Test Provider",
        "category": "Debt",
        "minimum_investment": "50000",
        "tenure": "12 months",
        "risk": "Moderate",
        "expected_return": "9% p.a.",
        "liquidity": "High",
    }
    row.update(overrides)
    return row


def test_missing_required_field_is_error_and_excludes_record():
    opportunity, issues = validate_record(_raw_row(risk=""))
    assert opportunity is None
    assert any(i.field == "risk" and i.severity == Severity.ERROR for i in issues)


def test_unparseable_return_is_warning_and_record_kept():
    opportunity, issues = validate_record(_raw_row(expected_return="Variable"))
    assert opportunity is not None
    assert opportunity.return_supported is False
    assert any(i.field == "expected_return" and i.severity == Severity.WARNING for i in issues)


def test_duplicate_id_keeps_first_and_flags_second():
    rows = [_raw_row(opportunity_id="OPP009", name="First"), _raw_row(opportunity_id="OPP009", name="Second")]
    valid, report = validate_dataset(rows)
    assert len(valid) == 1
    assert valid[0].name == "First"
    assert any(i.field == "opportunity_id" and i.severity == Severity.ERROR for i in report.issues)


def test_real_dataset_valid_plus_invalid_equals_total():
    valid, report = validate_dataset(load_opportunities())
    assert report.valid_count + report.invalid_count == report.total
    assert report.total == 31
    assert report.valid_count == 28
    assert report.invalid_count == 3
