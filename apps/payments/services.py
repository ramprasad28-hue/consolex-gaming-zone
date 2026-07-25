"""
Business logic for payments: Razorpay integration, verification, receipts.

Both the Django template views and the DRF API views delegate here.
"""
import logging

import razorpay
from decimal import Decimal
from django.conf import settings
from django.db import transaction

from apps.bookings.models import Booking
from apps.payments.models import Payment
from apps.payments.loyalty import accrue_loyalty
from apps.notifications.services import NotificationService
from apps.common.exceptions import (
    RazorpayError,
    RazorpaySignatureError,
    PaymentAlreadyCompletedError,
    PaymentNotFoundError,
    BookingNotFoundError,
)

logger = logging.getLogger("apps.payments")


class PaymentService:
    """Stateless payment operations."""

    # ── Razorpay client ────────────────────────────────────

    @staticmethod
    def _get_client():
        if settings.RAZORPAY_KEY_ID and settings.RAZORPAY_KEY_SECRET:
            return razorpay.Client(
                auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET)
            )
        return None

    # ── Order creation ─────────────────────────────────────

    @staticmethod
    def create_order(user, booking_id):
        """
        Create a Razorpay order (or demo payment) for a booking's advance.

        Returns dict with order details.
        """
        try:
            booking = Booking.objects.get(pk=booking_id, user=user)
        except Booking.DoesNotExist:
            raise BookingNotFoundError(f"Booking #{booking_id} not found.")

        advance_paise = int(booking.advance_amount * Decimal("100"))

        # Check if already paid
        existing = Payment.objects.filter(booking=booking).first()
        if existing and existing.status == Payment.Status.CAPTURED:
            raise PaymentAlreadyCompletedError()

        client = PaymentService._get_client()

        if client is None:
            # Demo mode
            payment = existing or Payment.objects.create(
                booking=booking,
                user=user,
                amount=advance_paise,
                status=Payment.Status.PENDING,
                is_demo=True,
            )
            logger.info("Demo mode: payment #%s created for booking #%s", payment.id, booking.id)
            return {
                "demo_mode": True,
                "payment_id": payment.id,
                "amount": advance_paise,
                "booking_id": booking.id,
            }

        try:
            order = client.order.create({
                "amount": advance_paise,
                "currency": "INR",
                "payment_capture": 0,
            })
        except Exception as e:
            logger.error("Razorpay order creation failed: %s", e)
            raise RazorpayError()

        payment = existing or Payment.objects.create(
            booking=booking,
            user=user,
            amount=advance_paise,
            status=Payment.Status.PENDING,
        )
        payment.razorpay_order_id = order["id"]
        payment.save(update_fields=["razorpay_order_id"])

        return {
            "order_id": order["id"],
            "amount": advance_paise,
            "key_id": settings.RAZORPAY_KEY_ID,
            "booking_id": booking.id,
            "payment_id": payment.id,
        }

    # ── Payment verification ───────────────────────────────

    @staticmethod
    def verify_payment(user, payment_id, razorpay_order_id, razorpay_payment_id, razorpay_signature):
        """
        Verify a Razorpay payment and confirm the booking.

        Returns dict with payment status.
        """
        try:
            payment = Payment.objects.select_for_update().get(
                pk=payment_id, booking__user=user
            )
        except Payment.DoesNotExist:
            raise PaymentNotFoundError("Payment not found.")

        if payment.is_successful:
            return {"status": payment.status, "booking_status": payment.booking.status}

        client = PaymentService._get_client()

        if client is None:
            # Demo mode — auto approve
            PaymentService._confirm_payment(
                payment,
                razorpay_payment_id or "demo_payment",
                razorpay_signature or "demo_sig",
                is_demo=True,
            )
            logger.info("Demo payment approved for booking #%s", payment.booking_id)
            return {"status": "demo", "booking_status": "confirmed"}

        try:
            client.utility.verify_payment_signature({
                "razorpay_order_id": razorpay_order_id,
                "razorpay_payment_id": razorpay_payment_id,
                "razorpay_signature": razorpay_signature,
            })
        except razorpay.errors.SignatureVerificationError:
            payment.status = Payment.Status.FAILED
            payment.razorpay_order_id = razorpay_order_id
            payment.razorpay_payment_id = razorpay_payment_id
            payment.razorpay_signature = razorpay_signature
            payment.save()
            logger.warning("Payment signature verification failed for payment #%s", payment.id)
            raise RazorpaySignatureError()

        PaymentService._confirm_payment(
            payment, razorpay_payment_id, razorpay_signature, is_demo=False
        )

        return {"status": payment.status, "booking_status": payment.booking.status}

    # ── Webhook handler ────────────────────────────────────

    @staticmethod
    @transaction.atomic
    def handle_webhook(event_payload):
        """
        Process a Razorpay webhook event.

        Called by the webhook view after signature verification.
        """
        event_type = event_payload.get("event")
        payment_entity = (
            event_payload.get("payload", {})
            .get("payment", {})
            .get("entity", {})
        )
        order_id = payment_entity.get("order_id")
        payment_id = payment_entity.get("id")

        if not order_id:
            return

        payment = Payment.objects.select_for_update().filter(
            razorpay_order_id=order_id
        ).first()

        if not payment or payment.is_successful:
            return

        if event_type == "payment.captured":
            PaymentService._confirm_payment(
                payment, payment_id or "", "", is_demo=False
            )
            logger.info("Webhook: payment #%s confirmed", payment.id)
        elif event_type == "payment.failed":
            payment.status = Payment.Status.FAILED
            payment.razorpay_payment_id = payment_id
            payment.save(update_fields=["status", "razorpay_payment_id", "updated_at"])
            logger.info("Webhook: payment #%s marked failed", payment.id)

    # ── Confirmation ───────────────────────────────────────

    @staticmethod
    def _confirm_payment(payment, razorpay_payment_id, razorpay_signature, is_demo=False):
        """
        Idempotently mark a payment as captured and confirm the booking.
        """
        if payment.is_successful:
            return

        payment.razorpay_payment_id = razorpay_payment_id
        payment.razorpay_signature = razorpay_signature
        payment.status = Payment.Status.DEMO if is_demo else Payment.Status.CAPTURED
        payment.is_demo = is_demo
        payment.save(update_fields=[
            "razorpay_payment_id", "razorpay_signature",
            "status", "is_demo", "updated_at",
        ])

        booking = payment.booking
        booking.status = "confirmed"
        booking.save(update_fields=["status", "updated_at"])

        # Loyalty accrual
        accrue_loyalty(payment.user, payment.amount_rupees)

        # Notification
        NotificationService.notify(
            payment.user,
            f"Booking #{booking.id} confirmed successfully.",
        )

    # ── Receipt ────────────────────────────────────────────

    @staticmethod
    def get_receipt(user, booking_id):
        try:
            booking = Booking.objects.select_related("payment", "game_console").get(
                pk=booking_id, user=user
            )
        except Booking.DoesNotExist:
            raise BookingNotFoundError(f"Booking #{booking_id} not found.")

        data = {
            "booking_id": booking.id,
            "date": str(booking.booking_date),
            "time": str(booking.start_time),
            "console": booking.game_console.name if booking.game_console else "",
            "players": booking.number_of_players,
            "duration": booking.duration_hours,
            "total_cost": float(booking.total_cost),
            "advance_paid": float(booking.advance_amount),
            "balance": float(booking.balance_amount),
            "status": booking.status,
        }

        if hasattr(booking, "payment"):
            from apps.api.serializers import PaymentSerializer
            data["payment"] = PaymentSerializer(booking.payment).data

        return data
