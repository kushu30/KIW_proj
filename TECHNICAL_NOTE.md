# Technical note

## Structure vs. the brief

The brief's suggested layout (`src/api.py`, `src/models.py`, etc.) is a generic Python layout.
This is a Django project, and in Django `models.py` means ORM models — using that name for
plain dataclasses would confuse anyone who opens the file expecting a database table. So the
layout follows Django's own convention instead:

| Brief suggested | This project | Why |
|---|---|---|
| `src/models.py` | `core/domain.py` | `models.py` in Django means ORM models; there's no database here, so the name would mislead. |
| `src/api.py` | `opportunities/views.py` + `serializers.py` + `urls.py` | Django splits routing, request/response shaping, and handlers into separate files by convention. |
| a single `src/` package | `core/` (pure Python) + `opportunities/` (Django app) | `core/` has zero Django imports and is unit-tested without Django running at all. `opportunities/` is a thin HTTP layer that converts DRF requests into `core.domain.SearchQuery` objects and converts `core` results back into JSON — nothing in `core/` ever sees a DRF or Django object. |
| — | `opportunities/store.py` | Holds the loaded dataset + validation report as module-level state, since there's no database to query. `apps.py.ready()` populates it once at startup. |

## Data validation

Raw CSV columns don't match the target schema 1:1. `tenure` and `expected_return` are each one
free-text column that has to split into two normalized fields (min/max), and
`minimum_investment` alone has five different raw formats (plain digits, `₹` with Indian-style
comma grouping, `Rs. N lakh`, `₹N lakh`, `₹N.N lakh`). All of this is catalogued with real
examples in `notes.md` before any parsing code was written.

`core/validator.py` has one small, pure parser per field (`parse_amount`, `parse_tenure`,
`parse_return`, `normalize_risk`, `normalize_liquidity`). `validate_record()` runs all of them on
a row regardless of whether an earlier one failed, so a row with two problems reports two
issues, not one. `validate_dataset()` also catches duplicate ids, keeping the first occurrence.

Two severities: `error` excludes the record, `warning` keeps it. An unparseable return
(`"Variable"`) is a warning only — the record stays usable with `return_supported=False`, since
the eligibility/ranking rules already define what to do with that case. Missing/invalid id,
name, minimum investment, tenure, risk, or liquidity are errors.

Running the validator on the actual dataset:

- 31 raw rows (30 opportunities + one deliberate duplicate id, `OPP030`)
- 28 valid, 3 excluded: `OPP030` (duplicate, second occurrence), `OPP002` (risk =
  `"Medium"`, not one of the 5 fixed labels), `OPP005` (risk = `"Moderately High"`, also not one
  of the 5 labels)
- 1 warning: `OPP014` (return = `"Variable"`, kept with `return_supported=False`)

I deliberately did **not** treat `"Medium"` or `"Moderately High"` as typos for `"Moderate"` /
`"Moderate-High"` and silently fix them. The risk scale is fixed at 5 exact labels; guessing what
a malformed value "probably meant" felt riskier than excluding it and reporting why. That's a
judgment call, not a certainty — full reasoning is in `notes.md`.

## Eligibility rules

All six rules run for every opportunity even after one fails, so a rejected record's reasons are
complete, not just "the first thing that went wrong":

| Rule | Logic | Reasoning |
|---|---|---|
| amount | `investment_amount >= min_investment` | Affordability check. No `max_investment` field exists anywhere in the schema or data, so there's no upper bound to check. |
| risk | `opportunity.risk <= user.risk` | Ordinal — a Low-risk fund suits a High-risk-tolerant user, not the reverse. |
| tenure | `min_months <= tenure <= max_months` (skip upper bound if open-ended) | Matches the requested lock-in period against the product's actual term. |
| minimum_return | `return_supported and return_min >= minimum_return` | Uses `return_min`, not `return_max` — a "14-18%" range only guarantees the floor; qualifying on the ceiling would promise an outcome the product doesn't guarantee. |
| category | case-insensitive substring match (`requested in opportunity_category`), only if given | Providers name specific products ("Corporate Debt", "Real Estate Debt"); users think in broad asset classes ("Debt"). A broad query term should match a narrower product name that contains it. Changed from exact match after checking real data: two opportunities (`OPP012`, `OPP023`) do have the exact category `"Debt"`, but seven others (`Corporate Debt`, `Real Estate Debt`, `Venture Debt`, ...) would be invisible to a "Debt" search under exact matching even though they're clearly the same asset class to a user. |
| liquidity | `opportunity.liquidity >= requested`, only if given | Liquidity is ordinal (how easily you can exit). More liquidity than requested is strictly better, so it's a floor, not an exact match. |

