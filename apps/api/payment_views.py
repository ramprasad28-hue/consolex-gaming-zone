from rest_framework import status
from rest_framework.decorators import api_view, permission_classes, throttle_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import UserRateThrottle

from apps.payments.services import PaymentService
from apps.common.exceptions import ServiceError
from apps.common.response import error_response
from apps.api.serializers import PaymentSerializer


class PaymentVerifyThrottle(UserRateThrottle):
    rate = "20/minute"


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def create_order(request):
    booking_id = request.data.get("booking_id")
    if not booking_id:
        return error_response("booking_id is required.")

    try:
        result = PaymentService.create_order(request.user, booking_id)
    except ServiceError as e:
        return error_response(str(e), e.status_code)

    return Response(result)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
@throttle_classes([PaymentVerifyThrottle])
def verify_payment(request):
    payment_id = request.data.get("payment_id")
    if not payment_id:
        return error_response("payment_id is required.")

    try:
        result = PaymentService.verify_payment(
            user=request.user,
            payment_id=payment_id,
            razorpay_order_id=request.data.get("razorpay_order_id", ""),
            razorpay_payment_id=request.data.get("razorpay_payment_id", ""),
            razorpay_signature=request.data.get("razorpay_signature", ""),
        )
    except ServiceError as e:
        return error_response(str(e), e.status_code)

    return Response(result)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def receipt(request, booking_id):
    try:
        data = PaymentService.get_receipt(request.user, booking_id)
    except ServiceError as e:
        return Response(status=status.HTTP_404_NOT_FOUND)
    return Response(data)
