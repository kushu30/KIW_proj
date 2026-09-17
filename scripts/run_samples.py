import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.data_loader import load_opportunities, load_sample_queries
from core.domain import LiquidityLevel, RiskLevel, SearchQuery
from core.eligibility import filter_eligible
from core.ranking import rank
from core.validator import validate_dataset

OUTPUT_DIR = Path(__file__).resolve().parent.parent / "sample_output"


def _build_query(row: dict) -> SearchQuery:
    return SearchQuery(
        investment_amount=float(row["investment_amount"]),
        risk=RiskLevel.from_label(row["risk"]),
        tenure_months=int(row["tenure_months"]),
        minimum_return=float(row["minimum_return"]) if row["minimum_return"] else None,
        category=row["category"] or None,
        liquidity=LiquidityLevel.from_label(row["liquidity"]) if row["liquidity"] else None,
    )


def main() -> None:
    opportunities, report = validate_dataset(load_opportunities())
    issues = [{"record_id": i.record_id, "field": i.field, "severity": i.severity.value, "message": i.message, "raw_value": i.raw_value} for i in report.issues]
    report_json = {"total": report.total, "valid_count": report.valid_count, "invalid_count": report.invalid_count, "issues": issues}
    (OUTPUT_DIR / "validation_report.json").write_text(json.dumps(report_json, indent=2))

    summary = []
    for row in load_sample_queries():
        query_id = row["query_id"]
        try:
            query = _build_query(row)
            results, rejection_summary = filter_eligible(opportunities, query)
            ranked = rank(results, query)
            output = {"count": len(ranked), "results": ranked} if ranked else {"count": 0, "results": [], "rejection_summary": rejection_summary}
            summary.append((query_id, len(ranked), ranked[0]["score"] if ranked else "-", ""))
        except (ValueError, KeyError) as exc:
            output = {"query_id": query_id, "error": str(exc)}
            summary.append((query_id, 0, "-", str(exc)))
        (OUTPUT_DIR / f"query_{query_id}.json").write_text(json.dumps(output, indent=2))

    print(f"{'query':<8}{'count':<8}{'top_score':<12}error")
    for query_id, count, top_score, error in summary:
        print(f"{query_id:<8}{count:<8}{str(top_score):<12}{error}")


if __name__ == "__main__":
    main()
