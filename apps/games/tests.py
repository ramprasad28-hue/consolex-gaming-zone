# apps/games/tests.py
from django.test import TestCase

from apps.games.models import GameConsole
from apps.games.services import GameService
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
