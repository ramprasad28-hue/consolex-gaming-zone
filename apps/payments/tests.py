# apps/payments/tests.py
import json
from decimal import Decimal
from unittest.mock import patch, MagicMock

from django.test import TestCase
from django.urls import reverse

from apps.bookings.models import Booking
from apps.memberships.models import LoyaltyProfile
from apps.payments.models import Payment
from apps.payments.services import PaymentService
from apps.users.models import User
from apps.common.exceptions import (
    PaymentAlreadyCompletedError,
    RazorpaySignatureError,
    BookingNotFoundError,
    PaymentNotFoundError,
)


class PaymentConfirmationTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(email="pay@x.com", password="x")
        self.booking = Booking.objects.create(
            user=self.user,
            booking_date=__import__("datetime").date(2026, 9, 1),
            start_time=__import__("datetime").time(10, 0),
            end_time=__import__("datetime").time(12, 0),
            number_of_players=1, total_cost=600, status="pending",
        )
        self.payment = Payment.objects.create(
            booking=self.booking, user=self.user,
            razorpay_order_id="order_abc", amount=18000, status="pending",
        )

    def _post_verify(self, valid_signature=True):
        fake_client = MagicMock()
        verify = fake_client.utility.verify_payment_signature
        if valid_signature:
            verify.return_value = None
        else:
            from razorpay.errors import SignatureVerificationError
            verify.side_effect = SignatureVerificationError("bad sig")

        with patch.object(PaymentService, "_get_client", return_value=fake_client):
            return self.client.post(
                reverse("payments:verify_payment"),
                data=json.dumps({
                    "razorpay_payment_id": "pay_xyz",
                    "razorpay_order_id": "order_abc",
                    "razorpay_signature": "sig" if valid_signature else "bad",
                    "payment_id": self.payment.id,
                }),
                content_type="application/json",
            )

    def test_valid_signature_confirms_booking(self):
        self.client.force_login(self.user)
        resp = self._post_verify(valid_signature=True)
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(json.loads(resp.content)["success"])

        self.booking.refresh_from_db()
        self.payment.refresh_from_db()
        self.assertEqual(self.booking.status, "confirmed")
        self.assertEqual(self.payment.status, "captured")

    def test_invalid_signature_marks_failed(self):
        self.client.force_login(self.user)
        resp = self._post_verify(valid_signature=False)
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(json.loads(resp.content)["success"])

        self.payment.refresh_from_db()
        self.assertEqual(self.payment.status, "failed")
        self.booking.refresh_from_db()
        self.assertEqual(self.booking.status, "pending")

    def test_confirmation_is_idempotent(self):
        self.client.force_login(self.user)
        self._post_verify(valid_signature=True)
        self._post_verify(valid_signature=True)

        profile = LoyaltyProfile.objects.get(user=self.user)
        # 18000 paise = 180 rupees -> 18 points (1 per 10 rupees).
        self.assertEqual(profile.points, 18)
        self.assertEqual(profile.lifetime_spending, Decimal("180.00"))


class PaymentServiceTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(email="psvc@x.com", password="x")
        self.booking = Booking.objects.create(
            user=self.user,
            booking_date=__import__("datetime").date(2026, 9, 1),
            start_time=__import__("datetime").time(10, 0),
            end_time=__import__("datetime").time(12, 0),
            number_of_players=1, total_cost=600, status="pending",
        )

    def test_create_order_booking_not_found(self):
        with self.assertRaises(BookingNotFoundError):
            PaymentService.create_order(self.user, 9999)

    def test_create_order_already_paid(self):
        Payment.objects.create(
            booking=self.booking, user=self.user,
            razorpay_order_id="order_paid", amount=18000, status="captured",
        )
        with self.assertRaises(PaymentAlreadyCompletedError):
            PaymentService.create_order(self.user, self.booking.id)

    def test_create_order_demo_mode(self):
        with patch.object(PaymentService, "_get_client", return_value=None):
            result = PaymentService.create_order(self.user, self.booking.id)
            self.assertTrue(result["demo_mode"])
            self.assertIn("payment_id", result)

    def test_verify_payment_not_found(self):
        with self.assertRaises(PaymentNotFoundError):
            PaymentService.verify_payment(self.user, 9999, "", "", "")

    def test_demo_payment_auto_approve(self):
        payment = Payment.objects.create(
            booking=self.booking, user=self.user,
            amount=18000, status="pending", is_demo=True,
        )
        with patch.object(PaymentService, "_get_client", return_value=None):
            result = PaymentService.verify_payment(
                self.user, payment.id, "demo_order", "demo_payment", "demo_sig"
            )
            self.assertEqual(result["status"], "demo")
            self.booking.refresh_from_db()
            self.assertEqual(self.booking.status, "confirmed")

    def test_get_receipt(self):
        Payment.objects.create(
            booking=self.booking, user=self.user,
            razorpay_order_id="order_1", amount=18000, status="captured",
        )
        data = PaymentService.get_receipt(self.user, self.booking.id)
        self.assertEqual(data["booking_id"], self.booking.id)
        self.assertIn("payment", data)

    def test_get_receipt_booking_not_found(self):
        with self.assertRaises(BookingNotFoundError):
            PaymentService.get_receipt(self.user, 9999)


class PaymentModelTests(TestCase):
    def test_amount_rupees(self):
        payment = Payment(amount=18000)
        self.assertEqual(payment.amount_rupees, Decimal("180.00"))

    def test_is_successful_captured(self):
        payment = Payment(status="captured")
        self.assertTrue(payment.is_successful)

    def test_is_successful_demo(self):
        payment = Payment(status="demo")
        self.assertTrue(payment.is_successful)

    def test_is_not_successful_pending(self):
        payment = Payment(status="pending")
        self.assertFalse(payment.is_successful)
