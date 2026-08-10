import csv
from datetime import date, datetime
from urllib.parse import urlencode

from django.shortcuts import render, get_object_or_404, redirect
from django.core.paginator import Paginator
from django.contrib import messages
from django.db.models import Avg, Count, F, Q, Sum, Max
from django.db.models import ExpressionWrapper, FloatField, OuterRef, Subquery
from django.http import HttpResponse, JsonResponse
from django.utils import timezone
from django.views.decorators.http import require_POST

from apps.bookings.models import Booking
from apps.bookings.services import BookingService
from apps.common.exceptions import ServiceError
from apps.users.models import User
from apps.payments.models import Payment
from apps.memberships.models import (
    Membership, MembershipSubscription, LoyaltyProfile, MembershipPayment
)
from apps.games.models import GameConsole, Game
from apps.tournaments.models import Tournament
from apps.notifications.models import Notification
from apps.cms.models import SiteSettings

from .services import StaffDashboardService, serialize_live_sessions


def staff_dashboard(request):
    data = StaffDashboardService.get_dashboard_data()
    data["site"] = SiteSettings.objects.get_solo()
    data["user_role"] = "Owner" if request.user.is_superuser else "Staff"
    return render(request, "staff/dashboard.html", data)


def filter_bookings(request):
    """Shared queryset builder for the booking list page and CSV export."""
    q = request.GET.get("q", "")
    status_filter = request.GET.get("status", "")
    payment_status = request.GET.get("payment_status", "")
    date_from = request.GET.get("date_from", "")
    date_to = request.GET.get("date_to", "")
    sort = request.GET.get("sort", "-booking_date")

    bookings = Booking.objects.select_related("user", "game_console", "payment").all()

    if q:
        bookings = bookings.filter(
            Q(user__email__icontains=q)
            | Q(user__first_name__icontains=q)
            | Q(user__phone__icontains=q)
            | Q(id__icontains=q)
            | Q(game_console__name__icontains=q)
        )
    if status_filter:
        bookings = bookings.filter(status=status_filter)
    if payment_status:
        bookings = bookings.filter(payment__status=payment_status)
    if date_from:
        try:
            bookings = bookings.filter(
                booking_date__gte=datetime.strptime(date_from, "%Y-%m-%d").date()
            )
        except ValueError:
            pass
    if date_to:
        try:
            bookings = bookings.filter(
                booking_date__lte=datetime.strptime(date_to, "%Y-%m-%d").date()
            )
        except ValueError:
            pass

    valid_sorts = [
        "booking_date", "-booking_date", "start_time", "-start_time",
        "created_at", "-created_at", "total_cost", "-total_cost",
        "status", "-status",
    ]
    if sort in valid_sorts:
        bookings = bookings.order_by(sort)
    else:
        bookings = bookings.order_by("-booking_date")

    return bookings, {
        "q": q,
        "status_filter": status_filter,
        "payment_status": payment_status,
        "date_from": date_from,
        "date_to": date_to,
        "sort": sort,
    }


def booking_list(request):
    bookings, filters = filter_bookings(request)

    paginator = Paginator(bookings, 20)
    page = paginator.get_page(request.GET.get("page"))

    params = {}
    for key in ("q", "status_filter", "payment_status", "date_from", "date_to"):
        if filters[key]:
            params[key if key != "status_filter" else "status"] = filters[key]
    if filters["sort"] != "-booking_date":
        params["sort"] = filters["sort"]

    today = timezone.localdate()
    return render(request, "staff/bookings/list.html", {
        "page_obj": page,
        "qs": urlencode(params),
        "status_choices": Booking.STATUS_CHOICES,
        "payment_status_choices": Payment.Status.choices,
        "booking_stats": {
            "total": Booking.objects.count(),
            "today": Booking.objects.filter(booking_date=today).count(),
            "upcoming": Booking.objects.active().count(),
            "live": Booking.objects.live().count(),
        },
        "today": today,
        **filters,
    })


