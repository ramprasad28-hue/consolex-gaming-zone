# apps/staff/tests.py
from decimal import Decimal

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from apps.users.models import User
from apps.games.models import GameConsole, Game
from apps.bookings.models import Booking
from apps.payments.models import Payment
from apps.tournaments.models import Tournament
from apps.memberships.models import Membership, MembershipSubscription, MembershipPayment


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


class BookingListFilterTests(TestCase):
    """Phase 2 — extended booking list filters and CSV export."""

    def setUp(self):
        make_staff()
        self.client.force_login(User.objects.get(email="staff@test.com"))
        self.console = make_console()
        self.customer = User.objects.create_user(
            email="payer@test.com", password="x", phone="9876543210"
        )
        self.booking = Booking.objects.create(
            user=self.customer, game_console=self.console,
            booking_date="2026-08-10", start_time="12:00", end_time="14:00",
            total_cost=Decimal("260.00"), status="confirmed",
        )
        self.payment = Payment.objects.create(
            booking=self.booking, user=self.customer,
            amount=26000, status="captured",
        )

    def test_list_renders_with_stats(self):
        resp = self.client.get(reverse("staff:staff_booking_list"))
        self.assertEqual(resp.status_code, 200)
        self.assertIn("booking_stats", resp.context)
        self.assertEqual(resp.context["booking_stats"]["total"], 1)
        self.assertIn("payment_status_choices", resp.context)

    def test_filter_by_payment_status(self):
        resp = self.client.get(
            reverse("staff:staff_booking_list"), {"payment_status": "captured"}
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.context["page_obj"].object_list), 1)

    def test_filter_by_payment_status_excludes(self):
        Payment.objects.filter(booking=self.booking).update(status="failed")
        resp = self.client.get(
            reverse("staff:staff_booking_list"), {"payment_status": "captured"}
        )
        self.assertEqual(len(resp.context["page_obj"].object_list), 0)

    def test_search_by_phone(self):
        resp = self.client.get(
            reverse("staff:staff_booking_list"), {"q": "9876543210"}
        )
        self.assertEqual(len(resp.context["page_obj"].object_list), 1)

    def test_filter_by_date_range(self):
        resp = self.client.get(
            reverse("staff:staff_booking_list"),
            {"date_from": "2026-08-01", "date_to": "2026-08-31"},
        )
        self.assertEqual(len(resp.context["page_obj"].object_list), 1)

    def test_filter_by_date_range_excludes(self):
        resp = self.client.get(
            reverse("staff:staff_booking_list"),
            {"date_from": "2026-09-01", "date_to": "2026-09-30"},
        )
        self.assertEqual(len(resp.context["page_obj"].object_list), 0)

    def test_export_csv(self):
        resp = self.client.get(reverse("staff:staff_booking_export"))
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp["Content-Type"], "text/csv; charset=utf-8")
        self.assertContains(resp, "payer@test.com")
        self.assertContains(resp, "9876543210")
        self.assertContains(resp, "Booking ID")

    def test_export_respects_filters(self):
        resp = self.client.get(
            reverse("staff:staff_booking_export"), {"payment_status": "failed"}
        )
        self.assertEqual(resp.status_code, 200)
        self.assertNotContains(resp, "payer@test.com")


def make_game(title="God of War", category="action", is_active=True, rating=Decimal("9.0")):
    return Game.objects.create(
        title=title, category=category, is_active=is_active,
        rating=rating, badge="", sort_order=0,
    )


def make_tournament(
    title="Warzone Weekend",
    game="Call of Duty",
    status="registrations_open",
    prize_pool=Decimal("5000.00"),
    total_slots=16,
    registered_slots=4,
):
    return Tournament.objects.create(
        title=title, game=game,
        date=timezone.now() + timezone.timedelta(days=5),
        status=status, prize_pool=prize_pool,
        total_slots=total_slots, registered_slots=registered_slots,
    )


