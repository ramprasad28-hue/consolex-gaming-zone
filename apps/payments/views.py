# apps/payments/views.py

import json
import razorpay

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.csrf import csrf_exempt

from apps.bookings.models import Booking
from apps.notifications.models import Notification

from .models import Payment
from .utils import send_whatsapp_booking_notification
from .loyalty import accrue_loyalty


@login_required
def payment_page(request, booking_id):

    booking = get_object_or_404(
        Booking,
        id=booking_id,
        user=request.user
    )

    if booking.status == "confirmed":
        messages.info(request, "Booking already paid.")
        return redirect("users:dashboard")

    client = razorpay.Client(
        auth=(
            settings.RAZORPAY_KEY_ID,
            settings.RAZORPAY_KEY_SECRET
        )
    )

    amount = int(booking.advance_amount * 100)

    try:

        razorpay_order = client.order.create({
            "amount": amount,
            "currency": "INR",
            "payment_capture": 1,
        })

    except Exception:

        messages.error(
            request,
            "Unable to connect to Razorpay."
        )

        return redirect("bookings:booking_form")

    Payment.objects.update_or_create(

        booking=booking,

        defaults={
            "user": request.user,
            "razorpay_order_id": razorpay_order["id"],
            "amount": amount,
            "status": "pending",
        }

    )

    return render(

        request,

        "payments/payment_page.html",

        {

            "booking": booking,

            "total_rupees": booking.total_cost,

            "advance_rupees": booking.advance_amount,

            "balance_rupees": booking.balance_amount,

            "rp_amount": amount,

            "rp_order_id": razorpay_order["id"],

            "razorpay_key_id": settings.RAZORPAY_KEY_ID,

        },

    )


@login_required
@transaction.atomic
def verify_payment(request):

    if request.method != "POST":

        return JsonResponse({

            "success": False,

            "error": "Invalid request."

        })

    try:

        data = json.loads(request.body)

    except json.JSONDecodeError:

        return JsonResponse({

            "success": False,

            "error": "Invalid JSON."

        })

    payment_id = data.get("razorpay_payment_id")
    order_id = data.get("razorpay_order_id")
    signature = data.get("razorpay_signature")

    if not payment_id or not order_id or not signature:

        return JsonResponse({

            "success": False,

            "error": "Missing payment data."

        })

    # Lock the payment row so concurrent confirmations are serialized.
    payment = get_object_or_404(

        Payment.objects.select_for_update(),

        razorpay_order_id=order_id,

        user=request.user

    )

    # Re-check inside the transaction: if a prior (concurrent) request
    # already confirmed this payment, short-circuit without re-processing.
    if payment.is_successful:
        booking = payment.booking
        return JsonResponse({
            "success": True,
            "redirect": f"/payments/success/{booking.id}/"
        })

    client = razorpay.Client(

        auth=(

            settings.RAZORPAY_KEY_ID,

            settings.RAZORPAY_KEY_SECRET

        )

    )

    params = {

        "razorpay_order_id": order_id,

        "razorpay_payment_id": payment_id,

        "razorpay_signature": signature,

    }

    try:

        client.utility.verify_payment_signature(params)

    except razorpay.errors.SignatureVerificationError:

        payment.status = "failed"
        payment.razorpay_payment_id = payment_id
        payment.razorpay_signature = signature
        payment.save()

        return JsonResponse({

            "success": False,

            "error": "Signature verification failed."

        })

    confirm_payment(payment, payment_id, signature, request.user)

    return JsonResponse({

        "success": True,

        "redirect": f"/payments/success/{payment.booking.id}/"

    })


def confirm_payment(payment, razorpay_payment_id, razorpay_signature, user):
    """
    Idempotently mark a payment captured, confirm the booking, accrue
    loyalty and notify. Safe to call from the return-URL flow OR the
    Razorpay webhook — caller is responsible for row locking and signature
    verification beforehand.
    """
    # Guard: never re-process an already-successful payment.
    if payment.is_successful:
        return

    booking = payment.booking

    payment.razorpay_payment_id = razorpay_payment_id
    payment.razorpay_signature = razorpay_signature
    payment.status = Payment.Status.CAPTURED
    payment.save(update_fields=[
        "razorpay_payment_id", "razorpay_signature", "status", "updated_at"
    ])

    booking.status = "confirmed"
    booking.save(update_fields=["status", "updated_at"])

    accrue_loyalty(user, payment.amount_rupees)

    Notification.objects.create(
        user=user,
        message=f"Booking #{booking.id} confirmed successfully."
    )

    try:
        send_whatsapp_booking_notification(booking, payment)
    except Exception:
        # Never let notification failures break the confirmation.
        pass


@csrf_exempt
@transaction.atomic
def razorpay_webhook(request):
    """
    Server-side source of truth for payment state.

    Razorpay sends events here (configure the webhook in the Razorpay
    dashboard pointing at /payments/webhook/ with the `payment.captured`
    and `payment.failed` events). This is what guarantees a booking is
    confirmed even if the user closes the tab before the return-URL flow
    runs. Verification uses the webhook secret (razorpay webhook body
    signature), not the order signature.
    """
    if request.method != "POST":
        return HttpResponse("Method not allowed", status=405)

    webhook_secret = settings.RAZORPAY_WEBHOOK_SECRET
    if not webhook_secret:
        # Webhook not configured — return 200 so Razorpay doesn't retry
        # endlessly, but do nothing. The return-URL flow still works.
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

    payment_entity = event.get("payload", {}).get("payment", {}).get("entity", {})
    order_id = payment_entity.get("order_id")
    payment_id = payment_entity.get("id")

    if not order_id:
        return HttpResponse("OK", status=200)

    # Lock the row so a concurrent return-URL confirmation can't race us.
    payment = Payment.objects.select_for_update().filter(
        razorpay_order_id=order_id
    ).first()
    if not payment:
        # Payment row may not exist yet (edge case) — let return-URL handle it.
        return HttpResponse("OK", status=200)

    if payment.is_successful:
        return HttpResponse("OK", status=200)

    if event.get("event") == "payment.captured":
        confirm_payment(payment, payment_id, "", payment.user)
    else:
        payment.status = Payment.Status.FAILED
        payment.razorpay_payment_id = payment_id
        payment.save(update_fields=["status", "razorpay_payment_id", "updated_at"])

    return HttpResponse("OK", status=200)


@login_required
def payment_success(request, booking_id):

    booking = get_object_or_404(

        Booking,

        id=booking_id,

        user=request.user

    )

    payment = booking.payment

    return render(

        request,

        "payments/payment_success.html",

        {

            "booking": booking,

            "payment": payment,

        },

    )


@login_required
def payment_failed(request, booking_id):

    booking = get_object_or_404(

        Booking,

        id=booking_id,

        user=request.user

    )

    return render(

        request,

        "payments/payment_failed.html",

        {

            "booking": booking,

        },

    )


@login_required
def payment_receipt(request, booking_id):
    """Downloadable/printable payment receipt for a confirmed booking."""
    booking = get_object_or_404(Booking, id=booking_id, user=request.user)
    payment = getattr(booking, 'payment', None)
    return render(request, "payments/receipt.html", {
        "booking": booking,
        "payment": payment,
    })