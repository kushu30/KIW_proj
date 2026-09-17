from core.domain import LiquidityLevel, Opportunity, RiskLevel, SearchQuery
from core.eligibility import (
    check_amount,
    check_category,
    check_liquidity,
    check_min_return,
    check_risk,
    check_tenure,
    evaluate,
    filter_eligible,
)


def _opp(**overrides) -> Opportunity:
    base = dict(
        opportunity_id="OPP1",
        name="Test Opportunity",
        provider="Test Provider",
        category="Debt",
        min_investment=50000,
        tenure_min_months=12,
        tenure_max_months=24,
        risk=RiskLevel.MODERATE,
        return_min=9.0,
        return_max=11.0,
        return_supported=True,
        liquidity=LiquidityLevel.MEDIUM,
    )
    base.update(overrides)
    return Opportunity(**base)


def _query(**overrides) -> SearchQuery:
    base = dict(
        investment_amount=50000,
        risk=RiskLevel.MODERATE,
        tenure_months=18,
        minimum_return=None,
        category=None,
        liquidity=None,
    )
    base.update(overrides)
    return SearchQuery(**base)


def test_amount_at_minimum_passes_below_fails():
    opp = _opp(min_investment=50000)
    assert check_amount(opp, _query(investment_amount=50000))[0] is True
    assert check_amount(opp, _query(investment_amount=49999))[0] is False


def test_risk_equal_passes_higher_fails():
    assert check_risk(_opp(risk=RiskLevel.MODERATE), _query(risk=RiskLevel.MODERATE))[0] is True
    assert check_risk(_opp(risk=RiskLevel.HIGH), _query(risk=RiskLevel.MODERATE))[0] is False


def test_tenure_edges_outside_and_open_ended():
    opp = _opp(tenure_min_months=12, tenure_max_months=24)
    assert check_tenure(opp, _query(tenure_months=12))[0] is True
    assert check_tenure(opp, _query(tenure_months=24))[0] is True
    assert check_tenure(opp, _query(tenure_months=11))[0] is False
    assert check_tenure(opp, _query(tenure_months=25))[0] is False

    open_ended = _opp(tenure_min_months=24, tenure_max_months=None)
    assert check_tenure(open_ended, _query(tenure_months=1000))[0] is True


def test_min_return_uses_return_min_and_handles_unsupported():
    opp = _opp(return_min=9.0, return_max=11.0, return_supported=True)
    assert check_min_return(opp, _query(minimum_return=None))[0] is True
    assert check_min_return(opp, _query(minimum_return=9.0))[0] is True
    # only return_max (11.0) would qualify for 10.5 — rule uses return_min, so this fails
    assert check_min_return(opp, _query(minimum_return=10.5))[0] is False

    unsupported = _opp(return_min=None, return_max=None, return_supported=False)
    assert check_min_return(unsupported, _query(minimum_return=1.0))[0] is False


def test_category_case_insensitive_and_absent_passes():
    opp = _opp(category="Debt")
    assert check_category(opp, _query(category="debt"))[0] is True
    assert check_category(opp, _query(category="Equity"))[0] is False
    assert check_category(opp, _query(category=None))[0] is True


def test_liquidity_higher_passes_lower_fails():
    opp = _opp(liquidity=LiquidityLevel.MEDIUM)
    assert check_liquidity(opp, _query(liquidity=LiquidityLevel.MEDIUM))[0] is True
    assert check_liquidity(opp, _query(liquidity=LiquidityLevel.HIGH))[0] is False
    assert check_liquidity(_opp(liquidity=LiquidityLevel.HIGH), _query(liquidity=LiquidityLevel.MEDIUM))[0] is True


def test_evaluate_never_short_circuits():
    opp = _opp(min_investment=1_000_000, category="Debt")
    query = _query(investment_amount=1000, category="Equity")
    result = evaluate(opp, query)
    assert result.eligible is False
    assert set(result.failed_rules) == {"amount", "category"}
    assert set(result.passed_reasons) == {"risk", "tenure", "min_return", "liquidity"}


def test_rejection_summary_counts_failures_per_rule():
    opps = [
        _opp(opportunity_id="A", risk=RiskLevel.HIGH),
        _opp(opportunity_id="B", min_investment=1_000_000),
        _opp(opportunity_id="C"),
    ]
    results, summary = filter_eligible(opps, _query(investment_amount=50000, risk=RiskLevel.MODERATE))
    assert summary == {"risk": 1, "amount": 1}
    assert sum(r.eligible for r in results) == 1
