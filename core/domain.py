import re
from dataclasses import dataclass, field
from enum import IntEnum, StrEnum
from typing import Any, NamedTuple

_RISK_LABELS = {"low": 1, "low-moderate": 2, "moderate": 3, "moderate-high": 4, "high": 5}
_LIQUIDITY_LABELS = {"low": 1, "medium": 2, "high": 3}


def _parse_label(cls: type, labels: dict[str, int], value: str, expected: str):
    normalized = re.sub(r"-+", "-", value.strip().lower().replace("_", "-").replace(" ", "-"))
    if normalized not in labels:
        raise ValueError(f"invalid {cls.__name__} label {value!r}; expected one of {expected}")
    return cls(labels[normalized])


class RiskLevel(IntEnum):
    LOW = 1
    LOW_MODERATE = 2
    MODERATE = 3
    MODERATE_HIGH = 4
    HIGH = 5

    @classmethod
    def from_label(cls, value: str) -> "RiskLevel":
        """Parse a risk label case- and separator-insensitively."""
        return _parse_label(cls, _RISK_LABELS, value, "Low, Low-Moderate, Moderate, Moderate-High, High")


class LiquidityLevel(IntEnum):
    LOW = 1
    MEDIUM = 2
    HIGH = 3

    @classmethod
    def from_label(cls, value: str) -> "LiquidityLevel":
        """Parse a liquidity label case-insensitively."""
        return _parse_label(cls, _LIQUIDITY_LABELS, value, "Low, Medium, High")


class Severity(StrEnum):
    ERROR = "error"
    WARNING = "warning"


class RuleOutcome(NamedTuple):
    passed: bool
    reason: str


@dataclass
class Opportunity:
    opportunity_id: str
    name: str
    provider: str
    category: str
    min_investment: int
    tenure_min_months: int
    tenure_max_months: int | None
    risk: RiskLevel
    return_min: float | None
    return_max: float | None
    return_supported: bool
    liquidity: LiquidityLevel


@dataclass
class ValidationIssue:
    record_id: str | None
    field: str
    severity: Severity
    message: str
    raw_value: Any


@dataclass
class ValidationReport:
    total: int
    valid_count: int
    invalid_count: int
    issues: list[ValidationIssue] = field(default_factory=list)


@dataclass
class SearchQuery:
    investment_amount: float
    risk: RiskLevel
    tenure_months: int
    minimum_return: float | None = None
    category: str | None = None
    liquidity: LiquidityLevel | None = None


@dataclass
class EligibilityResult:
    opportunity_id: str
    eligible: bool
    rule_outcomes: dict[str, RuleOutcome] = field(default_factory=dict)