class GameLibraryTests(TestCase):
    """Phase 3 — game library filters, stats and archive toggle."""

    def setUp(self):
        make_staff()
        self.client.force_login(User.objects.get(email="staff@test.com"))
        self.game = make_game()
        make_game("Gran Turismo", category="racing", is_active=False, rating=Decimal("0"))

    def test_list_renders_with_stats(self):
        resp = self.client.get(reverse("staff:staff_game_list"))
        self.assertEqual(resp.status_code, 200)
        self.assertIn("game_stats", resp.context)
        self.assertEqual(resp.context["game_stats"]["total"], 2)
        self.assertEqual(resp.context["game_stats"]["active"], 1)
        self.assertEqual(resp.context["game_stats"]["archived"], 1)
        self.assertIn("consoles", resp.context)

    def test_filter_by_category(self):
        resp = self.client.get(
            reverse("staff:staff_game_list"), {"category": "racing"}
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.context["page_obj"].object_list), 1)
        self.assertEqual(resp.context["page_obj"].object_list[0].title, "Gran Turismo")

    def test_filter_by_active(self):
        resp = self.client.get(
            reverse("staff:staff_game_list"), {"active": "archived"}
        )
        self.assertEqual(len(resp.context["page_obj"].object_list), 1)
        self.assertEqual(resp.context["page_obj"].object_list[0].title, "Gran Turismo")

    def test_search_by_title(self):
        resp = self.client.get(
            reverse("staff:staff_game_list"), {"q": "gran"}
        )
        self.assertEqual(len(resp.context["page_obj"].object_list), 1)

    def test_detail_renders(self):
        resp = self.client.get(
            reverse("staff:staff_game_detail", args=[self.game.id])
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.context["game"].title, "God of War")

    def test_anonymous_cannot_access_detail(self):
        self.client.logout()
        resp = self.client.get(
            reverse("staff:staff_game_detail", args=[self.game.id])
        )
        self.assertNotEqual(resp.status_code, 200)

    def test_toggle_active_archives(self):
        resp = self.client.post(
            reverse("staff:staff_game_toggle_active", args=[self.game.id])
        )
        self.assertEqual(resp.status_code, 302)
        self.game.refresh_from_db()
        self.assertFalse(self.game.is_active)

    def test_toggle_active_restores(self):
        archived = Game.objects.get(title="Gran Turismo")
        self.client.post(
            reverse("staff:staff_game_toggle_active", args=[archived.id])
        )
        archived.refresh_from_db()
        self.assertTrue(archived.is_active)

    def test_toggle_active_requires_post(self):
        resp = self.client.get(
            reverse("staff:staff_game_toggle_active", args=[self.game.id])
        )
        self.assertEqual(resp.status_code, 405)


