from django.shortcuts import render

from apps.memberships.models import Membership
from apps.tournaments.models import Tournament
from apps.games.models import Game


def home(request):
    plans = Membership.objects.filter(is_active=True)
    tournaments = Tournament.objects.filter(is_active=True).order_by("date")[:6]
    games = Game.objects.filter(is_active=True).order_by("sort_order", "title")[:12]
    return render(request, "pages/home.html", {
        "plans": plans,
        "tournaments": tournaments,
        "games": games,
    })
