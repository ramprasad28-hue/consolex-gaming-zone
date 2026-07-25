from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.users.services import UserService


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def dashboard(request):
    data = UserService.get_api_dashboard_data(request.user)
    return Response(data)
