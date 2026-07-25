from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.notifications.services import NotificationService
from apps.common.exceptions import NotFoundError
from apps.api.serializers import NotificationSerializer
from apps.common.response import success_response


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def notification_list(request):
    page = int(request.query_params.get("page", 1))
    result = NotificationService.list_for_user(request.user, page=page)
    return success_response(data={
        "count": result["count"],
        "results": NotificationSerializer(result["results"], many=True).data,
    })


@api_view(["PATCH"])
@permission_classes([IsAuthenticated])
def mark_read(request, pk):
    try:
        notif = NotificationService.mark_read(request.user, pk)
    except NotFoundError:
        return Response(status=status.HTTP_404_NOT_FOUND)
    return Response(NotificationSerializer(notif).data)
