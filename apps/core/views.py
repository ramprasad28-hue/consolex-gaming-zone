from django.http import HttpResponse
from django.shortcuts import render
from django.urls import reverse

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


def robots_txt(request):
    """Search-engine crawl policy. Private/portal areas are disallowed."""
    content = (
        "User-agent: *\n"
        "Allow: /\n"
        "Disallow: /users/\n"
        "Disallow: /bookings/\n"
        "Disallow: /payments/\n"
        "Disallow: /memberships/subscribe/\n"
        "Disallow: /staff/\n"
        "Disallow: /admin/\n"
        "Disallow: /api/\n"
        "Sitemap: {scheme}://{host}/sitemap.xml\n"
    ).format(
        scheme=request.scheme,
        host=request.get_host(),
    )
    return HttpResponse(content, content_type="text/plain")


def sitemap_xml(request):
    """Static sitemap of public, indexable pages."""
    base = "{scheme}://{host}".format(
        scheme=request.scheme,
        host=request.get_host(),
    )
    public_urls = [
        ("/", "1.0", "daily"),
        (reverse("games:game_list"), "0.9", "weekly"),
        (reverse("memberships:plan_list"), "0.9", "weekly"),
        (reverse("tournaments:tournament_list"), "0.8", "daily"),
    ]
    items = []
    for path, priority, freq in public_urls:
        items.append(
            "  <url>\n"
            f"    <loc>{base}{path}</loc>\n"
            f"    <changefreq>{freq}</changefreq>\n"
            f"    <priority>{priority}</priority>\n"
            "  </url>"
        )
    xml = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        + "\n".join(items)
        + "\n</urlset>\n"
    )
    return HttpResponse(xml, content_type="application/xml")
