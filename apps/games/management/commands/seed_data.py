import datetime
from decimal import Decimal
from django.core.management.base import BaseCommand
from django.utils import timezone
from apps.games.models import Game, GameConsole
from apps.tournaments.models import Tournament


class Command(BaseCommand):
    help = "Seed demo data: games, consoles, and tournaments"

    def add_arguments(self, parser):
        parser.add_argument("--clear", action="store_true", help="Clear existing data first")

    def handle(self, *args, **options):
        if options["clear"]:
            Game.objects.all().delete()
            GameConsole.objects.all().delete()
            Tournament.objects.all().delete()
            self.stdout.write(self.style.WARNING("Cleared all games, consoles, and tournaments."))

        self._seed_consoles()
        self._seed_games()
        self._seed_tournaments()

        self.stdout.write(self.style.SUCCESS(
            f"Done. Games: {Game.objects.count()}, "
            f"Consoles: {GameConsole.objects.count()}, "
            f"Tournaments: {Tournament.objects.count()}"
        ))

    def _seed_consoles(self):
        consoles = [
            {
                "name": "PS5 Station 1",
                "console_type": "PS5",
                "hourly_rate_weekday": Decimal("130.00"),
                "hourly_rate_weekend": Decimal("150.00"),
            },
            {
                "name": "PS5 Station 2",
                "console_type": "PS5",
                "hourly_rate_weekday": Decimal("130.00"),
                "hourly_rate_weekend": Decimal("150.00"),
            },
            {
                "name": "PS5 Station 3",
                "console_type": "PS5",
                "hourly_rate_weekday": Decimal("130.00"),
                "hourly_rate_weekend": Decimal("150.00"),
            },
            {
                "name": "PS5 VIP Room",
                "console_type": "PS5",
                "hourly_rate_weekday": Decimal("180.00"),
                "hourly_rate_weekend": Decimal("220.00"),
            },
            {
                "name": "Xbox Series X",
                "console_type": "XBOX",
                "hourly_rate_weekday": Decimal("120.00"),
                "hourly_rate_weekend": Decimal("140.00"),
            },
        ]
        created = 0
        for data in consoles:
            _, was_created = GameConsole.objects.get_or_create(
                name=data["name"],
                defaults=data,
            )
            if was_created:
                created += 1
        self.stdout.write(f"  Consoles: {created} created, {len(consoles) - created} already existed.")

    def _seed_games(self):
        games = [
            {
                "title": "God of War Ragnarok",
                "category": "adventure",
                "rating": Decimal("9.6"),
                "badge": "top_rated",
                "sort_order": 1,
                "image": "games/kratos.png",
            },
            {
                "title": "Call of Duty: MW III",
                "category": "action",
                "rating": Decimal("8.8"),
                "badge": "popular",
                "sort_order": 2,
                "image": "games/cod.jpg",
            },
            {
                "title": "Spider-Man 2",
                "category": "action",
                "rating": Decimal("9.4"),
                "badge": "new",
                "sort_order": 3,
                "image": "png for web/spiderman.png",
            },
            {
                "title": "GTA V",
                "category": "action",
                "rating": Decimal("9.2"),
                "badge": "popular",
                "sort_order": 4,
                "image": "png for web/gtav.png",
            },
            {
                "title": "Ghost of Tsushima",
                "category": "adventure",
                "rating": Decimal("9.3"),
                "badge": "",
                "sort_order": 5,
                "image": "png for web/ghost.png",
            },
            {
                "title": "Red Dead Redemption 2",
                "category": "adventure",
                "rating": Decimal("9.7"),
                "badge": "top_rated",
                "sort_order": 6,
                "image": "png for web/arthur.png",
            },
            {
                "title": "EA FC 25",
                "category": "sports",
                "rating": Decimal("8.5"),
                "badge": "new",
                "sort_order": 7,
                "image": "png for web/ronald.png",
            },
            {
                "title": "A Way Out",
                "category": "coop",
                "rating": Decimal("8.6"),
                "badge": "coop",
                "sort_order": 8,
                "image": "",
            },
            {
                "title": "Resident Evil Village",
                "category": "horror",
                "rating": Decimal("9.1"),
                "badge": "",
                "sort_order": 9,
                "image": "",
            },
            {
                "title": "Need for Speed Unbound",
                "category": "racing",
                "rating": Decimal("8.2"),
                "badge": "",
                "sort_order": 10,
                "image": "",
            },
            {
                "title": "FIFA 23",
                "category": "sports",
                "rating": Decimal("8.4"),
                "badge": "",
                "sort_order": 11,
                "image": "",
            },
            {
                "title": "It Takes Two",
                "category": "coop",
                "rating": Decimal("8.9"),
                "badge": "coop",
                "sort_order": 12,
                "image": "",
            },
        ]
        created = 0
        for data in games:
            _, was_created = Game.objects.get_or_create(
                title=data["title"],
                defaults=data,
            )
            if was_created:
                created += 1
        self.stdout.write(f"  Games: {created} created, {len(games) - created} already existed.")

    def _seed_tournaments(self):
        now = timezone.now()
        tournaments = [
            {
                "title": "COD Championship — Erode Finals",
                "game": "Call of Duty: MW III",
                "description": "3v3 Search & Destroy tournament. Entry fee included. Top 3 teams win cash prizes.",
                "date": now + datetime.timedelta(days=14),
                "prize_pool": Decimal("15000.00"),
                "total_slots": 16,
                "registered_slots": 12,
                "status": Tournament.Status.REGISTRATIONS_OPEN,
                "is_active": True,
            },
            {
                "title": "FIFA Friday Knockout",
                "game": "EA FC 25",
                "description": "1v1 FIFA knockout bracket. Best of 3 in finals. Open to all skill levels.",
                "date": now + datetime.timedelta(days=5),
                "prize_pool": Decimal("5000.00"),
                "total_slots": 32,
                "registered_slots": 28,
                "status": Tournament.Status.REGISTRATIONS_OPEN,
                "is_active": True,
            },
            {
                "title": "Spider-Man Speed Run Challenge",
                "game": "Spider-Man 2",
                "description": "Complete the first chapter fastest. Time trial format with live leaderboard.",
                "date": now + datetime.timedelta(days=21),
                "prize_pool": Decimal("3000.00"),
                "total_slots": 20,
                "registered_slots": 0,
                "status": Tournament.Status.UPCOMING,
                "is_active": True,
            },
            {
                "title": "GTA V Heist Challenge",
                "game": "GTA V Online",
                "description": "4-player teams race to complete The Diamond Casino Heist with max payout.",
                "date": now + datetime.timedelta(days=30),
                "prize_pool": Decimal("10000.00"),
                "total_slots": 12,
                "registered_slots": 0,
                "status": Tournament.Status.UPCOMING,
                "is_active": True,
            },
        ]
        created = 0
        for data in tournaments:
            _, was_created = Tournament.objects.get_or_create(
                title=data["title"],
                defaults=data,
            )
            if was_created:
                created += 1
        self.stdout.write(f"  Tournaments: {created} created, {len(tournaments) - created} already existed.")
