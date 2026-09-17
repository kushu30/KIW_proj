from rest_framework.views import exception_handler


def custom_exception_handler(exc, context):
    """Delegate to DRF's default handler; response shaping lands in a later step."""
    return exception_handler(exc, context)