def booking_export(request):
    """CSV export of bookings honouring the same filters as the list page."""
    bookings, _ = filter_bookings(request)

    response = HttpResponse(content_type="text/csv; charset=utf-8")
    response["Content-Disposition"] = 'attachment; filename="bookings.csv"'
    writer = csv.writer(response)
    writer.writerow([
        "Booking ID", "Customer", "Email", "Phone", "Console", "Console Type",
        "Booking Date", "Start", "End", "Duration (hrs)", "Players",
        "Amount (INR)", "Booking Status", "Payment Status",
        "Payment Amount (INR)", "Razorpay Order ID", "Created At",
    ])
    for b in bookings:
        payment = getattr(b, "payment", None)
        writer.writerow([
            b.id,
            b.user.full_display_name,
            b.user.email,
            b.user.phone or "",
            b.game_console.name if b.game_console else "",
            b.game_console.console_type if b.game_console else "",
            b.booking_date.isoformat(),
            b.start_time.strftime("%H:%M"),
            b.end_time.strftime("%H:%M"),
            b.duration_hours,
            b.number_of_players,
            b.total_cost,
            b.get_status_display(),
            payment.get_status_display() if payment else "",
            payment.amount_rupees if payment else "",
            payment.razorpay_order_id if payment else "",
            b.created_at.strftime("%Y-%m-%d %H:%M:%S") if b.created_at else "",
        ])
    return response


def booking_detail(request, booking_id):
    booking = get_object_or_404(
        Booking.objects.select_related("user", "game_console", "payment"),
        id=booking_id
    )
    return render(request, "staff/bookings/detail.html", {
        "booking": booking,
    })


# ── Live sessions (Ch12) ────────────────────────
@require_POST
def booking_checkin(request, booking_id):
    try:
        booking = BookingService.check_in(booking_id, request.user)
    except ServiceError as e:
        messages.error(request, e.message)
    else:
        messages.success(
            request,
            f"{booking.user.full_display_name} checked in — session is live.",
        )
    return redirect("staff:staff_booking_detail", booking_id=booking_id)


@require_POST
def booking_checkout(request, booking_id):
    try:
        booking = BookingService.check_out(booking_id, request.user)
    except ServiceError as e:
        messages.error(request, e.message)
    else:
        messages.success(
            request,
            f"Session for {booking.user.full_display_name} completed.",
        )
    return redirect("staff:staff_booking_detail", booking_id=booking_id)


def live_sessions(request):
    data = StaffDashboardService.get_dashboard_data()
    data["site"] = SiteSettings.objects.get_solo()
    return render(request, "staff/live_sessions.html", data)


def live_sessions_data(request):
    """JSON feed used by the staff console 30s poll."""
    sessions = Booking.objects.live().select_related("user", "game_console")
    return JsonResponse({
        "count": sessions.count(),
        "sessions": serialize_live_sessions(sessions),
    })


def filter_customers(request):
    """Shared queryset builder for the customer management page."""
    q = request.GET.get("q", "")
    membership_filter = request.GET.get("membership", "")  # active / subscriber / none
    status_filter = request.GET.get("status", "")          # active / inactive
    sort = request.GET.get("sort", "-date_joined")

    active_plan = MembershipSubscription.objects.filter(
        user=OuterRef("pk"),
        status="active",
        expires_at__gt=timezone.now(),
    ).values("plan__name")[:1]

    users = User.objects.annotate(
        booking_count=Count("bookings"),
        total_spent=Sum(
            "payments__amount",
            filter=Q(payments__status__in=["captured", "demo"])
        ),
        last_booking_date=Max("bookings__booking_date"),
        active_plan_name=Subquery(active_plan),
    ).select_related("membership")

    if q:
        users = users.filter(
            Q(email__icontains=q)
            | Q(first_name__icontains=q)
            | Q(last_name__icontains=q)
            | Q(phone__icontains=q)
            | Q(username__icontains=q)
            | Q(id__icontains=q)
        )
    if membership_filter == "active":
        users = users.filter(
            subscriptions__status="active",
            subscriptions__expires_at__gt=timezone.now(),
        ).distinct()
    elif membership_filter == "subscriber":
        users = users.filter(subscriptions__isnull=False).distinct()
    elif membership_filter == "none":
        users = users.filter(subscriptions__isnull=True)
    if status_filter == "active":
        users = users.filter(is_active=True)
    elif status_filter == "inactive":
        users = users.filter(is_active=False)

    valid_sorts = {
        "date_joined": ["date_joined"],
        "-date_joined": ["-date_joined"],
        "email": ["email"],
        "-email": ["-email"],
        "booking_count": ["booking_count", "-date_joined"],
        "-booking_count": ["-booking_count", "-date_joined"],
        "total_spent": ["total_spent", "-date_joined"],
        "-total_spent": ["-total_spent", "-date_joined"],
        "last_login": ["last_login", "-date_joined"],
        "-last_login": ["-last_login", "-date_joined"],
        "name": ["first_name", "last_name", "-date_joined"],
    }
    users = users.order_by(*valid_sorts.get(sort, valid_sorts["-date_joined"]))

    return users, {
        "q": q,
        "membership_filter": membership_filter,
        "status_filter": status_filter,
        "sort": sort,
    }


