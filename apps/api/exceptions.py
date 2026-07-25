"""
DRF custom exception handler for CONSOLEX.

Translates ServiceError subclasses and DRF errors into consistent JSON shape:
{
    "success": false,
    "error": "Human-readable message",
    "code": "ERROR_CODE",
    "errors": { ... }  // optional field-level errors
}
"""
import logging

from rest_framework.views import exception_handler
from rest_framework import status as http_status

from apps.common.exceptions import ServiceError

logger = logging.getLogger("apps.api")


def custom_exception_handler(exc, context):
    """
    Catch ServiceError before DRF even looks at it, then delegate
    everything else to the default handler.
    """
    if isinstance(exc, ServiceError):
        payload = {
            "success": False,
            "error": exc.message,
            "code": exc.code,
        }
        if exc.extra:
            payload["errors"] = exc.extra
        from rest_framework.response import Response
        return Response(payload, status=exc.status_code)

    # Let DRF handle its own ValidationError, PermissionDenied, etc.
    response = exception_handler(exc, context)

    if response is not None:
        # Normalise DRF errors into our shape
        data = response.data if isinstance(response.data, dict) else {"detail": response.data}
        response.data = {
            "success": False,
            "error": data.get("detail", "Validation error."),
            "code": exc.__class__.__name__,
            "errors": {k: v for k, v in data.items() if k != "detail"},
        }
    else:
        # Unhandled exception → 500
        logger.exception("Unhandled exception in API view")
        from rest_framework.response import Response
        return Response(
            {"success": False, "error": "An unexpected error occurred.", "code": "InternalServerError"},
            status=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    return response
