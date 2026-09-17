import logging

from rest_framework.decorators import api_view
from rest_framework.response import Response

from core.eligibility import filter_eligible
from core.ranking import rank
from opportunities import store
from opportunities.serializers import SearchRequestSerializer

logger = logging.getLogger(__name__)


@api_view(["POST"])
def search(request):
    serializer = SearchRequestSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    query = serializer.to_search_query()

    results, rejection_summary = filter_eligible(store.get_opportunities(), query)
    ranked = rank(results, query)

    logger.info("search returned %d result(s)", len(ranked))

    if not ranked:
        return Response({"count": 0, "results": [], "rejection_summary": rejection_summary})
    return Response({"count": len(ranked), "results": ranked})


@api_view(["GET"])
def health(request):
    return Response({"status": "ok"})


@api_view(["GET"])
def validation_report(request):
    report = store.get_report()
    return Response(
        {
            "total": report.total,
            "valid_count": report.valid_count,
            "invalid_count": report.invalid_count,
            "issues": [
                {
                    "record_id": issue.record_id,
                    "field": issue.field,
                    "severity": issue.severity.value,
                    "message": issue.message,
                    "raw_value": issue.raw_value,
                }
                for issue in report.issues
            ],
        }
    )