def customer_list(request):
    users, filters = filter_customers(request)

    paginator = Paginator(users, 20)
    page = paginator.get_page(request.GET.get("page"))

    params = {}
    for key in ("q", "membership_filter", "status_filter"):
        if filters[key]:
            params[key if key != "membership_filter" else "membership"] = filters[key]
    if filters["sort"] != "-date_joined":
        params["sort"] = filters["sort"]

    month_start = timezone.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    return render(request, "staff/customers/list.html", {
        "page_obj": page,
        "qs": urlencode(params),
        "customer_stats": {
            "total": User.objects.count(),
            "active": User.objects.filter(is_active=True).count(),
            "new_this_month": User.objects.filter(date_joined__gte=month_start).count(),
            "members": MembershipSubscription.objects.active().values("user").distinct().count(),
        },
        **filters,
    })


def customer_detail(request, user_id):
    customer = get_object_or_404(
        User.objects.select_related("membership", "loyalty_profile"),
        id=user_id
    )
    bookings = Booking.objects.filter(user=customer).select_related(
        "game_console", "payment"
    ).order_by("-booking_date")[:10]

    payments = Payment.objects.filter(user=customer).select_related(
        "booking"
    ).order_by("-created_at")[:10]

    subscriptions = MembershipSubscription.objects.filter(
        user=customer
    ).select_related("plan").order_by("-started_at")

    active_subscription = subscriptions.filter(
        status="active", expires_at__gt=timezone.now()
    ).first()

    totals = Booking.objects.filter(user=customer).aggregate(
        booking_total=Count("id"),
        spent=Sum(
            "payment__amount",
            filter=Q(payment__status__in=["captured", "demo"])
        ),
    )

    events = []
    for b in bookings:
        events.append({
            "kind": "booking",
            "booking_id": b.id,
            "title": f"Booking #{b.id} — {b.game_console.name if b.game_console else 'Console'}",
            "sub": f"{b.booking_date} · {b.start_time:%I:%M %p} · ₹{b.total_cost} · {b.get_status_display()}",
            "at": b.created_at,
        })
    for p in payments:
        events.append({
            "kind": "payment",
            "booking_id": p.booking_id,
            "title": f"Payment #{p.id} — Booking #{p.booking_id}",
            "sub": f"₹{p.amount_rupees} · {p.get_status_display()}",
            "at": p.created_at,
        })
    for s in subscriptions:
        events.append({
            "kind": "membership",
            "title": f"{s.plan.name} membership — {s.get_status_display()}",
            "sub": f"Started {s.started_at:%d %b %Y}" + (f" · Expires {s.expires_at:%d %b %Y}" if s.expires_at else ""),
            "at": s.created_at,
        })
    events.sort(key=lambda e: e["at"], reverse=True)
    events = events[:15]

    return render(request, "staff/customers/detail.html", {
        "customer": customer,
        "bookings": bookings,
        "payments": payments,
        "subscriptions": subscriptions,
        "active_subscription": active_subscription,
        "totals": totals,
        "timeline": events,
    })


