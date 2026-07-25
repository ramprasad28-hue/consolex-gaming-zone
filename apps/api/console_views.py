from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status as http_status
from apps.games.models import GameConsole
from .serializers import GameConsoleSerializer


@api_view(["GET"])
@permission_classes([AllowAny])
def console_list(request):
    consoles = GameConsole.objects.filter(is_active=True)
    return Response(GameConsoleSerializer(consoles, many=True).data)


@api_view(["GET"])
@permission_classes([AllowAny])
def console_detail(request, pk):
    try:
        console = GameConsole.objects.get(pk=pk, is_active=True)
    except GameConsole.DoesNotExist:
        return Response(status=http_status.HTTP_404_NOT_FOUND)
    return Response(GameConsoleSerializer(console).data)
