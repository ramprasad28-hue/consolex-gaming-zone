# apps/staff/tests.py
from decimal import Decimal

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from apps.users.models import User
from apps.games.models import GameConsole
from apps.bookings.models import Booking


def make_staff(email="staff@test.com", superuser=False):
    if superuser:
        return User.objects.create_superuser(email=email, password="x")
    return User.objects.create_user(email=email, password="x", is_staff=True)


def make_console(name="PS5 Lounge 1"):
    return GameConsole.objects.create(
        name=name,
        console_type="PS5",
        hourly_rate_weekday=Decimal("130.00"),
        hourly_rate_weekend=Decimal("150.00"),
    )


class StaffAccessTests(TestCase):
    """The staff portal must be gated to staff/superusers only."""

    def test_anonymous_redirected_to_login(self):
        resp = self.client.get(reverse("staff:staff_dashboard"))
        self.assertRedirects(
            resp,
            f"{reverse('users:login')}?next={reverse('staff:staff_dashboard')}",
            fetch_redirect_response=False,
        )

    def test_regular_user_cannot_access(self):
        user = User.objects.create_user(email="customer@test.com", password="x")
        self.client.force_login(user)
        resp = self.client.get(reverse("staff:staff_dashboard"))
        self.assertNotEqual(resp.status_code, 200)

    def test_staff_can_access_dashboard(self):
        make_staff()
        self.client.force_login(User.objects.get(email="staff@test.com"))
        resp = self.client.get(reverse("staff:staff_dashboard"))
        self.assertEqual(resp.status_code, 200)

    def test_superuser_can_access_dashboard(self):
        make_staff(superuser=True)
        self.client.force_login(User.objects.get(email="staff@test.com"))
        resp = self.client.get(reverse("staff:staff_dashboard"))
        self.assertEqual(resp.status_code, 200)


class StaffDashboardTests(TestCase):
    def setUp(self):
        make_staff()
        self.client.force_login(User.objects.get(email="staff@test.com"))

    def test_dashboard_renders_with_context(self):
        resp = self.client.get(reverse("staff:staff_dashboard"))
        self.assertEqual(resp.status_code, 200)
        self.assertIn("todays_bookings_count", resp.context)
        self.assertIn("total_users", resp.context)
        self.assertIn("user_role", resp.context)

    def test_booking_list_filters_by_status(self):
        console = make_console()
        user = User.objects.create_user(email="b@test.com", password="x")
        Booking.objects.create(
            user=user, game_console=console,
            booking_date="2026-08-05", start_time="10:00", end_time="11:00",
            total_cost=Decimal("130.00"), status="confirmed",
        )
        resp = self.client.get(
            reverse("staff:staff_booking_list"), {"status": "confirmed"}
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.context["page_obj"].object_list), 1)

    def test_customer_list_renders(self):
        resp = self.client.get(reverse("staff:staff_customer_list"))
        self.assertEqual(resp.status_code, 200)
        self.assertIn("page_obj", resp.context)

    def test_analytics_renders(self):
        resp = self.client.get(reverse("staff:staff_analytics"))
        self.assertEqual(resp.status_code, 200)
        self.assertIn("daily_bookings", resp.context)
        self.assertIn("status_data", resp.context)

    def test_reports_index_renders(self):
        resp = self.client.get(reverse("staff:staff_reports"))
        self.assertEqual(resp.status_code, 200)


class LiveSessionsTests(TestCase):
    """Ch12 — check-in/check-out and the live-sessions console."""

    def setUp(self):
        make_staff()
        self.client.force_login(User.objects.get(email="staff@test.com"))
        self.console = make_console()
        self.customer = User.objects.create_user(email="player@test.com", password="x")
        self.booking = Booking.objects.create(
            user=self.customer, game_console=self.console,
            booking_date="2026-08-05", start_time="10:00", end_time="11:00",
            total_cost=Decimal("130.00"), status="confirmed",
        )

    def test_checkin_only_confirmed(self):
        self.booking.status = "pending"
        self.booking.save(update_fields=["status"])
        resp = self.client.post(
            reverse("staff:staff_booking_checkin", args=[self.booking.id])
        )
        self.assertEqual(resp.status_code, 302)
        self.booking.refresh_from_db()
        self.assertIsNone(self.booking.checked_in_at)
        self.assertEqual(self.booking.status, "pending")

    def test_checkin_marks_live(self):
        resp = self.client.post(
            reverse("staff:staff_booking_checkin", args=[self.booking.id])
        )
        self.assertEqual(resp.status_code, 302)
        self.booking.refresh_from_db()
        self.assertIsNotNone(self.booking.checked_in_at)
        self.assertEqual(self.booking.status, "checked_in")

    def test_checkout_completes_session(self):
        self.booking.status = "checked_in"
        self.booking.checked_in_at = timezone.now()
        self.booking.save(update_fields=["status", "checked_in_at"])

        resp = self.client.post(
            reverse("staff:staff_booking_checkout", args=[self.booking.id])
        )
        self.assertEqual(resp.status_code, 302)
        self.booking.refresh_from_db()
        self.assertIsNone(self.booking.checked_in_at)
        self.assertEqual(self.booking.status, "completed")

    def test_live_sessions_page_renders(self):
        resp = self.client.get(reverse("staff:staff_live_sessions"))
        self.assertEqual(resp.status_code, 200)
        self.assertIn("live_sessions_count", resp.context)

    def test_live_sessions_data_endpoint(self):
        self.booking.status = "checked_in"
        self.booking.checked_in_at = timezone.now()
        self.booking.save(update_fields=["status", "checked_in_at"])

        resp = self.client.get(reverse("staff:staff_live_sessions_data"))
        self.assertEqual(resp.status_code, 200)
        payload = resp.json()
        self.assertEqual(payload["count"], 1)
        self.assertEqual(payload["sessions"][0]["customer"], "player@test.com")
        self.assertIn("session_end", payload["sessions"][0])

    def test_live_sessions_data_empty(self):
        resp = self.client.get(reverse("staff:staff_live_sessions_data"))
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["count"], 0)

    def test_dashboard_includes_live_sessions(self):
        resp = self.client.get(reverse("staff:staff_dashboard"))
        self.assertEqual(resp.status_code, 200)
        self.assertIn("live_sessions", resp.context)


class ExecutiveDashboardTests(TestCase):
    """Ch13 — owner-only KPI dashboard."""

    def setUp(self):
        self.owner = make_staff(superuser=True)
        self.client.force_login(self.owner)

    def test_owner_can_access(self):
        resp = self.client.get(reverse("staff:staff_executive"))
        self.assertEqual(resp.status_code, 200)

    def test_regular_staff_cannot_access(self):
        self.client.logout()
        self.client.force_login(make_staff(email="junior@test.com"))
        resp = self.client.get(reverse("staff:staff_executive"))
        self.assertNotEqual(resp.status_code, 200)

    def test_executive_context_keys(self):
        resp = self.client.get(reverse("staff:staff_executive"))
        self.assertEqual(resp.status_code, 200)
        for key in [
            "total_revenue", "mrr", "arpu", "active_customers",
            "retention_rate", "monthly_revenue", "top_consoles",
            "top_customers", "utilization_pct",
        ]:
            self.assertIn(key, resp.context, key)

    def test_retention_rate_zero_safe(self):
        resp = self.client.get(reverse("staff:staff_executive"))
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.context["active_customers"], 0)
        self.assertEqual(resp.context["retention_rate"], 0)
