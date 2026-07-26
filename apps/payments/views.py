# apps/payments/views.py
import json
import logging

import razorpay
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.csrf import csrf_exempt

from apps.bookings.models import Booking
from apps.payments.services import PaymentService
from apps.common.exceptions import ServiceError, RazorpayError

logger = logging.getLogger("apps.payments")


@login_required
def payment_page(request, booking_id):
    booking = get_object_or_404(Booking, id=booking_id, user=request.user)

    if booking.status == "confirmed":
        messages.info(request, "Booking already paid.")
        return redirect("users:dashboard")

    try:
        order = PaymentService.create_order(request.user, booking.id)
    except ServiceError as e:
        messages.error(request, str(e))
        return redirect("bookings:booking_form")

    if order.get("demo_mode"):
        # Demo mode: auto-approve and redirect to success
        PaymentService.verify_payment(
            request.user, order["payment_id"], "", "", ""
        )
        return redirect("payments:payment_success", booking_id=booking.id)

    return render(request, "payments/payment_page.html", {
        "booking": booking,
        "total_rupees": booking.total_cost,
        "advance_rupees": booking.advance_amount,
        "balance_rupees": booking.balance_amount,
        "rp_amount": order["amount"],
        "rp_order_id": order["order_id"],
        "razorpay_key_id": settings.RAZORPAY_KEY_ID,
        "db_payment_id": order["payment_id"],
        "booking_id": booking.id,
    })


@login_required
@transaction.atomic
def verify_payment(request):
    if request.method != "POST":
        return JsonResponse({"success": False, "error": "Invalid request."})

    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"success": False, "error": "Invalid JSON."})

    payment_id = data.get("razorpay_payment_id", "")
    order_id = data.get("razorpay_order_id", "")
    signature = data.get("razorpay_signature", "")
    db_payment_id = data.get("payment_id")

    if not db_payment_id:
        return JsonResponse({"success": False, "error": "Missing payment data."})

    try:
        result = PaymentService.verify_payment(
            request.user, db_payment_id, order_id, payment_id, signature
        )
        return JsonResponse({
            "success": True,
            "redirect": f"/payments/success/{data.get('booking_id', '')}/",
        })
    except ServiceError as e:
        return JsonResponse({"success": False, "error": str(e)})


@csrf_exempt
@transaction.atomic
def razorpay_webhook(request):
    """Server-side payment confirmation via Razorpay webhook."""
    if request.method != "POST":
        return HttpResponse("Method not allowed", status=405)

    webhook_secret = settings.RAZORPAY_WEBHOOK_SECRET
    if not webhook_secret:
        return HttpResponse("OK", status=200)

    razorpay_signature = request.headers.get("X-Razorpay-Signature")
    if not razorpay_signature:
        return HttpResponse("Missing signature", status=400)

    try:
        payload = request.body.decode("utf-8")
        client = razorpay.Client(
            auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET)
        )
        client.utility.verify_webhook_signature(
            payload, razorpay_signature, webhook_secret
        )
    except (razorpay.errors.SignatureVerificationError, Exception):
        return HttpResponse("Invalid signature", status=400)

    try:
        event = json.loads(payload)
    except json.JSONDecodeError:
        return HttpResponse("Invalid JSON", status=400)

    if event.get("event") not in ("payment.captured", "payment.failed"):
        return HttpResponse("OK", status=200)

    PaymentService.handle_webhook(event)
    return HttpResponse("OK", status=200)


@login_required
def payment_success(request, booking_id):
    booking = get_object_or_404(Booking, id=booking_id, user=request.user)
    payment = booking.payment
    return render(request, "payments/payment_success.html", {
        "booking": booking,
        "payment": payment,
    })


@login_required
def payment_failed(request, booking_id):
    booking = get_object_or_404(Booking, id=booking_id, user=request.user)
    return render(request, "payments/payment_failed.html", {"booking": booking})


@login_required
def payment_receipt(request, booking_id):
    booking = get_object_or_404(Booking, id=booking_id, user=request.user)
    payment = getattr(booking, "payment", None)
    return render(request, "payments/receipt.html", {
        "booking": booking,
        "payment": payment,
    })