def filter_games(request):
    """Shared queryset builder for the game library page."""
    q = request.GET.get("q", "")
    category = request.GET.get("category", "")
    badge = request.GET.get("badge", "")
    active_filter = request.GET.get("active", "")
    sort = request.GET.get("sort", "popular")

    games = Game.objects.all()

    if q:
        games = games.filter(
            Q(title__icontains=q)
            | Q(category__icontains=q)
            | Q(badge__icontains=q)
        )
    if category:
        games = games.filter(category=category)
    if badge:
        games = games.filter(badge=badge)
    if active_filter == "active":
        games = games.filter(is_active=True)
    elif active_filter == "archived":
        games = games.filter(is_active=False)

    valid_sorts = {
        "title": ["title", "sort_order"],
        "-title": ["-title", "sort_order"],
        "rating": ["-rating", "sort_order", "title"],
        "-rating": ["rating", "sort_order", "title"],
        "newest": ["-created_at", "sort_order"],
        "popular": ["sort_order", "title"],
    }
    games = games.order_by(*valid_sorts.get(sort, valid_sorts["popular"]))

    return games, {
        "q": q,
        "category": category,
        "badge": badge,
        "active_filter": active_filter,
        "sort": sort,
    }


def game_list(request):
    games, filters = filter_games(request)

    paginator = Paginator(games, 24)
    page = paginator.get_page(request.GET.get("page"))

    params = {}
    for key in ("q", "category", "badge", "active_filter"):
        if filters[key]:
            params[key if key != "active_filter" else "active"] = filters[key]
    if filters["sort"] != "popular":
        params["sort"] = filters["sort"]

    avg_rating = Game.objects.filter(rating__gt=0).aggregate(avg=Avg("rating"))["avg"]
    consoles = GameConsole.objects.annotate(
        booking_count=Count("bookings")
    ).order_by("name")

    return render(request, "staff/games/list.html", {
        "page_obj": page,
        "qs": urlencode(params),
        "consoles": consoles,
        "categories": Game.CATEGORIES,
        "badge_choices": [c for c in Game.BADGE_CHOICES if c[0]],
        "game_stats": {
            "total": Game.objects.count(),
            "active": Game.objects.filter(is_active=True).count(),
            "archived": Game.objects.filter(is_active=False).count(),
            "avg_rating": round(avg_rating, 1) if avg_rating is not None else 0,
        },
        "consoles_active": GameConsole.objects.active().count(),
        **filters,
    })


def game_detail(request, game_id):
    game = get_object_or_404(Game, id=game_id)

    related_tournaments = Tournament.objects.filter(
        game__iexact=game.title, is_active=True
    ).order_by("date")[:6]
    similar_games = Game.objects.filter(
        category=game.category
    ).exclude(pk=game.pk).order_by("sort_order", "title")[:4]

    return render(request, "staff/games/detail.html", {
        "game": game,
        "related_tournaments": related_tournaments,
        "similar_games": similar_games,
    })


@require_POST
def game_toggle_active(request, game_id):
    game = get_object_or_404(Game, id=game_id)
    game.is_active = not game.is_active
    game.save(update_fields=["is_active", "updated_at"])
    action = "restored to the library" if game.is_active else "archived"
    messages.success(request, f"“{game.title}” {action}.")

    next_url = request.POST.get("next", "")
    if next_url.startswith("/staff/games"):
        return redirect(next_url)
    return redirect("staff:staff_game_list")


