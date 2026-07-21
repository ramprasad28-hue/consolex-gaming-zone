# apps/memberships/views.py
import json
from datetime import date

import razorpay
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt

from apps.bookings.pricing import player_hourly_rate
from apps.notifications.models import Notification

from .models import Membership, MembershipSubscription, MembershipPayment


def plan_list(request):
    """Render all active membership plans from the database."""
    plans = Membership.objects.filter(is_active=True)
    payg_2h_weekday = player_hourly_rate(2, date(2026, 1, 5)) * 2
    return render(
        request,
        "memberships/plans.html",
        {"plans": plans, "payg_2h_weekday": payg_2h_weekday},
    )


@login_required
def subscribe(request, plan_id):
    """Show the subscription confirmation page (GET) or start payment (POST)."""
    plan = get_object_or_404(Membership, id=plan_id, is_active=True)
    return render(request, "memberships/subscribe_confirm.html", {"plan": plan})


@login_required
def membership_payment_page(request, plan_id):
    """Create a Razorpay order for the membership plan and render the payment page."""
    plan = get_object_or_404(Membership, id=plan_id, is_active=True)

    # Check for an existing pending subscription+payment and reuse if still valid.
    existing_sub = MembershipSubscription.objects.filter(
        user=request.user,
        plan=plan,
        status=MembershipSubscription.STATUS_PENDING,
    ).first()
    if existing_sub and hasattr(existing_sub, 'payment') and existing_sub.payment.status == MembershipPayment.Status.PENDING:
        subscription = existing_sub
        mpayment = subscription.payment
        rp_order_id = mpayment.razorpay_order_id
    else:
        now = timezone.now()
        subscription = MembershipSubscription.objects.create(
            user=request.user,
            plan=plan,
            status=MembershipSubscription.STATUS_PENDING,
            started_at=now,
            expires_at=now + timezone.timedelta(days=plan.duration_days),
        )
        client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))
        amount = int(plan.price * 100)
        try:
            razorpay_order = client.order.create({
                "amount": amount,
                "currency": "INR",
                "payment_capture": 1,
            })
            rp_order_id = razorpay_order["id"]
        except Exception:
            subscription.delete()
            messages.error(request, "Unable to connect to Razorpay. Please try again.")
            return redirect("memberships:plan_list")

        mpayment = MembershipPayment.objects.create(
            subscription=subscription,
            user=request.user,
            razorpay_order_id=rp_order_id,
            amount=amount,
            status=MembershipPayment.Status.PENDING,
        )

    return render(request, "memberships/membership_payment.html", {
        "plan": plan,
        "subscription": subscription,
        "rp_order_id": rp_order_id,
        "rp_amount": mpayment.amount,
        "razorpay_key_id": settings.RAZORPAY_KEY_ID,
    })


@login_required
@transaction.atomic
def verify_membership_payment(request):
    """Verify Razorpay signature and activate the membership."""
    if request.method != "POST":
        return JsonResponse({"success": False, "error": "Invalid request."})

    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"success": False, "error": "Invalid JSON."})

    payment_id = data.get("razorpay_payment_id")
    order_id = data.get("razorpay_order_id")
    signature = data.get("razorpay_signature")

    if not payment_id or not order_id or not signature:
        return JsonResponse({"success": False, "error": "Missing payment data."})

    mpayment = get_object_or_404(
        MembershipPayment.objects.select_for_update(),
        razorpay_order_id=order_id,
        user=request.user,
    )

    if mpayment.is_successful:
        return JsonResponse({"success": True, "redirect": "/users/dashboard/"})

    client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))
    try:
        client.utility.verify_payment_signature({
            "razorpay_order_id": order_id,
            "razorpay_payment_id": payment_id,
            "razorpay_signature": signature,
        })
    except razorpay.errors.SignatureVerificationError:
        mpayment.status = MembershipPayment.Status.FAILED
        mpayment.razorpay_payment_id = payment_id
        mpayment.save()
        return JsonResponse({"success": False, "error": "Payment verification failed."})

    # Payment successful — activate the subscription.
    mpayment.razorpay_payment_id = payment_id
    mpayment.razorpay_signature = signature
    mpayment.status = MembershipPayment.Status.CAPTURED
    mpayment.save(update_fields=["razorpay_payment_id", "razorpay_signature", "status", "updated_at"])

    subscription = mpayment.subscription
    # Cancel any prior active subscription.
    MembershipSubscription.objects.filter(
        user=request.user, status=MembershipSubscription.STATUS_ACTIVE
    ).update(
        status=MembershipSubscription.STATUS_CANCELLED,
        cancelled_at=timezone.now(),
    )
    subscription.status = MembershipSubscription.STATUS_ACTIVE
    subscription.started_at = timezone.now()
    subscription.expires_at = timezone.now() + timezone.timedelta(days=subscription.plan.duration_days)
    subscription.save(update_fields=["status", "started_at", "expires_at", "updated_at"])

    request.user.membership = subscription.plan
    request.user.save(update_fields=["membership"])

    Notification.objects.create(
        user=request.user,
        message=f"Your {subscription.plan.name} membership is now active!",
    )

    return JsonResponse({"success": True, "redirect": "/users/dashboard/"})
