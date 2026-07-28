from django.shortcuts import render, get_object_or_404
from django.core.paginator import Paginator
from django.db.models import Q
from .models import Tournament


def tournament_list(request):
    tournaments = Tournament.objects.filter(is_active=True)

    query = request.GET.get("q", "").strip()
    status = request.GET.get("status", "")
    sort = request.GET.get("sort", "date")

    if query:
        tournaments = tournaments.filter(
            Q(title__icontains=query) | Q(game__icontains=query)
        )

    if status:
        tournaments = tournaments.filter(status=status)

    sort_map = {
        "date": "date",
        "prize": "-prize_pool",
        "title": "title",
        "newest": "-created_at",
    }
    tournaments = tournaments.order_by(sort_map.get(sort, "date"))

    paginator = Paginator(tournaments, 9)
    page_obj = paginator.get_page(request.GET.get("page"))

    return render(request, "tournaments/tournament_list.html", {
        "page_obj": page_obj,
        "query": query,
        "status": status,
        "sort": sort,
        "total_count": paginator.count,
        "statuses": Tournament.Status.choices,
    })


def tournament_detail(request, pk):
    tournament = get_object_or_404(Tournament, pk=pk, is_active=True)

    similar = Tournament.objects.filter(
        game=tournament.game, is_active=True
    ).exclude(pk=pk)[:3]

    return render(request, "tournaments/tournament_detail.html", {
        "tournament": tournament,
        "similar_tournaments": similar,
    })
