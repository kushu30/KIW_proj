# K&I Wealth Tech — opportunity matching API

Django + DRF service that loads a CSV of 31 financial opportunity records, validates and
normalizes them, and matches/ranks them against a user's investment criteria.

No database. Everything is read from `data/opportunities.csv` once at startup and held in memory.

## Requirements

- Python 3.11+ (built and tested on 3.13)
- See `requirements.txt` for pinned package versions (Django, djangorestframework, pytest,
  pytest-django)

## Setup (clean environment)

```bash
python3 -m venv .venv
source .venv/bin/activate        # .venv\Scripts\activate on Windows
pip install -r requirements.txt
```

## Running the tests

```bash
python -m pytest
```

56 tests, no database needed. `pytest.ini` points pytest at `config.settings`.

## Running the server

```bash
python manage.py runserver
```

On startup you'll see a log line like `dataset loaded: 28 valid, 3 invalid` — that's the
validator running against `data/opportunities.csv`. 3 records are excluded on purpose (two have
risk labels outside the fixed 5-label scale, one is a deliberate duplicate id); see
`TECHNICAL_NOTE.md` for details.

### Endpoints

- `POST /opportunities/search/` — the main endpoint. Body:
  ```json
  {
    "investment_amount": 50000,
    "risk": "Low",
    "tenure_months": 12,
    "minimum_return": 6,
    "category": "Debt",
    "liquidity": "High"
  }
  ```
  `minimum_return`, `category`, and `liquidity` are optional. `risk` is case-insensitive.
- `GET /health/` — returns `{"status": "ok"}`.
- `GET /validation-report/` — the full list of records excluded or flagged during validation,
  with reasons.

## Generating sample output

```bash
python scripts/run_samples.py
```

Runs every row in `data/sample_queries.csv` through the same eligibility/ranking code the API
uses, and writes one JSON file per query into `sample_output/`, plus
`sample_output/validation_report.json`.

## Project layout

`core/` is plain Python with no Django imports — data loading, validation, eligibility, and
ranking. `opportunities/` is the Django app: it only wires `core/` up to HTTP (serializers,
views, the exception handler). See `TECHNICAL_NOTE.md` for why this differs from the layout the
original brief suggested.
