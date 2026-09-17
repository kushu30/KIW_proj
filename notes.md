# Data Analysis Notes — opportunities.csv / sample_queries.csv / schema

Files actually present in `data/`: `opportunities.csv`, `sample_queries.csv`, `data_schema.json`,
`README_DATA.md`. Note: CLAUDE.md and the task prompt both say `data/schema.json` — the actual
filename is `data/data_schema.json`. Minor naming mismatch, flag it, use the real filename.

## 1. Actual CSV columns vs schema.json

**Raw `opportunities.csv` header (9 cols):**
`opportunity_id, name, provider, category, minimum_investment, tenure, risk, expected_return, liquidity`

**`data_schema.json` target (11 fields):**
`opportunity_id, name, provider, category, minimum_investment_inr, tenure_min_months, tenure_max_months, risk, expected_return_min_pct, expected_return_max_pct, liquidity`

Differences:
- `minimum_investment` (1 raw col, mixed free-text money format) → `minimum_investment_inr` (1 schema field, integer). Straightforward rename + parse, 1:1.
- `tenure` (1 raw col, free text) → splits into **two** schema fields: `tenure_min_months` + `tenure_max_months`. 1:2 split, requires parsing.
- `expected_return` (1 raw col, free text) → splits into **two** schema fields: `expected_return_min_pct` + `expected_return_max_pct`. 1:2 split, requires parsing.
- `risk`, `liquidity`, `category`, `provider`, `name`, `opportunity_id` are 1:1 in name but raw values need normalizing (risk especially — see §2).
- **No `maximum_investment` column exists anywhere** — not in the raw CSV, not in `data_schema.json`. But CLAUDE.md's eligibility rule table and ranking "budget" component both reference `max_investment` as an optional per-opportunity field (`<= max_investment if present`, `budget = max_investment/amount if amount > max_investment`). **This is a direct conflict — see "Flag" section below.**

## 2. Distinct raw formats found (real quoted values)

### minimum_investment
| Pattern | Example(s) |
|---|---|
| Plain digits, no marker | `25000` (OPP003), `250000` (OPP007), `100000` (OPP012) |
| `₹` + Indian-grouped digits (2,2,3 grouping) | `₹1,00,000` (OPP001), `₹50,000` (OPP004), `₹3,00,000` (OPP008), `₹5,00,000` (OPP024) |
| `Rs. ` prefix + integer + `lakh` | `Rs. 2 lakh` (OPP002) — only "Rs." occurrence in the file |
| `₹` + integer + `lakh` | `₹5 lakh` (OPP006), `₹10 lakh` (OPP016), `₹3 lakh` (OPP019), `₹1 lakh` (OPP021, OPP029), `₹2 lakh` (OPP025) |
| `₹` + decimal + `lakh` | `₹1.5 lakh` (OPP009), `₹1.25 lakh` (OPP014), `₹2.5 lakh` (OPP028) |

Currency markers seen: `₹` symbol, `Rs.` abbreviation, and no marker at all (bare integer, implied INR). No `$`, no ISO codes.

### maximum_investment
Column does not exist. Zero raw values of any format.

### tenure
| Pattern | Example(s) |
|---|---|
| `<N> months` (single, fixed) | `18 months` (OPP001), `12 months` (OPP012) |
| `<N>-<M> months` (range) | `12-24 months` (OPP003), `6-12 months` (OPP010), `9-15 months` (OPP021) |
| `<N> years` (different unit!) | `3 years` (OPP004) — only non-month unit in the file |
| `<N> months+` (open-ended) | `24 months+` (OPP011), `36 months+` (OPP019) |

### risk
| Raw value | Matches schema enum? | Opportunities |
|---|---|---|
| `Low` | yes | OPP007, OPP012, OPP017, OPP026 |
| `Low-Moderate` | yes | OPP003, OPP015, OPP023, OPP030 |
| `Moderate` | yes | OPP001, OPP008, OPP010, OPP020, OPP025, OPP029 |
| `Moderate-High` | yes | OPP006, OPP016, OPP018, OPP021, OPP028 |
| `High` | yes | OPP004, OPP009, OPP013, OPP014, OPP019, OPP022, OPP024, OPP027 |
| `Medium` | **no** | OPP002 — not one of the 5 schema labels |
| `Moderately High` | **no** | OPP005 — different spelling/word-order from `Moderate-High` |

