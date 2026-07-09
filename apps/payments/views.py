# apps/payments/views.py

import json
import razorpay

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render

from apps.bookings.models import Booking
from apps.notifications.models import Notification

from .models import Payment
from .utils import send_whatsapp_booking_notification


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

    payment = get_object_or_404(

        Payment,

        razorpay_order_id=order_id,

        user=request.user

    )

    booking = payment.booking

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

        payment.save()

        return JsonResponse({

            "success": False,

            "error": "Signature verification failed."

        })

    payment.razorpay_payment_id = payment_id
    payment.razorpay_signature = signature
    payment.status = "captured"

    payment.save()

    booking.status = "confirmed"

    booking.save()

    Notification.objects.create(

        user=request.user,

        message=(
            f"Booking #{booking.id} confirmed successfully."
        )

    )

    try:

        send_whatsapp_booking_notification(

            booking,

            payment

        )

    except Exception:

        pass

    return JsonResponse({

        "success": True,

        "redirect": f"/payments/success/{booking.id}/"

    })


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