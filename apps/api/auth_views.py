from django.contrib.auth import login, logout, get_user_model
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from apps.api.serializers import UserSerializer, UserRegisterSerializer, UserLoginSerializer
from apps.users.services import UserService
from apps.common.exceptions import ServiceError

User = get_user_model()


@api_view(["POST"])
@permission_classes([AllowAny])
def register(request):
    ser = UserRegisterSerializer(data=request.data)
    ser.is_valid(raise_exception=True)
    data = ser.validated_data

    try:
        user = UserService.register(
            email=data["email"],
            password=data["password"],
            first_name=data.get("first_name", ""),
            last_name=data.get("last_name", ""),
        )
    except ServiceError as e:
        return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    login(request, user)
    return Response(UserSerializer(user).data, status=status.HTTP_201_CREATED)


@api_view(["POST"])
@permission_classes([AllowAny])
def login_view(request):
    ser = UserLoginSerializer(data=request.data)
    ser.is_valid(raise_exception=True)
    data = ser.validated_data

    try:
        user = UserService.login(request, data["email"], data["password"])
    except ServiceError as e:
        return Response({"error": str(e)}, status=status.HTTP_401_UNAUTHORIZED)

    login(request, user)
    return Response(UserSerializer(user).data)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def logout_view(request):
    logout(request)
    return Response(status=status.HTTP_204_NO_CONTENT)


@api_view(["GET", "PATCH"])
@permission_classes([IsAuthenticated])
def me(request):
    if request.method == "GET":
        return Response(UserSerializer(request.user).data)

    ser = UserSerializer(request.user, data=request.data, partial=True)
    ser.is_valid(raise_exception=True)
    ser.save()
    return Response(ser.data)
