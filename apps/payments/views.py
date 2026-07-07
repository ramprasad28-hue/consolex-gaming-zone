# apps/payments/views.py
import razorpay
import hmac
import hashlib
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.conf import settings
from django.db import transaction
from django.contrib import messages
from apps.bookings.models import Booking
from apps.notifications.models import Notification
from .models import Payment
from .utils import send_whatsapp_booking_notification

@login_required
def payment_page(request, booking_id):
    booking = get_object_or_404(Booking, id=booking_id, user=request.user)
    
    if booking.status == 'confirmed':
        messages.info(request, "This booking is already confirmed and paid.")
        return redirect('users:dashboard')

    client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))
    
    # Amount in paise
    amount = int(booking.advance_amount * 100)
    
    # Create Razorpay Order
    razorpay_order = client.order.create({
        "amount": amount,
        "currency": "INR",
        "payment_capture": "1"
    })

    # Create Payment record
    Payment.objects.update_or_create(
        booking=booking,
        defaults={
            'user': request.user,
            'razorpay_order_id': razorpay_order['id'],
            'amount_paise': amount,
            'status': 'pending'
        }
    )

    context = {
        'booking': booking,
        'razorpay_order_id': razorpay_order['id'],
        'razorpay_key_id': settings.RAZORPAY_KEY_ID,
        'amount': amount,
        'currency': 'INR',
    }
    return render(request, 'payments/payment_page.html', context)

@login_required
@transaction.atomic
def verify_payment(request):
    if request.method != 'POST':
        return redirect('users:dashboard')

    payment_id = request.POST.get('razorpay_payment_id')
    order_id = request.POST.get('razorpay_order_id')
    signature = request.POST.get('razorpay_signature')

    if not all([payment_id, order_id, signature]):
        messages.error(request, "Payment validation failed: Missing data.")
        return redirect('users:dashboard')

    try:
        payment = get_object_or_404(Payment, razorpay_order_id=order_id, user=request.user)
        booking = payment.booking

        # Server-side HMAC-SHA256 Signature Verification
        generated_signature = hmac.new(
            settings.RAZORPAY_KEY_SECRET.encode('utf-8'),
            f"{order_id}|{payment_id}".encode('utf-8'),
            hashlib.sha256
        ).hexdigest()

        if hmac.compare_digest(generated_signature, signature):
            # Payment Successful
            payment.razorpay_payment_id = payment_id
            payment.razorpay_signature = signature
            payment.status = 'captured'
            payment.save()

            booking.status = 'confirmed'
            booking.save()

            # Create Database Notification
            Notification.objects.create(
                user=request.user,
                message=f"Your booking for {booking.booking_date} at {booking.start_time} is confirmed! Advance paid: ₹{payment.amount_rupees}."
            )

            # Send WhatsApp (Fails silently internally)
            send_whatsapp_booking_notification(booking, payment)

            messages.success(request, "Payment successful! Your slot is booked.")
            return redirect('payments:payment_success', booking_id=booking.id)
        else:
            # Signature Mismatch
            payment.status = 'failed'
            payment.save()
            booking.status = 'cancelled'
            booking.save()
            messages.error(request, "Payment verification failed: Signature mismatch.")
            return redirect('payments:payment_failed', booking_id=booking.id)

    except Exception as e:
        messages.error(request, f"An error occurred during payment verification: {str(e)}")
        return redirect('users:dashboard')

@login_required
def payment_success(request, booking_id):
    booking = get_object_or_404(Booking, id=booking_id, user=request.user)
    return render(request, 'payments/payment_success.html', {'booking': booking})

@login_required
def payment_failed(request, booking_id):
    booking = get_object_or_404(Booking, id=booking_id, user=request.user)
    return render(request, 'payments/payment_failed.html', {'booking': booking})