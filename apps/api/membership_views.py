from rest_framework import status
from rest_framework.decorators import api_view, permission_classes, throttle_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework.throttling import UserRateThrottle

from apps.memberships.services import MembershipService
from apps.common.exceptions import ServiceError
from apps.common.response import error_response
from apps.api.serializers import MembershipPlanSerializer, MembershipSubscriptionSerializer


class MembershipVerifyThrottle(UserRateThrottle):
    rate = "20/minute"


@api_view(["GET"])
@permission_classes([AllowAny])
def plan_list(request):
    plans = MembershipService.list_plans()
    return Response(MembershipPlanSerializer(plans, many=True).data)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def subscription_detail(request):
    sub = MembershipService.get_subscription(request.user)
    if sub is None:
        return Response({"subscription": None})
    return Response({"subscription": MembershipSubscriptionSerializer(sub).data})


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def subscribe(request, plan_id):
    try:
        result = MembershipService.create_order(request.user, plan_id)
    except ServiceError as e:
        return error_response(str(e), e.status_code)
    return Response(result)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
@throttle_classes([MembershipVerifyThrottle])
def verify_payment(request):
    subscription_id = request.data.get("subscription_id")
    if not subscription_id:
        return error_response("subscription_id is required.")

    try:
        result = MembershipService.verify_payment(
            user=request.user,
            subscription_id=subscription_id,
            razorpay_order_id=request.data.get("razorpay_order_id", ""),
            razorpay_payment_id=request.data.get("razorpay_payment_id", ""),
            razorpay_signature=request.data.get("razorpay_signature", ""),
        )
    except ServiceError as e:
        return error_response(str(e), e.status_code)

    return Response(result)
