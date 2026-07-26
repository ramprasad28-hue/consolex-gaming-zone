# apps/memberships/views.py
import logging

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.views.decorators.csrf import csrf_exempt

import json

from apps.memberships.services import MembershipService
from apps.bookings.pricing import (
    player_hourly_rate,
    RATE_PER_PLAYER_HOUR,
    RATE_PER_PLAYER_HOUR_WEEKEND,
)
from apps.common.exceptions import ServiceError
from datetime import date
import json

logger = logging.getLogger("apps.memberships")


def plan_list(request):
    plans = MembershipService.list_plans()
    payg_2h_weekday = player_hourly_rate(2, date(2026, 1, 5)) * 2
    rates = {
        "weekday": {str(k): str(v) for k, v in RATE_PER_PLAYER_HOUR.items()},
        "weekend": {str(k): str(v) for k, v in RATE_PER_PLAYER_HOUR_WEEKEND.items()},
    }
    return render(request, "memberships/plans.html", {
        "plans": plans,
        "payg_2h_weekday": payg_2h_weekday,
        "rates_json": json.dumps(rates),
    })


@login_required
def subscribe(request, plan_id):
    plan = MembershipService.get_plan(plan_id)
    return render(request, "memberships/subscribe_confirm.html", {"plan": plan})


@login_required
def membership_payment_page(request, plan_id):
    plan = MembershipService.get_plan(plan_id)

    try:
        order = MembershipService.create_order(request.user, plan_id)
    except ServiceError as e:
        messages.error(request, str(e))
        return redirect("memberships:plan_list")

    if order.get("demo_mode"):
        MembershipService.verify_payment(
            request.user, order["subscription_id"], "", "", ""
        )
        return redirect("users:dashboard")

    return render(request, "memberships/membership_payment.html", {
        "plan": plan,
        "subscription_id": order["subscription_id"],
        "rp_order_id": order["order_id"],
        "rp_amount": order["amount"],
        "razorpay_key_id": order["key_id"],
    })


@login_required
@transaction.atomic
@csrf_exempt
def verify_membership_payment(request):
    if request.method != "POST":
        return JsonResponse({"success": False, "error": "Invalid request."})

    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"success": False, "error": "Invalid JSON."})

    subscription_id = data.get("subscription_id")
    if not subscription_id:
        return JsonResponse({"success": False, "error": "Missing payment data."})

    try:
        result = MembershipService.verify_payment(
            request.user,
            subscription_id,
            data.get("razorpay_order_id", ""),
            data.get("razorpay_payment_id", ""),
            data.get("razorpay_signature", ""),
        )
        return JsonResponse({"success": True, "redirect": "/users/dashboard/"})
    except ServiceError as e:
        return JsonResponse({"success": False, "error": str(e)})