def tournament_list(request):
    q = request.GET.get("q", "")
    status_filter = request.GET.get("status", "")
    sort = request.GET.get("sort", "-date")

    tournaments = Tournament.objects.all()

    if q:
        tournaments = tournaments.filter(
            Q(title__icontains=q) | Q(game__icontains=q)
        )
    if status_filter:
        tournaments = tournaments.filter(status=status_filter)

    valid_sorts = ["date", "-date", "title", "-title",
                   "prize_pool", "-prize_pool", "fill", "-fill"]
    if sort in valid_sorts:
        if sort in ("fill", "-fill"):
            tournaments = tournaments.annotate(
                fill_ratio=ExpressionWrapper(
                    F("registered_slots") * 1.0 / F("total_slots"),
                    output_field=FloatField(),
                )
            ).order_by("-fill_ratio" if sort == "fill" else "fill_ratio")
        else:
            tournaments = tournaments.order_by(sort)
    else:
        tournaments = tournaments.order_by("-date")

    paginator = Paginator(tournaments, 18)
    page = paginator.get_page(request.GET.get("page"))

    params = {}
    if q:
        params["q"] = q
    if status_filter:
        params["status"] = status_filter
    if sort != "-date":
        params["sort"] = sort

    totals = Tournament.objects.aggregate(
        prize_total=Sum("prize_pool"),
        slots_total=Sum("total_slots"),
        registered_total=Sum("registered_slots"),
    )
    registered = totals["registered_total"] or 0
    slots = totals["slots_total"] or 0
    filled = int((registered / slots) * 100) if slots else 0

    return render(request, "staff/tournaments/list.html", {
        "page_obj": page,
        "qs": urlencode(params),
        "q": q,
        "status_filter": status_filter,
        "sort": sort,
        "status_choices": Tournament.Status.choices,
        "tournament_stats": {
            "total": Tournament.objects.count(),
            "open": Tournament.objects.filter(status="registrations_open").count(),
            "upcoming": Tournament.objects.filter(status="upcoming").count(),
            "live": Tournament.objects.filter(status="in_progress").count(),
            "completed": Tournament.objects.filter(status="completed").count(),
            "cancelled": Tournament.objects.filter(status="cancelled").count(),
            "full": Tournament.objects.filter(status="full").count(),
            "prize_total": totals["prize_total"] or 0,
            "filled": filled,
            "registered": registered,
            "slots": slots,
        },
    })


def tournament_detail(request, tournament_id):
    tournament = get_object_or_404(Tournament, id=tournament_id)

    similar_tournaments = Tournament.objects.filter(
        game=tournament.game
    ).exclude(pk=tournament.pk).order_by("date")[:3]

    return render(request, "staff/tournaments/detail.html", {
        "tournament": tournament,
        "similar_tournaments": similar_tournaments,
    })


@require_POST
def tournament_set_status(request, tournament_id):
    tournament = get_object_or_404(Tournament, id=tournament_id)
    status = request.POST.get("status", "")
    allowed = {c[0] for c in Tournament.Status.choices}

    if status in allowed:
        tournament.status = status
        tournament.save(update_fields=["status", "updated_at"])
        messages.success(
            request,
            f"“{tournament.title}” is now {tournament.get_status_display().lower()}.",
        )
    else:
        messages.error(request, "That status is not valid.")

    next_url = request.POST.get("next", "")
    if next_url.startswith("/staff/tournaments"):
        return redirect(next_url)
    return redirect("staff:staff_tournament_list")


