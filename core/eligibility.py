from core.domain import EligibilityResult, Opportunity, SearchQuery


def check_amount(opp: Opportunity, query: SearchQuery) -> tuple[bool, str]:
    passed = query.investment_amount >= opp.min_investment
    if passed:
        return True, f"investment {query.investment_amount:g} meets minimum {opp.min_investment}"
    return False, f"investment {query.investment_amount:g} below minimum {opp.min_investment}"


def check_risk(opp: Opportunity, query: SearchQuery) -> tuple[bool, str]:
    if opp.risk <= query.risk:
        return True, f"risk {opp.risk.name} within tolerance {query.risk.name}"
    return False, f"risk {opp.risk.name} exceeds tolerance {query.risk.name}"


def check_tenure(opp: Opportunity, query: SearchQuery) -> tuple[bool, str]:
    lo, hi = opp.tenure_min_months, opp.tenure_max_months
    span = f"{lo}+ months" if hi is None else f"{lo}-{hi} months"
    if query.tenure_months < lo or (hi is not None and query.tenure_months > hi):
        return False, f"tenure {query.tenure_months} months outside {span}"
    return True, f"tenure {query.tenure_months} months within {span}"


def check_min_return(opp: Opportunity, query: SearchQuery) -> tuple[bool, str]:
    if query.minimum_return is None:
        return True, "no preference given"
    if not opp.return_supported:
        return False, f"return not disclosed; cannot confirm >= {query.minimum_return:g}%"
    if opp.return_min >= query.minimum_return:
        return True, f"return_min {opp.return_min:g}% meets minimum {query.minimum_return:g}%"
    return False, f"return_min {opp.return_min:g}% below minimum {query.minimum_return:g}%"


def check_category(opp: Opportunity, query: SearchQuery) -> tuple[bool, str]:
    if query.category is None:
        return True, "no preference given"
    if opp.category.lower() == query.category.lower():
        return True, f"category {opp.category} matches {query.category}"
    return False, f"category {opp.category} does not match {query.category}"


def check_liquidity(opp: Opportunity, query: SearchQuery) -> tuple[bool, str]:
    if query.liquidity is None:
        return True, "no preference given"
    if opp.liquidity >= query.liquidity:
        return True, f"liquidity {opp.liquidity.name} meets minimum {query.liquidity.name}"
    return False, f"liquidity {opp.liquidity.name} below minimum {query.liquidity.name}"


def evaluate(opp: Opportunity, query: SearchQuery) -> EligibilityResult:
    """Run all six eligibility rules against one opportunity; never short-circuits."""
    outcomes = {
        "amount": check_amount(opp, query),
        "risk": check_risk(opp, query),
        "tenure": check_tenure(opp, query),
        "min_return": check_min_return(opp, query),
        "category": check_category(opp, query),
        "liquidity": check_liquidity(opp, query),
    }

    passed_reasons = {name: reason for name, (passed, reason) in outcomes.items() if passed}
    failed_reasons = {name: reason for name, (passed, reason) in outcomes.items() if not passed}
    failed_rules = list(failed_reasons)

    return EligibilityResult(
        opportunity=opp,
        eligible=not failed_rules,
        passed_reasons=passed_reasons,
        failed_reasons=failed_reasons,
        failed_rules=failed_rules,
    )


def filter_eligible(
    opportunities: list[Opportunity], query: SearchQuery
) -> tuple[list[EligibilityResult], dict[str, int]]:
    """Evaluate every opportunity; return results plus a per-rule failure count for the no-match summary."""
    results = [evaluate(opp, query) for opp in opportunities]
    rejection_summary: dict[str, int] = {}
    for result in results:
        for rule_name in result.failed_rules:
            rejection_summary[rule_name] = rejection_summary.get(rule_name, 0) + 1
    return results, rejection_summary
