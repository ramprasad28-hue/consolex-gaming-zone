"""
Consistent API response helpers for CONSOLEX.

Every API endpoint should return responses in a uniform shape so the
frontend (and any third-party consumers) can rely on a single contract.
"""
from rest_framework.response import Response
from rest_framework import status as http_status


def success_response(data=None, message=None, status_code=http_status.HTTP_200_OK):
    """Return a successful API response."""
    payload = {"success": True}
    if message:
        payload["message"] = message
    if data is not None:
        payload["data"] = data
    return Response(payload, status=status_code)


def created_response(data=None, message=None):
    """Return a 201 Created response."""
    return success_response(data=data, message=message, status_code=http_status.HTTP_201_CREATED)


def no_content_response(message=None):
    """Return a 204 No Content response."""
    return success_response(message=message, status_code=http_status.HTTP_204_NO_CONTENT)


def error_response(message, status_code=http_status.HTTP_400_BAD_REQUEST, code=None, errors=None):
    """Return an error API response."""
    payload = {
        "success": False,
        "error": message,
    }
    if code:
        payload["code"] = code
    if errors:
        payload["errors"] = errors
    return Response(payload, status=status_code)


def paginated_response(queryset, serializer_class, request, page_size=20):
    """Return a paginated list response with consistent shape."""
    page = int(request.query_params.get("page", 1))
    total = queryset.count()
    start = (page - 1) * page_size
    items = queryset[start : start + page_size]
    return success_response(data={
        "count": total,
        "page": page,
        "page_size": page_size,
        "total_pages": max(-(-total // page_size), 1) if total else 1,
        "results": serializer_class(items, many=True).data,
    })