class TournamentManagementTests(TestCase):
    """Phase 3 — tournament filters, stats and status updates."""

    def setUp(self):
        make_staff()
        self.client.force_login(User.objects.get(email="staff@test.com"))
        self.tournament = make_tournament()
        make_tournament(title="Old Final", game="FIFA 24", status="completed", prize_pool=Decimal("1000.00"))

    def test_list_renders_with_stats(self):
        resp = self.client.get(reverse("staff:staff_tournament_list"))
        self.assertEqual(resp.status_code, 200)
        self.assertIn("tournament_stats", resp.context)
        self.assertEqual(resp.context["tournament_stats"]["total"], 2)
        self.assertEqual(resp.context["tournament_stats"]["open"], 1)
        self.assertEqual(resp.context["tournament_stats"]["completed"], 1)
        self.assertEqual(resp.context["tournament_stats"]["filled"], 25)

    def test_filter_by_status(self):
        resp = self.client.get(
            reverse("staff:staff_tournament_list"), {"status": "completed"}
        )
        self.assertEqual(len(resp.context["page_obj"].object_list), 1)
        self.assertEqual(resp.context["page_obj"].object_list[0].title, "Old Final")

    def test_search_by_game(self):
        resp = self.client.get(
            reverse("staff:staff_tournament_list"), {"q": "Call of Duty"}
        )
        self.assertEqual(len(resp.context["page_obj"].object_list), 1)

    def test_detail_renders_with_slots(self):
        resp = self.client.get(
            reverse("staff:staff_tournament_detail", args=[self.tournament.id])
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.context["tournament"].slots_filled_percent, 25)

    def test_anonymous_cannot_access_detail(self):
        self.client.logout()
        resp = self.client.get(
            reverse("staff:staff_tournament_detail", args=[self.tournament.id])
        )
        self.assertNotEqual(resp.status_code, 200)

    def test_set_status_marks_full(self):
        resp = self.client.post(
            reverse("staff:staff_tournament_set_status", args=[self.tournament.id]),
            {"status": "full"},
        )
        self.assertEqual(resp.status_code, 302)
        self.tournament.refresh_from_db()
        self.assertEqual(self.tournament.status, "full")

    def test_set_status_rejects_invalid(self):
        resp = self.client.post(
            reverse("staff:staff_tournament_set_status", args=[self.tournament.id]),
            {"status": "bogus"},
        )
        self.assertEqual(resp.status_code, 302)
        self.tournament.refresh_from_db()
        self.assertEqual(self.tournament.status, "registrations_open")

    def test_set_status_requires_post(self):
        resp = self.client.get(
            reverse("staff:staff_tournament_set_status", args=[self.tournament.id])
        )
        self.assertEqual(resp.status_code, 405)


def make_plan(
    name="Pro Play",
    price=Decimal("1499.00"),
    duration_days=30,
    tier_level=1,
    is_active=True,
    is_popular=False,
    discount_percent=0,
    priority_booking=False,
    included_hours=10,
    weekend_hours=4,
    bonus_hours=2,
):
    return Membership.objects.create(
        name=name, price=price, duration_days=duration_days,
        tier_level=tier_level, is_active=is_active, is_popular=is_popular,
        discount_percent=discount_percent, priority_booking=priority_booking,
        included_hours=included_hours, weekend_hours=weekend_hours,
        bonus_hours=bonus_hours, badge_color="",
    )


