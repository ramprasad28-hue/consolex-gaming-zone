# apps/api/tests.py
import datetime
import json
from decimal import Decimal

from django.test import TestCase
from django.urls import reverse

from apps.users.models import User
from apps.games.models import GameConsole
from apps.bookings.models import Booking


class AuthRegisterTests(TestCase):
    def test_register_success(self):
        resp = self.client.post(
            reverse("api-register"),
            data=json.dumps({
                "email": "new@api.com",
                "password": "securepass123",
                "first_name": "API",
                "last_name": "User",
            }),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 201)
        self.assertTrue(User.objects.filter(email="new@api.com").exists())

    def test_register_missing_fields(self):
        resp = self.client.post(
            reverse("api-register"),
            data=json.dumps({"email": "x@x.com"}),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 400)

    def test_register_short_password(self):
        resp = self.client.post(
            reverse("api-register"),
            data=json.dumps({"email": "x@x.com", "password": "123"}),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 400)

    def test_register_duplicate_email(self):
        User.objects.create_user(email="dup@api.com", password="x")
        resp = self.client.post(
            reverse("api-register"),
            data=json.dumps({"email": "dup@api.com", "password": "securepass123"}),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 400)


class AuthLoginTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="login@api.com", password="testpass123"
        )

    def test_login_success(self):
        resp = self.client.post(
            reverse("api-login"),
            data=json.dumps({"email": "login@api.com", "password": "testpass123"}),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 200)
        self.assertIn("email", json.loads(resp.content))

    def test_login_wrong_password(self):
        resp = self.client.post(
            reverse("api-login"),
            data=json.dumps({"email": "login@api.com", "password": "wrong"}),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 401)

    def test_login_nonexistent_user(self):
        resp = self.client.post(
            reverse("api-login"),
            data=json.dumps({"email": "noone@api.com", "password": "x"}),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 401)


class AuthLogoutTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(email="lo@api.com", password="x")

    def test_logout_success(self):
        self.client.force_login(self.user)
        resp = self.client.post(reverse("api-logout"))
        self.assertEqual(resp.status_code, 204)

    def test_logout_unauthenticated(self):
        resp = self.client.post(reverse("api-logout"))
        self.assertIn(resp.status_code, [401, 403])


class AuthMeTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="me@api.com", password="x", first_name="Test"
        )

    def test_me_get(self):
        self.client.force_login(self.user)
        resp = self.client.get(reverse("api-me"))
        self.assertEqual(resp.status_code, 200)
        data = json.loads(resp.content)
        self.assertEqual(data["email"], "me@api.com")

    def test_me_patch(self):
        self.client.force_login(self.user)
        resp = self.client.patch(
            reverse("api-me"),
            data=json.dumps({"first_name": "Updated"}),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 200)
        self.user.refresh_from_db()
        self.assertEqual(self.user.first_name, "Updated")

    def test_me_unauthenticated(self):
        resp = self.client.get(reverse("api-me"))
        self.assertIn(resp.status_code, [401, 403])


class ConsoleListTests(TestCase):
    def setUp(self):
        self.console = GameConsole.objects.create(
            name="PS5-1", console_type="PS5",
            hourly_rate_weekday=Decimal("130.00"),
            hourly_rate_weekend=Decimal("150.00"),
        )

    def test_console_list(self):
        resp = self.client.get(reverse("api-console-list"))
        self.assertEqual(resp.status_code, 200)
        data = json.loads(resp.content)
        self.assertEqual(len(data), 1)

    def test_console_list_unauthenticated(self):
        resp = self.client.get(reverse("api-console-list"))
        self.assertEqual(resp.status_code, 200)

    def test_console_detail(self):
        resp = self.client.get(
            reverse("api-console-detail", args=[self.console.id])
        )
        self.assertEqual(resp.status_code, 200)
        data = json.loads(resp.content)
        self.assertEqual(data["name"], "PS5-1")

    def test_console_detail_not_found(self):
        resp = self.client.get(reverse("api-console-detail", args=[9999]))
        self.assertEqual(resp.status_code, 404)

    def test_console_detail_inactive(self):
        self.console.is_active = False
        self.console.save()
        resp = self.client.get(
            reverse("api-console-detail", args=[self.console.id])
        )
        self.assertEqual(resp.status_code, 404)


class BookingListTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(email="bl@api.com", password="x")
        self.console = GameConsole.objects.create(
            name="PS5-1", console_type="PS5",
            hourly_rate_weekday=Decimal("130.00"),
            hourly_rate_weekend=Decimal("150.00"),
        )

    def test_booking_list_authenticated(self):
        self.client.force_login(self.user)
        resp = self.client.get(reverse("api-booking-list"))
        self.assertEqual(resp.status_code, 200)

    def test_booking_list_unauthenticated(self):
        resp = self.client.get(reverse("api-booking-list"))
        self.assertIn(resp.status_code, [401, 403])

    def test_booking_detail(self):
        booking = Booking.objects.create(
            user=self.user, game_console=self.console,
            booking_date=datetime.date(2026, 9, 1),
            start_time=datetime.time(10, 0),
            end_time=datetime.time(12, 0),
            number_of_players=1, total_cost=260, status="pending",
        )
        self.client.force_login(self.user)
        resp = self.client.get(
            reverse("api-booking-detail", args=[booking.id])
        )
        self.assertEqual(resp.status_code, 200)
        data = json.loads(resp.content)
        self.assertEqual(data["id"], booking.id)

    def test_booking_detail_not_found(self):
        self.client.force_login(self.user)
        resp = self.client.get(reverse("api-booking-detail", args=[9999]))
        self.assertEqual(resp.status_code, 404)

    def test_booking_cancel(self):
        booking = Booking.objects.create(
            user=self.user, game_console=self.console,
            booking_date=datetime.date(2026, 9, 1),
            start_time=datetime.time(10, 0),
            end_time=datetime.time(12, 0),
            number_of_players=1, total_cost=260, status="confirmed",
        )
        self.client.force_login(self.user)
        resp = self.client.post(
            reverse("api-booking-cancel", args=[booking.id])
        )
        self.assertEqual(resp.status_code, 200)
        booking.refresh_from_db()
        self.assertEqual(booking.status, "cancelled")