### expected_return
| Pattern | Example(s) |
|---|---|
| `<N.N>% p.a.` (single, one decimal) | `9.2% p.a.` (OPP001) |
| `<N>% p.a.` (single, no decimal) | `15% p.a.` (OPP022) |
| `<N>-<M>% p.a.` (range, integers) | `14-18% p.a.` (OPP004), `11-15% p.a.` (OPP019) |
| `<N.N>-<N.N>% p.a.` (range, decimals) | `10.1-11.0% p.a.` (OPP008), `9.8-12.2% p.a.` (OPP010) |
| Non-numeric text | `Variable` (OPP014) — no `%`, no number at all |

### liquidity
Only three raw values seen, all already matching the schema enum exactly: `High`, `Medium`, `Low`. No variants, no case issues. No normalization work needed here — the one field with no format variation.

### category
Free text, no enum in schema. 20 distinct values across 30 rows (some repeat: `Equity` x4, `Private Credit` x3, `Mutual Fund`/`Invoice Financing`/`Debt`/`Real Estate Debt`/`Corporate Debt` x2 each). All are clean title-case strings, no formatting variants observed (unlike risk/tenure/return). Sample queries use `Debt` and `Equity`, both of which appear verbatim in the raw data.

## 3. Missing / invalid / duplicate records (by row number, 1-indexed incl. header)

Checked programmatically: **no blank/empty fields and no ragged rows** anywhere in the file (all 30+1 rows have all 9 columns populated).

- **Row 32 — `OPP030` (duplicate id)**: row 31 (`OPP030`, "Dawn Short Term Credit") and row 32 (`OPP030`, "Dawn Short Term Credit - Duplicate") share the same `opportunity_id`. Per CLAUDE.md, keep first occurrence (row 31) as valid, row 32 excluded as `error` (duplicate id).
- **Row 3 — `OPP002` risk = `Medium`**: not in schema's 5-label risk enum (`Low|Low-Moderate|Moderate|Moderate-High|High`). Under CLAUDE.md's severity rules, invalid risk is `error`-severity (record excluded) *unless* it's treated as a normalizable synonym — see assumptions.
- **Row 6 — `OPP005` risk = `Moderately High`**: same issue, not in the enum as spelled (schema uses `Moderate-High`). Likely intended synonym.
- **Row 15 — `OPP014` expected_return = `Variable`**: non-numeric return. Per CLAUDE.md this is `warning`-severity only (`return_supported=False`, both min/max set to `null`), record stays usable — not an exclusion.
- **Row 5 — `OPP004` tenure = `3 years`**: not a parsing error, but the only non-month unit in the file; must be converted to months (36) rather than misread as "3 months." Worth flagging since a naive regex for `months` would silently miss/mishandle it.

No records have missing id, name, minimum_investment, or tenure. No other invalid values found in category/liquidity.

## 4. Raw column → normalized field mapping

| Raw column | Normalized field(s) | Transform needed |
|---|---|---|
| `opportunity_id` | `opportunity_id` | trim; dedupe (keep first) |
| `name` | `name` | trim |
| `provider` | `provider` | trim |
| `category` | `category` | trim; case-insensitive compare downstream, store as-is |
| `minimum_investment` | `minimum_investment_inr` | strip `₹`/`Rs.` markers, strip commas, expand `lakh` (×100,000, handles decimals like `1.5 lakh`→150000), cast to int |
| `tenure` | `tenure_min_months`, `tenure_max_months` | parse single value vs `N-M` range vs `N+` open-ended; convert `years`→`months` (×12); `max=None` when open-ended or single value with no explicit max (single fixed value ⇒ min=max=N) |
| `risk` | `risk` | map raw string to one of the 5 canonical labels (needs a synonym table for `Medium`, `Moderately High`) |
| `expected_return` | `expected_return_min_pct`, `expected_return_max_pct` | strip `% p.a.`, parse single value (min=max) vs `N-M` range; non-numeric (`Variable`) ⇒ both `None`, `return_supported=False` |
| `liquidity` | `liquidity` | trim only, already canonical |
| *(none)* | `maximum_investment` (used by CLAUDE.md rules) | **no source column — cannot be populated from this dataset** |

## 5. Assumptions needed + recommended decision