class CustomerManagementTests(TestCase):
    """Phase 4 — customer list stats, filters, sorts, pagination and detail."""

    def setUp(self):
        make_staff()
        self.client.force_login(User.objects.get(email="staff@test.com"))
        self.customer = User.objects.create_user(
            email="player@test.com", password="x", first_name="Aarav", last_name="Sharma",
            phone="9876543210",
        )
        User.objects.create_user(
            email="other@test.com", password="x", first_name="Zoya", last_name="Khan",
            is_active=False,
        )
        self.console = make_console()
        self.booking = Booking.objects.create(
            user=self.customer, game_console=self.console,
            booking_date="2026-08-10", start_time="12:00", end_time="14:00",
            total_cost=Decimal("260.00"), status="confirmed",
        )
        Payment.objects.create(
            booking=self.booking, user=self.customer,
            amount=26000, status="captured",
        )
        self.plan = make_plan()
        MembershipSubscription.objects.create(
            user=self.customer, plan=self.plan,
            status="active",
            started_at=timezone.now(),
            expires_at=timezone.now() + timezone.timedelta(days=20),
        )

    def test_list_renders_with_stats(self):
        resp = self.client.get(reverse("staff:staff_customer_list"))
        self.assertEqual(resp.status_code, 200)
        self.assertIn("customer_stats", resp.context)
        self.assertEqual(resp.context["customer_stats"]["total"], 3)
        self.assertEqual(resp.context["customer_stats"]["active"], 2)
        self.assertEqual(resp.context["customer_stats"]["members"], 1)
        self.assertIn("page_obj", resp.context)

    def test_search_by_email(self):
        resp = self.client.get(
            reverse("staff:staff_customer_list"), {"q": "player@test.com"}
        )
        self.assertEqual(len(resp.context["page_obj"].object_list), 1)
        self.assertEqual(resp.context["page_obj"].object_list[0].email, "player@test.com")

    def test_search_by_phone(self):
        resp = self.client.get(
            reverse("staff:staff_customer_list"), {"q": "9876543210"}
        )
        self.assertEqual(len(resp.context["page_obj"].object_list), 1)

    def test_filter_membership_active(self):
        resp = self.client.get(
            reverse("staff:staff_customer_list"), {"membership": "active"}
        )
        self.assertEqual(len(resp.context["page_obj"].object_list), 1)
        self.assertEqual(resp.context["page_obj"].object_list[0].active_plan_name, "Pro Play")

    def test_filter_membership_none(self):
        resp = self.client.get(
            reverse("staff:staff_customer_list"), {"membership": "none"}
        )
        self.assertEqual(len(resp.context["page_obj"].object_list), 2)

    def test_filter_status_inactive(self):
        resp = self.client.get(
            reverse("staff:staff_customer_list"), {"status": "inactive"}
        )
        self.assertEqual(len(resp.context["page_obj"].object_list), 1)
        self.assertEqual(resp.context["page_obj"].object_list[0].email, "other@test.com")

    def test_sort_highest_spend(self):
        resp = self.client.get(
            reverse("staff:staff_customer_list"), {"sort": "-total_spent"}
        )
        rows = resp.context["page_obj"].object_list
        self.assertEqual(rows[0].total_spent, 26000)

    def test_sort_by_name(self):
        resp = self.client.get(
            reverse("staff:staff_customer_list"), {"sort": "name"}
        )
        rows = list(resp.context["page_obj"].object_list)
        names = [r.first_name for r in rows if r.first_name]
        self.assertEqual(names[0], "Aarav")
        self.assertEqual(names[1], "Zoya")

    def test_detail_renders_context(self):
        resp = self.client.get(
            reverse("staff:staff_customer_detail", args=[self.customer.id])
        )
        self.assertEqual(resp.status_code, 200)
        self.assertIn("totals", resp.context)
        self.assertEqual(resp.context["totals"]["booking_total"], 1)
        self.assertEqual(resp.context["totals"]["spent"], 26000)
        self.assertIn("active_subscription", resp.context)
        self.assertIsNotNone(resp.context["active_subscription"])
        self.assertIn("timeline", resp.context)
        self.assertIn("payments", resp.context)
        self.assertIn("subscriptions", resp.context)

    def test_anonymous_cannot_access_detail(self):
        self.client.logout()
        resp = self.client.get(
            reverse("staff:staff_customer_detail", args=[self.customer.id])
        )
        self.assertNotEqual(resp.status_code, 200)

    def test_pagination_preserves_page(self):
        resp = self.client.get(
            reverse("staff:staff_customer_list"), {"page": "1"}
        )
        self.assertEqual(resp.status_code, 200)


