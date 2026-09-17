import pytest

from core.domain import EligibilityResult, LiquidityLevel, Opportunity, RiskLevel, SearchQuery
from core.ranking import rank, return_fit, risk_fit, score_opportunity, tenure_fit


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


def _eligible(opp: Opportunity, passed_reasons: dict | None = None) -> EligibilityResult:
    return EligibilityResult(opportunity=opp, eligible=True, passed_reasons=passed_reasons or {})


def test_risk_fit_at_diff_zero_and_diff_three():
    assert risk_fit(_opp(risk=RiskLevel.MODERATE), _query(risk=RiskLevel.MODERATE)) == 1.0
    diff_three = risk_fit(_opp(risk=RiskLevel.LOW_MODERATE), _query(risk=RiskLevel.HIGH))
    assert diff_three == pytest.approx(1.0 - 3 * 0.15)


def test_tenure_fit_at_mid_edge_and_open_ended():
    opp = _opp(tenure_min_months=12, tenure_max_months=24)
    assert tenure_fit(opp, _query(tenure_months=18)) == 1.0
    assert tenure_fit(opp, _query(tenure_months=12)) == pytest.approx(0.5)
    open_ended = _opp(tenure_min_months=24, tenure_max_months=None)
    assert tenure_fit(open_ended, _query(tenure_months=999)) == 0.8


def test_return_fit_all_equal_no_divide_by_zero():
    pool = [9.0, 9.0, 9.0]
    assert return_fit(_opp(return_min=9.0), pool) == 1.0


def test_rank_single_eligible_result_does_not_crash():
    opp = _opp()
    ranked = rank([_eligible(opp)], _query())
    assert len(ranked) == 1
    assert ranked[0]["id"] == opp.opportunity_id


def test_higher_return_ranks_higher_all_else_equal():
    low = _opp(opportunity_id="OPP1", return_min=8.0, return_max=8.0)
    high = _opp(opportunity_id="OPP2", return_min=12.0, return_max=12.0)
    ranked = rank([_eligible(low), _eligible(high)], _query())
    assert ranked[0]["id"] == "OPP2"
    assert ranked[0]["score"] > ranked[1]["score"]


def test_score_within_bounds_and_breakdown_sums_to_total():
    opp = _opp()
    score, breakdown = score_opportunity(opp, _query(), [opp.return_min])
    assert 0.0 <= score <= 100.0
    assert round(sum(breakdown.values()), 2) == score


def test_tie_sorts_by_id_ascending():
    ranked = rank([_eligible(_opp(opportunity_id="OPP002")), _eligible(_opp(opportunity_id="OPP001"))], _query())
    assert ranked[0]["score"] == ranked[1]["score"]
    assert [r["id"] for r in ranked] == ["OPP001", "OPP002"]