1. **`risk = "Medium"` (OPP002)** — is it a typo/synonym for `Moderate`, or an invalid value? → **Recommend: treat as invalid (error, excluded)**, since CLAUDE.md's enum is fixed and "Medium" isn't liquidity-flavored bleed-through worth guessing at; don't silently guess client intent on a scored assessment. (Report the exclusion clearly rather than silently mapping it.)
2. **`risk = "Moderately High"` (OPP005)** — synonym for `Moderate-High`? → **Recommend: also treat as invalid/excluded**, for the same reason as #1 — consistent treatment, no ad hoc synonym table for one-off spellings.
3. **No `max_investment` field exists in data or schema, but CLAUDE.md's eligibility "amount" rule and ranking "budget" component both reference it** → **Recommend: treat `max_investment` as always absent/`None` for every record** (so the amount rule reduces to `investment_amount >= min_investment` only, and budget component is always `1.0`). This is the most literal reading of "if present" / "exists" — it's optional and this dataset never supplies it. Flagged explicitly to the user below since it materially simplifies two scored components.
4. **Tenure `"24 months+"` (open-ended, OPP011/OPP019)** — is `min=24, max=None`, or `min=24, max=24` capped? → **Recommend: `min=24, max=None`** (open-ended), matching the `max_months=None` convention CLAUDE.md already defines for open-ended tenure.
5. **Tenure single fixed value (e.g. `"18 months"`)** — is min=max=18, or is it actually open-ended too? → **Recommend: `min=max=18`** (closed, single point), reserving `max=None` strictly for the explicit `+` suffix.
6. **`expected_return = "Variable"` (OPP014)** — confirmed by CLAUDE.md itself as the documented case (`return_supported=False`), no assumption needed, just confirming implementation matches the rule.
7. **Duplicate `OPP030`** — CLAUDE.md says keep first occurrence. → **Recommend: keep row 31 (name "Dawn Short Term Credit"), exclude row 32 as error**, exactly per the documented rule — no assumption gap here either, just confirming.
8. **Currency assumption** — all values are implicitly INR (`₹`, `Rs.`, or bare number) → **Recommend: treat every value as INR**, no FX conversion needed since schema target field is `minimum_investment_inr` and no other currency ever appears.

## 6. What each sample query asks (no answers)

- **Q001**: opportunities eligible for a ₹200,000 investment, Moderate risk tolerance, 24-month tenure, minimum return of 9%, category = Debt, liquidity = Medium.
- **Q002**: opportunities eligible for a ₹50,000 investment, Low risk tolerance, 12-month tenure, no minimum return, no category, liquidity = High.
- **Q003**: opportunities eligible for a ₹100,000 investment, High risk tolerance, 36-month tenure, minimum return of 12%, category = Equity, liquidity = Low.
- **Q004**: opportunities eligible for a ₹80,000 investment, Moderate risk tolerance, 18-month tenure, no minimum return, no category, liquidity = High.
- **Q005**: opportunities eligible for a ₹300,000 investment, High risk tolerance, 36-month tenure, minimum return of 11%, category = Equity, liquidity = Low.
- **Q006**: opportunities eligible for a ₹250,000 investment, Moderate risk tolerance, 24-month tenure, minimum return of 9%, no category, liquidity = Medium.

## Flags — where the data makes a CLAUDE.md rule impossible as literally written

1. **`max_investment` does not exist anywhere** (not in `opportunities.csv`, not in `data_schema.json`), but CLAUDE.md's eligibility "amount" rule and ranking "budget" component both branch on its presence. As written these rules are *vacuously* satisfiable (the "if present"/"exists" branch never fires with this dataset) but the code will need to implement the dead branch anyway since CLAUDE.md treats it as a real, sometimes-present field. Confirm this is expected before writing eligibility/ranking code, since it means the budget-efficiency ranking component will always evaluate to `1.0` for every real record.
2. **File path mismatch**: CLAUDE.md and this task both say `data/schema.json`; the real file is `data/data_schema.json`. Cosmetic, but any code/doc referencing the literal path needs the corrected name.
3. **Two risk values (`Medium`, `Moderately High`) fall outside the fixed 5-label enum.** CLAUDE.md's severity table implies invalid risk is `error`-severity → exclusion, with no synonym-mapping step defined anywhere in CLAUDE.md. If the intent was actually for these to be recoverable synonyms, that step needs to be explicitly added to CLAUDE.md's validation rules before coding, otherwise 2 of 30 records (OPP002, OPP005) get silently lost from every future query.