## Ranking

Score is 0-100 across five weighted components, each normalized to 0.0-1.0 first:

| Component | Weight | Formula |
|---|---|---|
| return | 30 | min-max normalize `return_min` across the eligible set, floored at 0.2 (unsupported = 0.5, all equal = 1.0) |
| risk_fit | 25 | `1.0 - (user.risk - opp.risk) * 0.15`, floored at 0.3 |
| tenure_fit | 20 | 0.8 if open-ended; otherwise 1 minus distance from the product's midpoint, scaled by its half-width |
| budget | 15 | `1 - (min_investment / investment_amount)`, clipped to [0, 1] |
| preference | 10 | split evenly across category/liquidity if given; exact match earns full share, liquidity above the requested level earns half; no preferences given = full 10 |

The return floor (0.2, not 0.0) exists because min-max normalization always drives the worst
performer in the eligible set to zero, regardless of how good that worst performer actually is —
every candidate here already cleared the user's minimum-return bar, so relative ranking
shouldn't zero one out entirely for simply being last.

Weight reasoning: return is weighted highest because it's what people are actually comparing
products on. risk_fit is close behind — recommending something riskier than requested is the
worst failure mode a ranking can have, worse than a slightly lower return. tenure_fit matters
less, since a tenure mismatch is inconvenient rather than a suitability problem. budget rewards
products that leave room to diversify, but that's secondary to whether the product itself fits.
preference is weighted lowest because category/liquidity are optional filters the user may not
even set — a tiebreaker, not a core signal.

The budget formula isn't what the brief originally described. It referenced a `max_investment`
field to reward higher investment ceilings, but that field doesn't exist anywhere in the schema
or data, so budget is instead `1 - (min_investment / investment_amount)`: a lower entry bar
leaves more of the stated amount free for diversification elsewhere. Simpler, and it doesn't
depend on a field that's never populated.

## API and error handling

`POST /opportunities/search/` is the only real endpoint; `GET /health/` and
`GET /validation-report/` are read-only diagnostics. Validation errors (bad risk, zero
investment, unknown fields, malformed JSON) return HTTP 400 as
`{"error": "Invalid request", "details": [{"field": ..., "message": ...}]}`. This is a
deliberate difference from FastAPI, which would use 422 for the same cases — DRF's convention is
400, and there's no real benefit to fighting the framework on it.

Anything unhandled (a bug, not a validation problem) returns HTTP 500 with just
`{"error": "Internal server error"}`. The exception and traceback are logged server-side via
`logger.exception()`, never included in the response — checked manually by forcing an exception
in a view and confirming the response body had no exception detail in it.

A search with no matches still returns HTTP 200 —
`{"count": 0, "results": [], "rejection_summary": {...}}` — with per-rule failure counts, so a
caller can tell why nothing matched instead of getting an empty list with no explanation.

## Known limitations

- `max_investment` is not populated anywhere in this dataset. The amount rule and budget formula
  both assume it's absent; there's no code path exercising "amount above the max" because no
  record has one.
- `OPP002` and `OPP005` are permanently excluded because their risk labels don't match the fixed
  5-label scale. If those were meant to be recoverable typos, that's a policy decision, not
  something the validator should guess at silently.
- The dataset has 31 raw rows, not the 30 the brief's prose describes, because of the deliberate
  duplicate id. Tests and this note both say 31 to match what's actually in the file.
