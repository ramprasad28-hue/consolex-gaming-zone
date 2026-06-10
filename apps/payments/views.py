from django.shortcuts import render
import hmac
import hashlib
import json

import razorpay
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render, redirect
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from apps.bookings.models import Booking
from .models import Payment
from .utils import send_whatsapp_booking_notification


def _razorpay_client():
    return razorpay.Client(
        auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET)
    )


# ── 1. PAYMENT PAGE ──────────────────────────────────────
@login_required
def payment_page(request, booking_id):
    """
    Shows the payment page for a booking.
    Creates a Razorpay order if one doesn't exist yet.
    """
    booking = get_object_or_404(Booking, id=booking_id, user=request.user)

    # Prevent double-payment
    if hasattr(booking, 'payment') and booking.payment.status == 'captured':
        return redirect('payment_success', booking_id=booking.id)

    # 30% advance in paise
    advance_rupees = round(booking.total_cost * 0.30, 2)
    advance_paise  = int(advance_rupees * 100)

    # Create Razorpay order
    client = _razorpay_client()
    rp_order = client.order.create({
        'amount':   advance_paise,
        'currency': 'INR',
        'receipt':  f'consolex_booking_{booking.id}',
        'notes': {
            'booking_id': str(booking.id),
            'customer':   request.user.email,
        }
    })

    # Save / update Payment record
    payment, _ = Payment.objects.get_or_create(
        booking=booking,
        defaults={
            'user':              request.user,
            'razorpay_order_id': rp_order['id'],
            'amount_paise':      advance_paise,
        }
    )
    # If order was already created earlier, refresh the order id
    if payment.razorpay_order_id != rp_order['id']:
        payment.razorpay_order_id = rp_order['id']
        payment.amount_paise      = advance_paise
        payment.save()

    context = {
        'booking':         booking,
        'payment':         payment,
        'advance_rupees':  advance_rupees,
        'total_rupees':    booking.total_cost,
        'balance_rupees':  booking.total_cost - advance_rupees,
        'razorpay_key_id': settings.RAZORPAY_KEY_ID,
        'rp_order_id':     rp_order['id'],
        'rp_amount':       advance_paise,
    }
    return render(request, 'payments/payment_page.html', context)


# ── 2. VERIFY PAYMENT (AJAX) ─────────────────────────────
@login_required
@require_POST
def verify_payment(request):
    """
    Called by the Razorpay JS handler after checkout completes.
    Verifies HMAC signature and marks payment as captured.
    """
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'Invalid JSON'}, status=400)

    rp_order_id   = data.get('razorpay_order_id', '')
    rp_payment_id = data.get('razorpay_payment_id', '')
    rp_signature  = data.get('razorpay_signature', '')

    # Verify HMAC-SHA256 signature
    generated = hmac.new(
        settings.RAZORPAY_KEY_SECRET.encode(),
        f"{rp_order_id}|{rp_payment_id}".encode(),
        hashlib.sha256
    ).hexdigest()

    if not hmac.compare_digest(generated, rp_signature):
        return JsonResponse({'success': False, 'error': 'Signature mismatch'}, status=400)

    # Update Payment record
    try:
        payment = Payment.objects.get(razorpay_order_id=rp_order_id)
    except Payment.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Payment record not found'}, status=404)

    payment.razorpay_payment_id = rp_payment_id
    payment.razorpay_signature  = rp_signature
    payment.status              = 'captured'
    payment.save()

    # Update booking status
    booking = payment.booking
    booking.status = 'confirmed'
    booking.save()

    # Send WhatsApp notification to owner
    send_whatsapp_booking_notification(booking, payment)

    return JsonResponse({
        'success':    True,
        'booking_id': booking.id,
        'redirect':   f'/payments/success/{booking.id}/',
    })


# ── 3. SUCCESS PAGE ───────────────────────────────────────
@login_required
def payment_success(request, booking_id):
    booking = get_object_or_404(Booking, id=booking_id, user=request.user)
    payment = get_object_or_404(Payment, booking=booking)
    return render(request, 'payments/payment_success.html', {
        'booking': booking,
        'payment': payment,
    })


# ── 4. FAILURE PAGE ───────────────────────────────────────
@login_required
def payment_failed(request, booking_id):
    booking = get_object_or_404(Booking, id=booking_id, user=request.user)
    return render(request, 'payments/payment_failed.html', {'booking': booking})