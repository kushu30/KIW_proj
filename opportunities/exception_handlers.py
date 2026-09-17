import logging

from rest_framework.exceptions import ParseError, ValidationError
from rest_framework.response import Response
from rest_framework.views import exception_handler as drf_exception_handler

logger = logging.getLogger(__name__)


def _flatten(detail, field: str = "non_field_errors") -> list[dict]:
    if isinstance(detail, dict):
        return [item for key, value in detail.items() for item in _flatten(value, field=key)]
    if isinstance(detail, list):
        return [item for value in detail for item in _flatten(value, field=field)]
    return [{"field": field, "message": str(detail)}]


def custom_exception_handler(exc, context):
    """ValidationError/ParseError -> 400 {error, details}; anything else -> 500, traceback logged only."""
    if isinstance(exc, ValidationError):
        return Response({"error": "Invalid request", "details": _flatten(exc.detail)}, status=400)
    if isinstance(exc, ParseError):
        return Response({"error": "Invalid request", "details": [{"field": "body", "message": str(exc.detail)}]}, status=400)

    response = drf_exception_handler(exc, context)
    if response is not None:
        return response

    logger.exception("unhandled exception in %s", context["view"])
    return Response({"error": "Internal server error"}, status=500)
