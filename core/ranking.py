from core.domain import EligibilityResult, Opportunity, SearchQuery

WEIGHTS = {"return": 30, "risk_fit": 25, "tenure_fit": 20, "budget": 15, "preference": 10}


def return_fit(opp: Opportunity, return_min_pool: list[float]) -> float:
    if not opp.return_supported:
        return 0.5
    lo, hi = min(return_min_pool), max(return_min_pool)
    if hi == lo:
        return 1.0
    # Floored at 0.2: every candidate here already cleared the user's minimum-return bar,
    # so the worst performer in the eligible set still earns some credit, not zero.
    return max(0.2, (opp.return_min - lo) / (hi - lo))


def risk_fit(opp: Opportunity, query: SearchQuery) -> float:
    diff = query.risk - opp.risk
    return max(0.3, 1.0 - diff * 0.15)


def tenure_fit(opp: Opportunity, query: SearchQuery) -> float:
    if opp.tenure_max_months is None:
        return 0.8
    mid = (opp.tenure_min_months + opp.tenure_max_months) / 2
    half = (opp.tenure_max_months - opp.tenure_min_months) / 2
    if half == 0:
        return 1.0
    return 1 - 0.5 * abs(query.tenure_months - mid) / half


def budget_fit(opp: Opportunity, query: SearchQuery) -> float:
    value = 1 - (opp.min_investment / query.investment_amount)
    return max(0.0, min(1.0, value))


def preference_fit(opp: Opportunity, query: SearchQuery) -> float:
    preferences = [p for p in (query.category, query.liquidity) if p is not None]
    if not preferences:
        return 1.0

    share = 1.0 / len(preferences)
    earned = 0.0
    if query.category is not None and opp.category.lower() == query.category.lower():
        earned += share
    if query.liquidity is not None:
        if opp.liquidity == query.liquidity:
            earned += share
        elif opp.liquidity > query.liquidity:
            earned += share * 0.5
    return earned


def score_opportunity(
    opp: Opportunity, query: SearchQuery, return_min_pool: list[float]
) -> tuple[float, dict[str, float]]:
    """Score one opportunity 0-100; breakdown holds POINTS (fit x weight) per component, 2 decimals."""
    fits = {
        "return": return_fit(opp, return_min_pool),
        "risk_fit": risk_fit(opp, query),
        "tenure_fit": tenure_fit(opp, query),
        "budget": budget_fit(opp, query),
        "preference": preference_fit(opp, query),
    }
    breakdown = {name: round(fit * WEIGHTS[name], 2) for name, fit in fits.items()}
    return round(sum(breakdown.values()), 2), breakdown


def rank(results: list[EligibilityResult], query: SearchQuery) -> list[dict]:
    """Score every eligible result and sort by score desc, then id asc."""
    eligible = [r for r in results if r.eligible]
    return_min_pool = [r.opportunity.return_min for r in eligible if r.opportunity.return_supported]

    ranked = []
    for result in eligible:
        opp = result.opportunity
        score, breakdown = score_opportunity(opp, query, return_min_pool)
        summary = (
            f"score {score:.2f}/100 (return {breakdown['return']}, risk_fit {breakdown['risk_fit']}, "
            f"tenure_fit {breakdown['tenure_fit']}, budget {breakdown['budget']}, "
            f"preference {breakdown['preference']})"
        )
        ranked.append(
            {
                "id": opp.opportunity_id,
                "name": opp.name,
                "score": score,
                "score_breakdown": breakdown,
                "reasons": list(result.passed_reasons.values()) + [summary],
                "attributes": {
                    "provider": opp.provider,
                    "category": opp.category,
                    "min_investment": opp.min_investment,
                    "tenure_min_months": opp.tenure_min_months,
                    "tenure_max_months": opp.tenure_max_months,
                    "risk": opp.risk.name,
                    "return_min": opp.return_min,
                    "return_max": opp.return_max,
                    "return_supported": opp.return_supported,
                    "liquidity": opp.liquidity.name,
                },
            }
        )

    ranked.sort(key=lambda item: (-item["score"], item["id"]))
    return ranked
