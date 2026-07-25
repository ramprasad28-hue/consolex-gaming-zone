from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.bookings.services import BookingService
from apps.bookings.pricing import RATE_PER_PLAYER_HOUR
from apps.common.exceptions import ServiceError
from apps.common.response import success_response, error_response, paginated_response
from apps.api.serializers import BookingSerializer, BookingCreateSerializer


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def booking_list(request):
    status_filter = request.query_params.get("status")
    qs = BookingService.list_for_user(request.user, status_filter)
    return paginated_response(qs, BookingSerializer, request)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def booking_create(request):
    ser = BookingCreateSerializer(data=request.data)
    ser.is_valid(raise_exception=True)
    data = ser.validated_data

    try:
        booking = BookingService.create_booking(
            user=request.user,
            console_id=data["game_console"],
            booking_date=data["booking_date"],
            start_time=data["start_time"],
            duration_hours=data["duration_hours"],
            number_of_players=data["number_of_players"],
        )
    except ServiceError as e:
        return error_response(str(e), e.status_code if hasattr(e, "status_code") else status.HTTP_400_BAD_REQUEST)

    return Response(BookingSerializer(booking).data, status=status.HTTP_201_CREATED)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def booking_detail(request, pk):
    try:
        booking = BookingService.get_for_user(request.user, pk)
    except ServiceError as e:
        return Response(status=status.HTTP_404_NOT_FOUND)
    return Response(BookingSerializer(booking).data)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def booking_cancel(request, pk):
    try:
        booking = BookingService.cancel_booking(request.user, pk)
    except ServiceError as e:
        return error_response(str(e), e.status_code if hasattr(e, "status_code") else status.HTTP_400_BAD_REQUEST)
    return Response(BookingSerializer(booking).data)
