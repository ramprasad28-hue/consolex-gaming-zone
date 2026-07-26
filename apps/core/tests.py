# apps/core/tests.py
import datetime
from decimal import Decimal

from django.test import TestCase
from django.urls import reverse

from apps.games.models import Game, GameConsole
from apps.memberships.models import Membership
from apps.tournaments.models import Tournament
from apps.users.models import User


class HomeViewTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(email="home@test.com", password="x")
        self.console = GameConsole.objects.create(
            name="PS5 Lounge 1", console_type="PS5",
            hourly_rate_weekday=Decimal("130.00"),
            hourly_rate_weekend=Decimal("150.00"),
        )
        Membership.objects.filter(name="test").delete()

    def test_home_returns_200(self):
        resp = self.client.get(reverse("home"))
        self.assertEqual(resp.status_code, 200)

    def test_home_uses_correct_template(self):
        resp = self.client.get(reverse("home"))
        self.assertTemplateUsed(resp, "pages/home.html")

    def test_home_context_has_plans(self):
        Membership.objects.create(
            name="Test Basic", price=Decimal("999.00"), duration_days=30,
            discount_percent=10, included_hours=10,
        )
        resp = self.client.get(reverse("home"))
        self.assertTrue(resp.context["plans"].filter(name="Test Basic").exists())

    def test_home_context_has_tournaments(self):
        Tournament.objects.create(
            title="Test Tourney", game="FIFA",
            date=datetime.datetime(2026, 10, 1),
            prize_pool=Decimal("5000.00"),
            is_active=True,
        )
        resp = self.client.get(reverse("home"))
        titles = [t.title for t in resp.context["tournaments"]]
        self.assertIn("Test Tourney", titles)

    def test_home_context_has_games(self):
        Game.objects.create(
            title="Spider-Man 2", category="action",
            rating=Decimal("4.8"), is_active=True,
        )
        resp = self.client.get(reverse("home"))
        titles = [g.title for g in resp.context["games"]]
        self.assertIn("Spider-Man 2", titles)

    def test_home_excludes_inactive_plans(self):
        p = Membership.objects.create(
            name="Hidden Plan", price=Decimal("0.00"), duration_days=30,
            discount_percent=0, included_hours=0, is_active=False,
        )
        resp = self.client.get(reverse("home"))
        self.assertNotIn(p, resp.context["plans"])

    def test_home_excludes_inactive_tournaments(self):
        t = Tournament.objects.create(
            title="Hidden Tourney", game="FIFA",
            date=datetime.datetime(2026, 10, 1),
            prize_pool=Decimal("0.00"), is_active=False,
        )
        resp = self.client.get(reverse("home"))
        self.assertNotIn(t, resp.context["tournaments"])

    def test_home_excludes_inactive_games(self):
        g = Game.objects.create(
            title="Hidden Game", category="action",
            rating=Decimal("0.0"), is_active=False,
        )
        resp = self.client.get(reverse("home"))
        self.assertNotIn(g, resp.context["games"])

    def test_home_limits_tournaments_to_6(self):
        for i in range(8):
            Tournament.objects.create(
                title=f"T{i}", game="FIFA",
                date=datetime.datetime(2026, 10, i + 1),
                prize_pool=Decimal("100.00"), is_active=True,
            )
        resp = self.client.get(reverse("home"))
        self.assertLessEqual(resp.context["tournaments"].count(), 6)

    def test_home_limits_games_to_12(self):
        for i in range(15):
            Game.objects.create(
                title=f"Game {i}", category="action",
                rating=Decimal("4.0"), is_active=True, sort_order=i,
            )
        resp = self.client.get(reverse("home"))
        self.assertLessEqual(resp.context["games"].count(), 12)
