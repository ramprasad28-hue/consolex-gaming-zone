# ─────────────────────────────────────────────
# File: apps/payments/views.py
# ─────────────────────────────────────────────

import hmac
import hashlib
import json

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render, redirect
from django.views.decorators.http import require_POST
from django.contrib import messages

from apps.bookings.models import Booking
from apps.notifications.models import Notification
from .models import Payment
from .utils import send_whatsapp_booking_notification


# ── DEMO MODE FLAG ────────────────────────────
# Set RAZORPAY_DEMO_MODE = True in settings to
# bypass Razorpay entirely for demonstrations.
DEMO_MODE = getattr(settings, 'RAZORPAY_DEMO_MODE', False)


def _razorpay_client():
    import razorpay
    return razorpay.Client(
        auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET)
    )


# ── 1. PAYMENT PAGE ───────────────────────────
@login_required
def payment_page(request, booking_id):
    booking = get_object_or_404(Booking, id=booking_id, user=request.user)

    # Already paid — go straight to success
    if hasattr(booking, 'payment') and booking.payment.status in ('captured', 'demo'):
        return redirect('payment_success', booking_id=booking.id)

    advance_rupees = float(booking.advance_amount)
    advance_paise  = int(advance_rupees * 100)

    rp_order_id = ''

    if not DEMO_MODE:
        try:
            client   = _razorpay_client()
            rp_order = client.order.create({
                'amount':   advance_paise,
                'currency': 'INR',
                'receipt':  f'consolex_{booking.id}',
                'notes':    {'booking_id': str(booking.id)},
            })
            rp_order_id = rp_order['id']

            payment, _ = Payment.objects.get_or_create(
                booking=booking,
                defaults={
                    'user':              request.user,
                    'razorpay_order_id': rp_order_id,
                    'amount_paise':      advance_paise,
                }
            )
            if payment.razorpay_order_id != rp_order_id:
                payment.razorpay_order_id = rp_order_id
                payment.amount_paise      = advance_paise
                payment.save()

        except Exception as e:
            # Razorpay unavailable — fall back to demo mode gracefully
            messages.warning(
                request,
                'Payment gateway unavailable. Using demo mode for this session.'
            )
            return redirect('demo_payment', booking_id=booking.id)
    else:
        # Demo mode — create a Payment record without an order id
        Payment.objects.get_or_create(
            booking=booking,
            defaults={
                'user':         request.user,
                'amount_paise': advance_paise,
                'is_demo':      True,
            }
        )

    context = {
        'booking':         booking,
        'advance_rupees':  advance_rupees,
        'balance_rupees':  float(booking.balance_amount),
        'total_rupees':    float(booking.total_cost),
        'razorpay_key_id': settings.RAZORPAY_KEY_ID,
        'rp_order_id':     rp_order_id,
        'rp_amount':       advance_paise,
        'demo_mode':       DEMO_MODE,
    }
    return render(request, 'payments/payment_page.html', context)


# ── 2. DEMO PAYMENT (no Razorpay needed) ─────
@login_required
def demo_payment(request, booking_id):
    """
    Simulates a successful payment for demo / submission purposes.
    Activated when RAZORPAY_DEMO_MODE=True or Razorpay is unavailable.
    """
    booking = get_object_or_404(Booking, id=booking_id, user=request.user)

    advance_paise = int(float(booking.advance_amount) * 100)

    payment, _ = Payment.objects.get_or_create(
        booking=booking,
        defaults={
            'user':         request.user,
            'amount_paise': advance_paise,
            'is_demo':      True,
            'status':       'pending',
        }
    )

    if request.method == 'POST':
        action = request.POST.get('action', 'approve')

        if action == 'approve':
            payment.status              = 'demo'
            payment.razorpay_payment_id = 'demo_pay_consolex'
            payment.save()

            booking.status = 'confirmed'
            booking.save()

            # Save notification
            Notification.objects.create(
                user    = request.user,
                message = (
                    f'Booking #{booking.id} confirmed (demo). '
                    f'Slot: {booking.booking_date} '
                    f'{booking.start_time.strftime("%I:%M %p")} – '
                    f'{booking.end_time.strftime("%I:%M %p")}'
                )
            )

            # WhatsApp — never crashes flow
            send_whatsapp_booking_notification(booking, payment)

            return redirect('payment_success', booking_id=booking.id)

        elif action == 'fail':
            payment.status = 'failed'
            payment.save()
            return redirect('payment_failed', booking_id=booking.id)

    context = {
        'booking':        booking,
        'advance_rupees': float(booking.advance_amount),
        'balance_rupees': float(booking.balance_amount),
        'total_rupees':   float(booking.total_cost),
    }
    return render(request, 'payments/demo_payment.html', context)


# ── 3. VERIFY PAYMENT (Razorpay AJAX) ────────
@login_required
@require_POST
def verify_payment(request):
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'Invalid JSON'}, status=400)

    rp_order_id   = data.get('razorpay_order_id', '')
    rp_payment_id = data.get('razorpay_payment_id', '')
    rp_signature  = data.get('razorpay_signature', '')

    # HMAC-SHA256 verification
    generated = hmac.new(
        settings.RAZORPAY_KEY_SECRET.encode(),
        f"{rp_order_id}|{rp_payment_id}".encode(),
        hashlib.sha256
    ).hexdigest()

    if not hmac.compare_digest(generated, rp_signature):
        return JsonResponse({'success': False, 'error': 'Signature mismatch'}, status=400)

    try:
        payment = Payment.objects.get(razorpay_order_id=rp_order_id)
    except Payment.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Payment not found'}, status=404)

    payment.razorpay_payment_id = rp_payment_id
    payment.razorpay_signature  = rp_signature
    payment.status              = 'captured'
    payment.save()

    booking        = payment.booking
    booking.status = 'confirmed'
    booking.save()

    # Notification record
    Notification.objects.create(
        user    = booking.user,
        message = (
            f'Booking #{booking.id} confirmed. '
            f'Slot: {booking.booking_date} '
            f'{booking.start_time.strftime("%I:%M %p")} – '
            f'{booking.end_time.strftime("%I:%M %p")}'
        )
    )

    send_whatsapp_booking_notification(booking, payment)

    return JsonResponse({
        'success':    True,
        'booking_id': booking.id,
        'redirect':   f'/payments/success/{booking.id}/',
    })


# ── 4. SUCCESS ────────────────────────────────
@login_required
def payment_success(request, booking_id):
    booking = get_object_or_404(Booking, id=booking_id, user=request.user)
    payment = get_object_or_404(Payment, booking=booking)
    return render(request, 'payments/payment_success.html', {
        'booking': booking,
        'payment': payment,
    })


# ── 5. FAILED ─────────────────────────────────
@login_required
def payment_failed(request, booking_id):
    booking = get_object_or_404(Booking, id=booking_id, user=request.user)
    payment = Payment.objects.filter(booking=booking).first()
    return render(request, 'payments/payment_failed.html', {
        'booking': booking,
        'payment': payment,
    })