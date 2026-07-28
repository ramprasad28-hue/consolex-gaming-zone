from django.shortcuts import render, get_object_or_404
from django.core.paginator import Paginator
from django.db.models import Q
from .models import Game, GameConsole


def game_list(request):
    games = Game.objects.filter(is_active=True)

    query = request.GET.get("q", "").strip()
    category = request.GET.get("category", "")
    badge = request.GET.get("badge", "")
    sort = request.GET.get("sort", "popular")

    if query:
        games = games.filter(
            Q(title__icontains=query) | Q(category__icontains=query)
        )

    if category:
        games = games.filter(category=category)

    if badge:
        games = games.filter(badge=badge)

    sort_map = {
        "newest": "-created_at",
        "rating": "-rating",
        "title": "title",
        "popular": "sort_order",
    }
    games = games.order_by(sort_map.get(sort, "sort_order"), "title")

    paginator = Paginator(games, 12)
    page_obj = paginator.get_page(request.GET.get("page"))

    consoles = GameConsole.objects.filter(is_active=True)

    return render(request, "games/game_list.html", {
        "page_obj": page_obj,
        "query": query,
        "category": category,
        "badge": badge,
        "sort": sort,
        "consoles": consoles,
        "categories": Game.CATEGORIES,
        "total_count": paginator.count,
    })


def game_detail(request, pk):
    game = get_object_or_404(Game, pk=pk, is_active=True)

    similar_games = Game.objects.filter(
        category=game.category, is_active=True
    ).exclude(pk=pk)[:4]

    return render(request, "games/game_detail.html", {
        "game": game,
        "similar_games": similar_games,
    })
