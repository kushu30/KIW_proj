from core.domain import (
    LiquidityLevel,
    Opportunity,
    RiskLevel,
    Severity,
    ValidationIssue,
    ValidationReport,
)

_TENURE_UNITS = {"months": 1, "month": 1, "years": 12, "year": 12}


def parse_amount(raw: str) -> float | None:
    """Parse minimum_investment text (plain digits, ₹/Rs. markers, comma grouping, 'lakh') to a rupee float."""
    text = raw.strip().lower().replace("₹", "").replace("rs.", "").replace("rs", "").strip()
    is_lakh = "lakh" in text
    text = text.replace("lakh", "").replace(",", "").strip()
    try:
        value = float(text)
    except ValueError:
        return None
    return value * 100_000 if is_lakh else value


def parse_tenure(raw: str) -> tuple[int, int | None] | None:
    """Parse tenure text ('18 months', '12-24 months', '3 years', '24 months+') to (min, max) months."""
    text = raw.strip().lower()
    open_ended = text.endswith("+")
    text = text.rstrip("+").strip()

    for unit, months in _TENURE_UNITS.items():
        if text.endswith(unit):
            unit_months = months
            text = text[: -len(unit)].strip()
            break
    else:
        return None

    low_text, sep, high_text = text.partition("-")
    try:
        low = int(low_text.strip()) * unit_months
        high = int(high_text.strip()) * unit_months if sep else low
    except ValueError:
        return None
    return (low, None if open_ended else high)


def parse_return(raw: str) -> tuple[float | None, float | None, bool]:
    """Parse expected_return text ('9.2% p.a.', '14-18% p.a.', 'Variable') to (min, max, supported)."""
    text = raw.strip().lower()
    if "%" not in text:
        return (None, None, False)

    low_text, sep, high_text = text.split("%")[0].strip().partition("-")
    try:
        low = float(low_text.strip())
        high = float(high_text.strip()) if sep else low
    except ValueError:
        return (None, None, False)
    return (low, high, True)


def normalize_risk(raw: str) -> RiskLevel | None:
    """Parse a risk label into RiskLevel, or None if it doesn't match one of the 5 labels."""
    try:
        return RiskLevel.from_label(raw)
    except ValueError:
        return None


def normalize_liquidity(raw: str) -> LiquidityLevel | None:
    """Parse a liquidity label into LiquidityLevel, or None if it doesn't match Low/Medium/High."""
    try:
        return LiquidityLevel.from_label(raw)
    except ValueError:
        return None


def validate_record(raw: dict) -> tuple[Opportunity | None, list[ValidationIssue]]:
    """Validate and normalize one raw CSV row; returns (Opportunity, issues) or (None, issues) on error."""
    record_id = (raw.get("opportunity_id") or "").strip() or None
    name = (raw.get("name") or "").strip()
    min_investment = parse_amount(raw.get("minimum_investment", ""))
    tenure = parse_tenure(raw.get("tenure", ""))
    risk = normalize_risk(raw.get("risk", ""))
    liquidity = normalize_liquidity(raw.get("liquidity", ""))
    return_min, return_max, return_supported = parse_return(raw.get("expected_return", ""))

    def issue(sev: Severity, field: str, message: str, raw_value) -> ValidationIssue:
        return ValidationIssue(record_id, field, sev, message, raw_value)

    issues: list[ValidationIssue] = []
    if not record_id:
        issues.append(issue(Severity.ERROR, "opportunity_id", "missing opportunity_id", raw.get("opportunity_id")))
    if not name:
        issues.append(issue(Severity.ERROR, "name", "missing name", raw.get("name")))
    if min_investment is None:
        issues.append(issue(Severity.ERROR, "minimum_investment", "unparseable minimum_investment", raw.get("minimum_investment")))
    if tenure is None:
        issues.append(issue(Severity.ERROR, "tenure", "unparseable tenure", raw.get("tenure")))
    if risk is None:
        issues.append(issue(Severity.ERROR, "risk", "unrecognized risk label", raw.get("risk")))
    if liquidity is None:
        issues.append(issue(Severity.ERROR, "liquidity", "unrecognized liquidity label", raw.get("liquidity")))
    if not return_supported:
        issues.append(issue(Severity.WARNING, "expected_return", "unparseable return; treated as not disclosed", raw.get("expected_return")))

    if any(i.severity == Severity.ERROR for i in issues):
        return None, issues

    opportunity = Opportunity(
        opportunity_id=record_id,
        name=name,
        provider=(raw.get("provider") or "").strip(),
        category=(raw.get("category") or "").strip(),
        min_investment=round(min_investment),
        tenure_min_months=tenure[0],
        tenure_max_months=tenure[1],
        risk=risk,
        return_min=return_min,
        return_max=return_max,
        return_supported=return_supported,
        liquidity=liquidity,
    )
    return opportunity, issues


def validate_dataset(records: list[dict]) -> tuple[list[Opportunity], ValidationReport]:
    """Validate all raw rows, dropping duplicate ids (keep first) and invalid records; never silent."""
    seen_ids: set[str] = set()
    valid: list[Opportunity] = []
    issues: list[ValidationIssue] = []

    for raw in records:
        record_id = (raw.get("opportunity_id") or "").strip()
        if record_id and record_id in seen_ids:
            issues.append(ValidationIssue(record_id, "opportunity_id", Severity.ERROR, "duplicate opportunity_id; keeping first occurrence", record_id))
            continue
        if record_id:
            seen_ids.add(record_id)

        opportunity, record_issues = validate_record(raw)
        issues.extend(record_issues)
        if opportunity is not None:
            valid.append(opportunity)

    report = ValidationReport(
        total=len(records),
        valid_count=len(valid),
        invalid_count=len(records) - len(valid),
        issues=issues,
    )
    return valid, report
