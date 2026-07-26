# apps/games/tests.py
from decimal import Decimal
from django.test import TestCase

from apps.games.models import Game, GameConsole
from apps.games.services import GameService
from apps.tournaments.models import Tournament
from apps.common.exceptions import ConsoleNotFoundError


class GameServiceTests(TestCase):
    def setUp(self):
        self.ps5 = GameConsole.objects.create(
            name="PS5 Setup 1", console_type="PS5",
            hourly_rate_weekday=300, hourly_rate_weekend=400,
        )
        self.ps4 = GameConsole.objects.create(
            name="PS4 Setup 1", console_type="PS4",
            hourly_rate_weekday=200, hourly_rate_weekend=250,
            is_active=False,
        )

    def test_list_active_consoles(self):
        consoles = GameService.list_active_consoles()
        self.assertEqual(consoles.count(), 1)
        self.assertEqual(consoles.first(), self.ps5)

    def test_get_console_success(self):
        console = GameService.get_console(self.ps5.id)
        self.assertEqual(console.name, "PS5 Setup 1")

    def test_get_console_not_found(self):
        with self.assertRaises(ConsoleNotFoundError):
            GameService.get_console(9999)

    def test_get_console_inactive(self):
        with self.assertRaises(ConsoleNotFoundError):
            GameService.get_console(self.ps4.id)


class GameConsoleModelTests(TestCase):
    def test_str(self):
        console = GameConsole.objects.create(
            name="Test Console", console_type="PS5",
            hourly_rate_weekday=300, hourly_rate_weekend=400,
        )
        self.assertEqual(str(console), "Test Console")

    def test_rate_for_date_weekday(self):
        from datetime import date
        console = GameConsole.objects.create(
            name="Test", console_type="PS5",
            hourly_rate_weekday=300, hourly_rate_weekend=400,
        )
        from decimal import Decimal
        self.assertEqual(console.rate_for_date(date(2026, 7, 22)), Decimal("300"))  # Wednesday

    def test_rate_for_date_weekend(self):
        from datetime import date
        console = GameConsole.objects.create(
            name="Test", console_type="PS5",
            hourly_rate_weekday=300, hourly_rate_weekend=400,
        )
        from decimal import Decimal
        self.assertEqual(console.rate_for_date(date(2026, 7, 25)), Decimal("400"))  # Saturday


class GameModelTests(TestCase):
    def test_str(self):
        g = Game.objects.create(title="Test Game", category="action", rating=Decimal("8.5"))
        self.assertEqual(str(g), "Test Game")

    def test_image_src_from_image_field(self):
        g = Game.objects.create(title="With File", category="action", image="games/cod.jpg")
        self.assertIn("cod.jpg", g.image_src)

    def test_image_src_from_url(self):
        g = Game.objects.create(title="WithURL", category="action", image_url="https://example.com/img.jpg")
        self.assertEqual(g.image_src, "https://example.com/img.jpg")

    def test_image_src_empty(self):
        g = Game.objects.create(title="NoImg", category="action")
        self.assertEqual(g.image_src, "")

    def test_badge_css_class_mapping(self):
        g = Game.objects.create(title="B", category="action", badge="top_rated")
        self.assertEqual(g.badge_css_class, "game-card-badge-gold")
        g.badge = "popular"
        g.save()
        self.assertEqual(g.badge_css_class, "game-card-badge-red")

    def test_badge_label(self):
        g = Game.objects.create(title="B", category="action", badge="coop")
        self.assertEqual(g.badge_label, "Co-op")

    def test_queryset_active(self):
        Game.objects.create(title="On", category="action", is_active=True)
        Game.objects.create(title="Off", category="action", is_active=False)
        self.assertEqual(Game.objects.active().count(), 1)

    def test_queryset_by_category(self):
        Game.objects.create(title="Act", category="action")
        Game.objects.create(title="Spr", category="sports")
        self.assertEqual(Game.objects.by_category("action").count(), 1)


class SeedDataCommandTests(TestCase):
    def test_seed_creates_data(self):
        from django.core.management import call_command
        call_command("seed_data", verbosity=0)
        self.assertGreaterEqual(Game.objects.count(), 10)
        self.assertGreaterEqual(GameConsole.objects.count(), 4)
        self.assertGreaterEqual(Tournament.objects.count(), 3)

    def test_seed_idempotent(self):
        from django.core.management import call_command
        call_command("seed_data", verbosity=0)
        counts = (Game.objects.count(), GameConsole.objects.count(), Tournament.objects.count())
        call_command("seed_data", verbosity=0)
        self.assertEqual(
            (Game.objects.count(), GameConsole.objects.count(), Tournament.objects.count()),
            counts,
        )

    def test_seed_clear(self):
        from django.core.management import call_command
        call_command("seed_data", verbosity=0)
        call_command("seed_data", "--clear", verbosity=0)
        self.assertGreaterEqual(Game.objects.count(), 10)