class MembershipManagementTests(TestCase):
    """Phase 4 — membership plan cards, stats, expiring list and toggle."""

    def setUp(self):
        make_staff()
        self.client.force_login(User.objects.get(email="staff@test.com"))
        self.plan = make_plan()
        make_plan(
            name="Elite", price=Decimal("4999.00"),
            tier_level=3, is_popular=True, discount_percent=15,
        )
        self.member = User.objects.create_user(email="m@test.com", password="x")
        MembershipSubscription.objects.create(
            user=self.member, plan=self.plan,
            status="active",
            started_at=timezone.now(),
            expires_at=timezone.now() + timezone.timedelta(days=12),
        )
        MembershipPayment.objects.create(
            subscription=MembershipSubscription.objects.first(),
            user=self.member, amount=149900, status="captured",
            created_at=timezone.now(),
        )

    def test_list_renders_with_stats(self):
        resp = self.client.get(reverse("staff:staff_membership_list"))
        self.assertEqual(resp.status_code, 200)
        self.assertIn("membership_stats", resp.context)
        self.assertEqual(resp.context["membership_stats"]["plans"], 5)
        self.assertEqual(resp.context["membership_stats"]["active_plans"], 5)
        self.assertEqual(resp.context["membership_stats"]["members"], 1)
        self.assertIn("expiring_soon", resp.context)
        self.assertIn("subscriptions", resp.context)

    def test_revenue_30_captured(self):
        resp = self.client.get(reverse("staff:staff_membership_list"))
        self.assertEqual(resp.context["membership_stats"]["revenue_30"], 1499.0)

    def test_expiring_soon_list(self):
        resp = self.client.get(reverse("staff:staff_membership_list"))
        self.assertEqual(len(resp.context["expiring_soon"]), 1)

    def test_filter_status_inactive(self):
        make_plan(name="Retired", price=Decimal("999.00"), is_active=False)
        resp = self.client.get(
            reverse("staff:staff_membership_list"), {"status": "inactive"}
        )
        self.assertEqual(len(resp.context["memberships"]), 1)
        self.assertEqual(resp.context["memberships"][0].name, "Retired")

    def test_search_by_name(self):
        resp = self.client.get(
            reverse("staff:staff_membership_list"), {"q": "elite"}
        )
        self.assertEqual(len(resp.context["memberships"]), 1)
        self.assertEqual(resp.context["memberships"][0].name, "Elite")

    def test_sort_by_members(self):
        resp = self.client.get(
            reverse("staff:staff_membership_list"), {"sort": "-members"}
        )
        rows = list(resp.context["memberships"])
        self.assertEqual(rows[0].active_member_count, 1)

    def test_plan_detail_renders(self):
        resp = self.client.get(
            reverse("staff:staff_membership_detail", args=[self.plan.id])
        )
        self.assertEqual(resp.status_code, 200)
        self.assertIn("plan", resp.context)
        self.assertEqual(resp.context["plan"].active_member_count, 1)
        self.assertEqual(len(resp.context["members"]), 1)

    def test_anonymous_cannot_access_plan_detail(self):
        self.client.logout()
        resp = self.client.get(
            reverse("staff:staff_membership_detail", args=[self.plan.id])
        )
        self.assertNotEqual(resp.status_code, 200)

    def test_toggle_active_deactivates(self):
        resp = self.client.post(
            reverse("staff:staff_membership_toggle_active", args=[self.plan.id])
        )
        self.assertEqual(resp.status_code, 302)
        self.plan.refresh_from_db()
        self.assertFalse(self.plan.is_active)

    def test_toggle_active_reactivates(self):
        self.plan.is_active = False
        self.plan.save(update_fields=["is_active"])
        self.client.post(
            reverse("staff:staff_membership_toggle_active", args=[self.plan.id])
        )
        self.plan.refresh_from_db()
        self.assertTrue(self.plan.is_active)

    def test_toggle_active_requires_post(self):
        resp = self.client.get(
            reverse("staff:staff_membership_toggle_active", args=[self.plan.id])
        )
        self.assertEqual(resp.status_code, 405)

    def test_toggle_active_next_redirect_guard(self):
        resp = self.client.post(
            reverse("staff:staff_membership_toggle_active", args=[self.plan.id]),
            {"next": "https://evil.example/"},
        )
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(resp.url, reverse("staff:staff_membership_list"))

    def test_toggle_active_next_redirect_internal(self):
        resp = self.client.post(
            reverse("staff:staff_membership_toggle_active", args=[self.plan.id]),
            {"next": reverse("staff:staff_membership_detail", args=[self.plan.id])},
        )
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(resp.url, reverse("staff:staff_membership_detail", args=[self.plan.id]))