def membership_list(request):
    q = request.GET.get("q", "")
    status_filter = request.GET.get("status", "")
    sort = request.GET.get("sort", "tier")

    memberships = Membership.objects.annotate(
        active_member_count=Count(
            "subscriptions",
            filter=Q(subscriptions__status="active"),
        ),
        total_subscriptions=Count("subscriptions"),
    )

    if q:
        memberships = memberships.filter(
            Q(name__icontains=q) | Q(description__icontains=q)
        )
    if status_filter == "active":
        memberships = memberships.filter(is_active=True)
    elif status_filter == "inactive":
        memberships = memberships.filter(is_active=False)

    valid_sorts = {
        "tier": ["tier_level", "price"],
        "-tier": ["-tier_level", "-price"],
        "name": ["name"],
        "-name": ["-name"],
        "price": ["price"],
        "-price": ["-price"],
        "members": ["active_member_count", "tier_level"],
        "-members": ["-active_member_count", "tier_level"],
    }
    memberships = memberships.order_by(*valid_sorts.get(sort, valid_sorts["tier"]))

    now = timezone.now()
    expiring_soon = MembershipSubscription.objects.filter(
        status="active",
        expires_at__gte=now,
        expires_at__lte=now + timezone.timedelta(days=30),
    ).select_related("user", "plan").order_by("expires_at")

    captured_30 = MembershipPayment.objects.filter(
        status=MembershipPayment.Status.CAPTURED,
        created_at__gte=now - timezone.timedelta(days=30),
    ).aggregate(t=Sum("amount"))["t"] or 0

    subscriptions = MembershipSubscription.objects.select_related(
        "user", "plan"
    ).order_by("-created_at")[:12]

    return render(request, "staff/memberships/list.html", {
        "memberships": memberships,
        "subscriptions": subscriptions,
        "expiring_soon": expiring_soon,
        "q": q,
        "status_filter": status_filter,
        "sort": sort,
        "membership_stats": {
            "plans": Membership.objects.count(),
            "active_plans": Membership.objects.filter(is_active=True).count(),
            "members": MembershipSubscription.objects.active().values("user").distinct().count(),
            "active_subscriptions": MembershipSubscription.objects.active().count(),
            "expiring_7": MembershipSubscription.objects.filter(
                status="active",
                expires_at__gte=now,
                expires_at__lte=now + timezone.timedelta(days=7),
            ).count(),
            "expiring_30": expiring_soon.count(),
            "revenue_30": round(captured_30 / 100, 2),
        },
    })


def membership_plan_detail(request, plan_id):
    plan = get_object_or_404(
        Membership.objects.annotate(
            active_member_count=Count(
                "subscriptions",
                filter=Q(subscriptions__status="active"),
            ),
            total_subscriptions=Count("subscriptions"),
        ),
        id=plan_id,
    )
    members = MembershipSubscription.objects.filter(plan=plan).select_related(
        "user"
    ).order_by("-started_at")[:50]
    return render(request, "staff/memberships/detail.html", {
        "plan": plan,
        "members": members,
    })


@require_POST
def membership_toggle_active(request, plan_id):
    plan = get_object_or_404(Membership, id=plan_id)
    plan.is_active = not plan.is_active
    plan.save(update_fields=["is_active"])
    action = "activated" if plan.is_active else "deactivated"
    messages.success(request, f"“{plan.name}” plan {action}.")

    next_url = request.POST.get("next", "")
    if next_url.startswith("/staff/memberships"):
        return redirect(next_url)
    return redirect("staff:staff_membership_list")


def analytics_dashboard(request):
    data = StaffDashboardService.get_analytics_data()
    return render(request, "staff/analytics/dashboard.html", data)


def reports(request):
    return render(request, "staff/reports/index.html")


def report_detail(request, report_type):
    date_from_str = request.GET.get("from", "")
    date_to_str = request.GET.get("to", "")

    date_from = None
    date_to = None
    if date_from_str:
        try:
            date_from = datetime.strptime(date_from_str, "%Y-%m-%d").date()
        except ValueError:
            pass
    if date_to_str:
        try:
            date_to = datetime.strptime(date_to_str, "%Y-%m-%d").date()
        except ValueError:
            pass

    data = StaffDashboardService.get_report_data(report_type, date_from, date_to)

    return render(request, f"staff/reports/{report_type}.html", {
        "report_data": data,
        "date_from": date_from,
        "date_to": date_to,
        "report_type": report_type,
    })


def import_customers(request):
    return render(request, "staff/import/index.html")


def bulk_communication(request):
    users_count = User.objects.count()
    return render(request, "staff/communication/index.html", {
        "users_count": users_count,
    })


def communication_history(request):
    recent_notifications = Notification.objects.order_by("-created_at")[:30]
    return render(request, "staff/communication/history.html", {
        "notifications": recent_notifications,
    })


def settings_page(request):
    site = SiteSettings.objects.get_solo()
    return render(request, "staff/settings/index.html", {
        "site": site,
    })


# ── Ch13: Owner executive dashboard (superuser) ──
def executive_dashboard(request):
    data = StaffDashboardService.get_executive_data()
    data["site"] = SiteSettings.objects.get_solo()
    data["user_role"] = "Owner"
    return render(request, "staff/executive/dashboard.html", data)
