# Project: K&I Wealth Tech — Python Engineering Assessment

## What this is
A take-home assessment (50 marks). Django + DRF app that ingests a dataset of 30 financial
opportunity records, validates and normalizes it, applies eligibility rules, ranks matches,
and exposes `POST /opportunities/search/`.

## Marking scheme
| Section | Marks | Requirement |
|---|---|---|
| Data processing & validation | 10 | Read dataset programmatically, normalize money to INR, normalize tenure to min/max months, standardize risk terms, parse return values/ranges, detect missing/invalid fields, detect duplicate IDs, REPORT problems instead of silently dropping |
| Eligibility engine | 12 | Inputs: investment amount, risk, tenure, minimum return, optional category + liquidity. Documented rules. Explicit no-match result |
| Ranking engine | 8 | Transparent scoring: risk fit, tenure fit, return, budget efficiency, preferences. Must be justified |
| REST API | 10 | `POST /opportunities/search/`, response with count + structured results (id, name, score, reasons, attributes) |
| Error handling | 5 | Negative/zero investment, invalid risk or tenure, malformed request, missing fields, no matches, invalid source records |
| Code quality & testing | 5 | Readable modular code, layers separated, meaningful exceptions, requirements.txt, automated tests |

Deliverables: source, README.md (install + run from clean env), requirements.txt,
TECHNICAL_NOTE.md (1–2 pages), tests, dataset, sample output.
Hard rule: do NOT hard-code answers to the supplied sample queries.

## Dataset
`data/opportunities.csv` (30 records, deliberate format variation, one duplicate ID)
`data/sample_queries.csv` (dev scenarios)
`data/schema.json` — normalized target schema:

opportunity_id: string
name: string
provider: string
category: string
minimum_investment_inr: integer
tenure_min_months: integer
tenure_max_months: integer
risk: Low|Low-Moderate|Moderate|Moderate-High|High
expected_return_min_pct: number|null
expected_return_max_pct: number|null
liquidity: High|Medium|Low

Never modify files in `data/`.

## Tech stack (fixed)
Python 3.11+, Django 5.x, djangorestframework, pytest, pytest-django.
No database. No Django ORM models. No migrations. Dataset loaded once at startup, held in memory.

## Structure (fixed)

manage.py
config/ settings.py, urls.py, wsgi.py
opportunities/ Django app — API layer ONLY
apps.py loads + validates dataset in ready()
store.py module-level singleton: opportunities + validation report
serializers.py
views.py
exception_handlers.py
urls.py
core/ pure Python — NO Django imports anywhere
domain.py enums + dataclasses
exceptions.py
data_loader.py
validator.py
eligibility.py
ranking.py
tests/ test_validator.py, test_eligibility.py, test_ranking.py, test_api.py
scripts/run_samples.py
data/ original dataset, untouched
sample_output/

The brief suggested `src/api.py`, `src/models.py` etc. We deviate for Django conventions
(`models.py` means ORM models in Django). TECHNICAL_NOTE.md must include a mapping table
explaining this.

## Domain scales (fixed)
Risk, ordinal: LOW=1, LOW_MODERATE=2, MODERATE=3, MODERATE_HIGH=4, HIGH=5
Liquidity, ordinal: LOW=1, MEDIUM=2, HIGH=3
Tenure: `(min_months, max_months)`; `max_months=None` means open-ended
Return: `(return_min, return_max)` in % p.a. Non-numeric (e.g. "market-linked") means
`return_supported=False` and both None

## Eligibility rules (all must pass)
| Rule | Logic |
|---|---|
| amount | `investment_amount >= min_investment` (and `<= max_investment` if present) |
| risk | `opportunity.risk <= user.risk` |
| tenure | `min_months <= tenure_months <= max_months` (skip upper check if max is None) |
| minimum_return | only if given: `return_supported AND return_min >= minimum_return`. Uses return_min because promising the upper bound is misleading |
| category | only if given: case-insensitive exact match |
| liquidity | only if given: `opportunity.liquidity >= requested` (treated as a minimum) |

Each rule is its own function returning `(passed: bool, reason: str)`.
Optional rules return `(True, "no preference given")` when the field is None.
All rules run even after one fails, so the rejection summary is complete.
No match: HTTP 200, `{"count": 0, "results": [], "rejection_summary": {"risk": 5, ...}}`.

## Ranking (0–100, 2 decimals)
Weights as named constants: return 30, risk_fit 25, tenure_fit 20, budget 15, preference 10.

| Component | Formula (returns 0.0–1.0) |
|---|---|
| return | min-max normalize `return_min` across eligible set with supported return. All equal -> 1.0. Unsupported -> 0.5 |
| risk_fit | `diff = user.risk - opp.risk`; `1.0 - diff*0.15`, floored at 0.3 |
| tenure_fit | max is None -> 0.8. Else `mid=(min+max)/2`, `half=(max-min)/2`; if half==0 -> 1.0, else `1 - 0.5*abs(tenure-mid)/half` |
| budget | `max_investment` exists and amount > it -> `max_investment/amount`, else 1.0 |
| preference | split equally across preferences given. Exact category match earns its share; exact liquidity match earns its share, higher-than-requested earns half. No preferences -> full 10 |

Breakdown reports POINTS per component (value × weight). Sort by score desc, then id asc.

## Validation severity
- `error`: record excluded from search (missing/invalid id, name, min_investment, risk, tenure; or duplicate id — keep FIRST occurrence)
- `warning`: record still usable (e.g. unparseable return -> `return_supported=False`)
`ValidationIssue`: record_id, field, severity, message, raw_value.
Every excluded record must have at least one error issue. Never drop silently.

## API details
- `POST /opportunities/search/`, `GET /health/`, `GET /validation-report/`
- `SearchRequestSerializer`: investment_amount (float, > 0), risk (case-insensitive against
  the 5 labels), tenure_months (int, > 0, <= 600), minimum_return (optional, >= 0),
  category + liquidity (optional). Override `validate()` to reject unknown keys by comparing
  `initial_data` keys against `self.fields`.
- Serializer output is a `core.domain.SearchQuery` dataclass, so `core/` never sees DRF objects.
- Custom exception handler wired via `REST_FRAMEWORK['EXCEPTION_HANDLER']`:
  ValidationError -> 400 `{"error": "Invalid request", "details": [{"field":..., "message":...}]}`;
  ParseError (malformed JSON) -> 400, same shape; unhandled Exception -> 500
  `{"error": "Internal server error"}` with the traceback logged, never leaked.
  DRF uses 400 for validation where FastAPI would use 422 — intentional, note it.
- `apps.py` `ready()` calls `store.initialize()`; must be idempotent (Django autoreload calls
  it twice). On `DatasetLoadError`, log clearly and re-raise so startup fails loudly.
- `settings.py` minimal: no admin, auth, sessions, or migrations. Just `rest_framework` + the app.
- LOGGING at INFO: valid/invalid counts at startup, result count per search.

## Code style (always)
- Small pure functions. No classes where a function works. No clever abstractions.
- Type hints everywhere. No inline comments. One-line docstrings on public functions only.
- `core/` must never import Django or DRF.
- After finishing a step, explain in plain bullets what each function does and why —
  written so I can defend it in an interview. Plain direct language, no academic phrasing.

## Workflow rules
- Do ONLY the step I give you. Do not jump ahead to later steps.
- Run the tests you write and show me the output. Don't claim something passes without running it.
- If a decision in this file conflicts with what the data actually contains, stop and tell me
  instead of silently working around it.