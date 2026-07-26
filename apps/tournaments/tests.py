# apps/tournaments/tests.py
import datetime
from decimal import Decimal

from django.test import TestCase
from django.core.exceptions import ValidationError

from apps.tournaments.models import Tournament


class TournamentModelTests(TestCase):
    def setUp(self):
        self.tournament = Tournament.objects.create(
            title="CS2 Launch Tournament",
            game="Counter-Strike 2",
            description="5v5 competitive",
            date=datetime.datetime(2026, 9, 15, 18, 0),
            prize_pool=Decimal("5000.00"),
            total_slots=16,
            registered_slots=8,
            status=Tournament.Status.REGISTRATIONS_OPEN,
        )

    def test_str(self):
        self.assertEqual(str(self.tournament), "CS2 Launch Tournament")

    def test_ordering(self):
        Tournament.objects.create(
            title="Later", game="FIFA", date=datetime.datetime(2026, 12, 1),
            prize_pool=Decimal("1000.00"),
        )
        Tournament.objects.create(
            title="Earlier", game="COD", date=datetime.datetime(2026, 6, 1),
            prize_pool=Decimal("1000.00"),
        )
        titles = list(Tournament.objects.values_list("title", flat=True))
        self.assertEqual(titles[0], "Earlier")
        self.assertEqual(titles[-1], "Later")

    def test_clean_registered_exceeds_total(self):
        self.tournament.registered_slots = 20
        with self.assertRaises(ValidationError):
            self.tournament.clean()

    def test_clean_registered_equals_total(self):
        self.tournament.registered_slots = 16
        self.tournament.clean()

    def test_image_src_with_image_url(self):
        t = Tournament(image_url="https://example.com/img.jpg")
        self.assertEqual(t.image_src, "https://example.com/img.jpg")

    def test_image_src_empty(self):
        t = Tournament()
        self.assertEqual(t.image_src, "")

    def test_slots_remaining(self):
        self.assertEqual(self.tournament.slots_remaining, 8)

    def test_slots_remaining_zero(self):
        self.tournament.registered_slots = 16
        self.assertEqual(self.tournament.slots_remaining, 0)

    def test_slots_remaining_no_negative(self):
        self.tournament.registered_slots = 20
        self.assertEqual(self.tournament.slots_remaining, 0)

    def test_slots_filled_percent(self):
        self.assertEqual(self.tournament.slots_filled_percent, 50)

    def test_slots_filled_percent_zero_total(self):
        t = Tournament(total_slots=0, registered_slots=0)
        self.assertEqual(t.slots_filled_percent, 0)

    def test_slots_filled_percent_full(self):
        self.tournament.registered_slots = 16
        self.assertEqual(self.tournament.slots_filled_percent, 100)

    def test_status_label(self):
        self.assertEqual(self.tournament.status_label, "Registrations Open")

    def test_status_css_class_open(self):
        self.assertEqual(self.tournament.status_css_class, "tourney-status-open")

    def test_status_css_class_upcoming(self):
        self.tournament.status = Tournament.Status.UPCOMING
        self.assertEqual(self.tournament.status_css_class, "tourney-status-upcoming")

    def test_btn_css_class_primary(self):
        self.assertEqual(self.tournament.btn_css_class, "tourney-btn-primary")

    def test_btn_css_class_ghost(self):
        self.tournament.status = Tournament.Status.UPCOMING
        self.assertEqual(self.tournament.btn_css_class, "tourney-btn-ghost")

    def test_btn_label_register(self):
        self.assertEqual(self.tournament.btn_label, "Register Now")

    def test_btn_label_notify(self):
        self.tournament.status = Tournament.Status.UPCOMING
        self.assertEqual(self.tournament.btn_label, "Notify Me")

    def test_btn_label_sold_out(self):
        self.tournament.status = Tournament.Status.FULL
        self.assertEqual(self.tournament.btn_label, "Sold Out")

    def test_btn_label_live(self):
        self.tournament.status = Tournament.Status.IN_PROGRESS
        self.assertEqual(self.tournament.btn_label, "Live Now")

    def test_btn_label_completed(self):
        self.tournament.status = Tournament.Status.COMPLETED
        self.assertEqual(self.tournament.btn_label, "Completed")

    def test_btn_label_cancelled(self):
        self.tournament.status = Tournament.Status.CANCELLED
        self.assertEqual(self.tournament.btn_label, "Cancelled")

    def test_prize_pool_zero(self):
        t = Tournament(prize_pool=Decimal("0.00"))
        self.assertEqual(t.prize_pool, Decimal("0.00"))

    def test_is_active_default(self):
        t = Tournament()
        self.assertTrue(t.is_active)

    def test_total_slots_default(self):
        t = Tournament()
        self.assertEqual(t.total_slots, 16)

    def test_registered_slots_default(self):
        t = Tournament()
        self.assertEqual(t.registered_slots, 0)


class TournamentQuerySetTests(TestCase):
    def setUp(self):
        self.active_open = Tournament.objects.create(
            title="Active Open", game="FIFA",
            date=datetime.datetime(2026, 9, 1),
            prize_pool=Decimal("1000.00"),
            is_active=True,
            status=Tournament.Status.REGISTRATIONS_OPEN,
        )
        self.active_upcoming = Tournament.objects.create(
            title="Active Upcoming", game="COD",
            date=datetime.datetime(2026, 10, 1),
            prize_pool=Decimal("2000.00"),
            is_active=True,
            status=Tournament.Status.UPCOMING,
        )
        self.inactive = Tournament.objects.create(
            title="Inactive", game="GOW",
            date=datetime.datetime(2026, 11, 1),
            prize_pool=Decimal("500.00"),
            is_active=False,
            status=Tournament.Status.REGISTRATIONS_OPEN,
        )
        self.completed = Tournament.objects.create(
            title="Completed", game="RDR2",
            date=datetime.datetime(2026, 1, 1),
            prize_pool=Decimal("3000.00"),
            is_active=True,
            status=Tournament.Status.COMPLETED,
        )

    def test_active(self):
        qs = Tournament.objects.active()
        self.assertEqual(qs.count(), 3)

    def test_upcoming(self):
        qs = Tournament.objects.upcoming()
        self.assertEqual(qs.count(), 2)
        titles = list(qs.values_list("title", flat=True))
        self.assertIn("Active Open", titles)
        self.assertIn("Active Upcoming", titles)
        self.assertNotIn("Inactive", titles)
        self.assertNotIn("Completed", titles)
