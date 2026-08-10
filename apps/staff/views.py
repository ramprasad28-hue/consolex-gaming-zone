import csv
from datetime import date, datetime, timedelta
from decimal import Decimal, InvalidOperation
from urllib.parse import urlencode

from django.shortcuts import render, get_object_or_404, redirect
from django.core.paginator import Paginator
from django.contrib import messages
from django.contrib.auth import update_session_auth_hash
from django.conf import settings as django_settings
from django.db.models import Avg, Count, F, Q, Sum, Max
from django.db.models import ExpressionWrapper, FloatField, OuterRef, Subquery
from django.http import HttpResponse, JsonResponse, Http404
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
from apps.notifications.services import NotificationService
from apps.cms.models import SiteSettings

from .services import StaffDashboardService, serialize_live_sessions
from .forms import GeneralSettingsForm, StaffPasswordChangeForm, StaffProfileForm
from .health import run_health_checks


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


def filter_payments(request):
    """Shared queryset builder for the payments page and CSV export."""
    q = request.GET.get("q", "")
    status_filter = request.GET.get("status", "")
    date_from = request.GET.get("date_from", "")
    date_to = request.GET.get("date_to", "")
    amount_min = request.GET.get("amount_min", "")
    amount_max = request.GET.get("amount_max", "")
    sort = request.GET.get("sort", "-created_at")

    payments = Payment.objects.select_related("user", "booking", "booking__game_console").all()

    if q:
        payments = payments.filter(
            Q(user__email__icontains=q)
            | Q(user__first_name__icontains=q)
            | Q(user__last_name__icontains=q)
            | Q(user__phone__icontains=q)
            | Q(id__icontains=q)
            | Q(booking__id__icontains=q)
            | Q(razorpay_order_id__icontains=q)
            | Q(razorpay_payment_id__icontains=q)
        )
    if status_filter:
        payments = payments.filter(status=status_filter)
    if date_from:
        try:
            payments = payments.filter(
                created_at__date__gte=datetime.strptime(date_from, "%Y-%m-%d").date()
            )
        except ValueError:
            pass
    if date_to:
        try:
            payments = payments.filter(
                created_at__date__lte=datetime.strptime(date_to, "%Y-%m-%d").date()
            )
        except ValueError:
            pass
    for field, key in (("amount__gte", amount_min), ("amount__lte", amount_max)):
        if key:
            try:
                paise = int(Decimal(key) * 100)
            except (InvalidOperation, ValueError):
                continue
            if paise >= 0:
                payments = payments.filter(**{field: paise})

    valid_sorts = [
        "created_at", "-created_at", "amount", "-amount",
        "status", "-status", "booking_id", "-booking_id",
    ]
    if sort in valid_sorts:
        payments = payments.order_by(sort)
    else:
        payments = payments.order_by("-created_at")

    return payments, {
        "q": q,
        "status_filter": status_filter,
        "date_from": date_from,
        "date_to": date_to,
        "amount_min": amount_min,
        "amount_max": amount_max,
        "sort": sort,
    }


def _rupees(paise):
    return round(Decimal(paise or 0) / Decimal(100), 2)


def payment_list(request):
    payments, filters = filter_payments(request)

    paginator = Paginator(payments, 20)
    page = paginator.get_page(request.GET.get("page"))

    params = {}
    for key in ("q", "status_filter", "date_from", "date_to", "amount_min", "amount_max"):
        if filters[key]:
            params[key if key != "status_filter" else "status"] = filters[key]
    if filters["sort"] != "-created_at":
        params["sort"] = filters["sort"]

    today = timezone.localdate()
    week_start = today - timedelta(days=today.weekday())
    month_start = today.replace(day=1)

    captured = Payment.objects.captured()
    today_captured = captured.filter(created_at__date=today)
    week_captured = captured.filter(created_at__date__gte=week_start)
    month_captured = captured.filter(created_at__date__gte=month_start)

    revenue = {
        "today": _rupees(today_captured.aggregate(t=Sum("amount"))["t"]),
        "week": _rupees(week_captured.aggregate(t=Sum("amount"))["t"]),
        "month": _rupees(month_captured.aggregate(t=Sum("amount"))["t"]),
        "total": _rupees(captured.aggregate(t=Sum("amount"))["t"]),
        "tx_today": today_captured.count(),
        "tx_week": week_captured.count(),
        "tx_month": month_captured.count(),
        "tx_total": captured.count(),
    }

    status_counts = dict(
        Payment.objects.values_list("status").annotate(c=Count("id"))
    )
    refunded_amount = _rupees(
        Payment.objects.filter(status="refunded").aggregate(t=Sum("amount"))["t"]
    )

    days = request.GET.get("days", "30")
    try:
        days = int(days)
    except (TypeError, ValueError):
        days = 30
    trend = StaffDashboardService.get_revenue_trend(days)

    now = timezone.now()
    memb_captured = MembershipPayment.objects.filter(
        status=MembershipPayment.Status.CAPTURED
    )
    memb_month = memb_captured.filter(created_at__date__gte=month_start)
    memb_30 = memb_captured.filter(created_at__gte=now - timedelta(days=30))
    membership_billing = {
        "month": _rupees(memb_month.aggregate(t=Sum("amount"))["t"]),
        "total": _rupees(memb_captured.aggregate(t=Sum("amount"))["t"]),
        "recent_30": _rupees(memb_30.aggregate(t=Sum("amount"))["t"]),
        "active_subs": MembershipSubscription.objects.active().count(),
    }

    return render(request, "staff/payments/list.html", {
        "page_obj": page,
        "qs": urlencode(params),
        "payment_status_choices": Payment.Status.choices,
        "revenue": revenue,
        "status_counts": status_counts,
        "refunded_amount": refunded_amount,
        "trend": trend,
        "trend_days": days,
        "membership_billing": membership_billing,
        "today": today,
        **filters,
    })


def payment_export(request):
    """CSV export of payments honouring the same filters as the payments page."""
    payments, _ = filter_payments(request)

    response = HttpResponse(content_type="text/csv; charset=utf-8")
    response["Content-Disposition"] = 'attachment; filename="payments.csv"'
    writer = csv.writer(response)
    writer.writerow([
        "Payment ID", "Booking ID", "Customer", "Email", "Phone",
        "Amount (INR)", "Currency", "Status", "Razorpay Order ID",
        "Razorpay Payment ID", "Payment Date", "Updated At",
    ])
    for p in payments:
        booking = p.booking
        writer.writerow([
            p.id,
            booking.id if booking else "",
            p.user.full_display_name if p.user else "",
            p.user.email if p.user else "",
            p.user.phone if p.user and p.user.phone else "",
            p.amount_rupees,
            p.currency,
            p.get_status_display(),
            p.razorpay_order_id,
            p.razorpay_payment_id or "",
            p.created_at.strftime("%Y-%m-%d %H:%M:%S") if p.created_at else "",
            p.updated_at.strftime("%Y-%m-%d %H:%M:%S") if p.updated_at else "",
        ])
    return response


def booking_detail(request, booking_id):
    booking = get_object_or_404(
        Booking.objects.select_related("user", "game_console", "payment"),
        id=booking_id
    )
    payment = getattr(booking, "payment", None)
    booking_amount = booking.total_cost
    paid = payment.amount_rupees if payment and payment.is_successful else Decimal("0.00")
    outstanding = max(booking_amount - paid, Decimal("0.00"))
    paid_pct = (
        round(float(paid) * 100 / float(booking_amount), 1)
        if booking_amount else 0
    )
    return render(request, "staff/bookings/detail.html", {
        "booking": booking,
        "billing": {
            "booking_amount": booking_amount,
            "paid": paid,
            "outstanding": outstanding,
            "paid_pct": paid_pct,
        },
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

    plan_payments = MembershipPayment.objects.filter(
        subscription__plan=plan
    ).select_related("subscription", "user")
    plan_counts = dict(plan_payments.values_list("status").annotate(c=Count("id")))
    plan_revenue = _rupees(
        plan_payments.filter(
            status=MembershipPayment.Status.CAPTURED
        ).aggregate(t=Sum("amount"))["t"]
    )
    recent_plan_payments = plan_payments.order_by("-created_at")[:10]

    return render(request, "staff/memberships/detail.html", {
        "plan": plan,
        "members": members,
        "plan_payments": recent_plan_payments,
        "plan_payment_counts": plan_counts,
        "plan_revenue": plan_revenue,
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


REPORT_TYPES = {
    "revenue", "bookings", "payments", "customers",
    "memberships", "tournaments", "games",
}


def reports(request):
    today = timezone.localdate()
    week_start = today - timedelta(days=today.weekday())
    month_start = today.replace(day=1)

    captured = Payment.objects.captured()
    revenue_total = _rupees(captured.aggregate(t=Sum("amount"))["t"])
    revenue_month = _rupees(
        captured.filter(created_at__date__gte=month_start).aggregate(t=Sum("amount"))["t"]
    )

    booking_stats = Booking.objects.aggregate(
        total=Count("id"),
        today=Count("id", filter=Q(booking_date=today)),
        week=Count("id", filter=Q(booking_date__gte=week_start)),
    )

    payment_stats = Payment.objects.aggregate(
        total=Count("id"),
        captured=Count("id", filter=Q(status__in=["captured", "demo"])),
        pending=Count("id", filter=Q(status="pending")),
        failed=Count("id", filter=Q(status="failed")),
    )

    customers_total = User.objects.count()
    customers_active = User.objects.filter(
        bookings__isnull=False
    ).distinct().count()

    active_subs = MembershipSubscription.objects.active().count()
    memberships_total = Membership.objects.count()

    games_total = Game.objects.count()
    games_consoles = GameConsole.objects.count()
    booked_consoles = Booking.objects.values("game_console_id").distinct().count()

    tournaments_total = Tournament.objects.count()
    tournaments_open = Tournament.objects.filter(
        status="registrations_open"
    ).count()

    summary = {
        "revenue": {
            "total": revenue_total,
            "month": revenue_month,
            "count": captured.count(),
            "url": "staff:staff_report_detail",
        },
        "bookings": {
            "total": booking_stats["total"],
            "today": booking_stats["today"],
            "week": booking_stats["week"],
            "url": "staff:staff_report_detail",
        },
        "payments": {
            "total": payment_stats["total"],
            "captured": payment_stats["captured"],
            "pending": payment_stats["pending"],
            "failed": payment_stats["failed"],
            "url": "staff:staff_report_detail",
        },
        "customers": {
            "total": customers_total,
            "active": customers_active,
            "url": "staff:staff_report_detail",
        },
        "memberships": {
            "total": memberships_total,
            "active_subs": active_subs,
            "url": "staff:staff_report_detail",
        },
        "tournaments": {
            "total": tournaments_total,
            "open": tournaments_open,
            "url": "staff:staff_report_detail",
        },
        "games": {
            "total": games_total,
            "consoles": games_consoles,
            "booked": booked_consoles,
            "url": "staff:staff_report_detail",
        },
    }

    return render(request, "staff/reports/index.html", {
        "summary": summary,
        "today": today,
    })


def _parse_report_dates(request):
    """Parse ?from= and ?to= into dates (invalid values are ignored)."""
    date_from = None
    date_to = None
    for key in ("from", "to"):
        raw = request.GET.get(key, "")
        if raw:
            try:
                parsed = datetime.strptime(raw, "%Y-%m-%d").date()
            except ValueError:
                continue
            if key == "from":
                date_from = parsed
            else:
                date_to = parsed
    return date_from, date_to


def report_detail(request, report_type):
    if report_type not in REPORT_TYPES:
        raise Http404

    date_from, date_to = _parse_report_dates(request)
    data = StaffDashboardService.get_report_data(report_type, date_from, date_to)

    today = timezone.localdate()
    presets = {
        "7d": today - timedelta(days=6),
        "30d": today - timedelta(days=29),
        "90d": today - timedelta(days=89),
        "month": today.replace(day=1),
    }

    context = {
        "report_data": data,
        "date_from": date_from,
        "date_to": date_to,
        "report_type": report_type,
        "presets": presets,
        "today": today,
    }
    if report_type in ("revenue", "payments"):
        context["trend"] = StaffDashboardService.get_revenue_trend(30)

    return render(request, f"staff/reports/{report_type}.html", context)


def report_export(request, report_type):
    """CSV export of a report honouring the same from/to date filters."""
    if report_type not in REPORT_TYPES:
        raise Http404

    date_from, date_to = _parse_report_dates(request)

    def within(qs, field):
        if date_from:
            qs = qs.filter(**{f"{field}__gte": date_from})
        if date_to:
            qs = qs.filter(**{f"{field}__lte": date_to})
        return qs

    response = HttpResponse(content_type="text/csv; charset=utf-8")
    response["Content-Disposition"] = (
        f'attachment; filename="{report_type}-report.csv"'
    )
    writer = csv.writer(response)

    if report_type == "bookings":
        writer.writerow([
            "Booking ID", "Customer", "Email", "Phone", "Console",
            "Booking Date", "Start", "End", "Duration (hrs)", "Players",
            "Amount (INR)", "Status", "Payment Status", "Payment Amount (INR)",
            "Razorpay Order ID", "Created At",
        ])
        qs = within(Booking.objects.select_related("user", "game_console", "payment"), "booking_date")
        for b in qs.order_by("-booking_date"):
            payment = getattr(b, "payment", None)
            writer.writerow([
                b.id, b.user.full_display_name, b.user.email, b.user.phone or "",
                b.game_console.name if b.game_console else "",
                b.booking_date.isoformat(), b.start_time.strftime("%H:%M"),
                b.end_time.strftime("%H:%M"), b.duration_hours, b.number_of_players,
                b.total_cost, b.get_status_display(),
                payment.get_status_display() if payment else "",
                payment.amount_rupees if payment else "",
                payment.razorpay_order_id if payment else "",
                b.created_at.strftime("%Y-%m-%d %H:%M:%S") if b.created_at else "",
            ])

    elif report_type in ("revenue", "payments"):
        writer.writerow([
            "Payment ID", "Booking ID", "Customer", "Email", "Phone",
            "Amount (INR)", "Currency", "Status", "Razorpay Order ID",
            "Razorpay Payment ID", "Payment Date",
        ])
        qs = within(Payment.objects.select_related("user", "booking"), "created_at__date")
        for p in qs.order_by("-created_at"):
            booking = p.booking
            writer.writerow([
                p.id, booking.id if booking else "",
                p.user.full_display_name if p.user else "",
                p.user.email if p.user else "",
                p.user.phone if p.user and p.user.phone else "",
                p.amount_rupees, p.currency, p.get_status_display(),
                p.razorpay_order_id, p.razorpay_payment_id or "",
                p.created_at.strftime("%Y-%m-%d %H:%M:%S") if p.created_at else "",
            ])

    elif report_type == "customers":
        writer.writerow(["Customer", "Email", "Phone", "Joined", "Bookings", "Total Spent (INR)"])
        customers = within(User.objects.annotate(
            booking_count=Count("bookings"),
            total_spent=Sum("payments__amount", filter=Q(payments__status__in=["captured", "demo"])),
        ), "date_joined")
        for u in customers.order_by("-date_joined"):
            writer.writerow([
                u.full_display_name, u.email, u.phone or "",
                u.date_joined.strftime("%Y-%m-%d"),
                u.booking_count,
                round((u.total_spent or 0) / 100, 2),
            ])

    elif report_type == "memberships":
        writer.writerow(["User", "Email", "Plan", "Started", "Expires", "Status", "Auto Renew"])
        qs = within(MembershipSubscription.objects.select_related("user", "plan"), "created_at")
        for s in qs.order_by("-created_at"):
            writer.writerow([
                s.user.full_display_name, s.user.email, s.plan.name,
                s.started_at.strftime("%Y-%m-%d") if s.started_at else "",
                s.expires_at.strftime("%Y-%m-%d") if s.expires_at else "",
                s.get_status_display(), "Yes" if s.auto_renew else "No",
            ])

    elif report_type == "tournaments":
        writer.writerow(["Title", "Game", "Date", "Prize (INR)", "Slots", "Registered", "Status"])
        qs = within(Tournament.objects.all(), "date")
        for t in qs.order_by("-date"):
            writer.writerow([
                t.title, t.game, t.date.isoformat() if t.date else "",
                t.prize_pool, t.total_slots, t.registered_slots, t.get_status_display(),
            ])

    elif report_type == "games":
        writer.writerow(["Console", "Type", "Bookings", "Players", "Revenue (INR)"])
        qs = GameConsole.objects.annotate(
            booking_count=Count("bookings"),
            revenue=Sum("bookings__payment__amount", filter=Q(bookings__payment__status__in=["captured", "demo"])),
            players=Sum("bookings__number_of_players"),
        )
        qs = within(qs, "bookings__booking_date")
        for c in qs.distinct().order_by("-booking_count"):
            writer.writerow([
                c.name, c.console_type, c.booking_count, c.players or 0,
                round((c.revenue or 0) / 100, 2),
            ])

    return response


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


def _staff_next(request, default):
    """Redirect back to a safe staff URL after a POST action."""
    next_url = request.POST.get("next", "") or request.META.get("HTTP_REFERER", "")
    if next_url and next_url.startswith("/staff/") and "//" not in next_url:
        return redirect(next_url)
    return redirect(default)


# ── Phase 6: Settings hub ─────────────────────
def settings_page(request):
    site = SiteSettings.objects.get_solo()
    general_form = GeneralSettingsForm(instance=site)
    password_form = StaffPasswordChangeForm(request.user)

    if request.method == "POST":
        if request.POST.get("form_type") == "password":
            password_form = StaffPasswordChangeForm(request.user, request.POST)
            if password_form.is_valid():
                password_form.save()
                update_session_auth_hash(request, request.user)
                messages.success(request, "Password updated successfully.")
                return redirect("staff:staff_settings")
        else:
            general_form = GeneralSettingsForm(request.POST, instance=site)
            if general_form.is_valid():
                general_form.save()
                messages.success(request, "General settings saved.")
                return redirect("staff:staff_settings")
            messages.error(request, "Please fix the errors below.")

    return render(request, "staff/settings/index.html", {
        "site": site,
        "settings_form": general_form,
        "password_form": password_form,
        "active_tab": request.GET.get("tab", "general"),
        "razorpay_configured": bool(
            django_settings.RAZORPAY_KEY_ID and django_settings.RAZORPAY_KEY_SECRET
        ),
        "email_backend": django_settings.EMAIL_BACKEND.split(".")[-1],
        "whatsapp_configured": bool(
            getattr(django_settings, "TWILIO_ACCOUNT_SID", "")
            and getattr(django_settings, "TWILIO_AUTH_TOKEN", "")
        ),
        "system_checks": run_health_checks(),
    })


# ── Phase 6: Admin profile ────────────────────
def profile_page(request):
    profile_form = StaffProfileForm(instance=request.user)
    password_form = StaffPasswordChangeForm(request.user)

    if request.method == "POST":
        if request.POST.get("form_type") == "password":
            password_form = StaffPasswordChangeForm(request.user, request.POST)
            if password_form.is_valid():
                password_form.save()
                update_session_auth_hash(request, request.user)
                messages.success(request, "Password updated successfully.")
                return redirect("staff:staff_profile")
        else:
            profile_form = StaffProfileForm(request.POST, instance=request.user)
            if profile_form.is_valid():
                profile_form.save()
                messages.success(request, "Profile updated successfully.")
                return redirect("staff:staff_profile")
            messages.error(request, "Please fix the errors below.")

    return render(request, "staff/profile.html", {
        "profile_form": profile_form,
        "password_form": password_form,
    })


# ── Phase 6: Staff management ─────────────────
def staff_list(request):
    q = request.GET.get("q", "").strip()
    staff = User.objects.filter(is_staff=True).order_by("-is_superuser", "email")
    if q:
        staff = staff.filter(
            Q(email__icontains=q)
            | Q(first_name__icontains=q)
            | Q(last_name__icontains=q)
            | Q(phone__icontains=q)
        )
    paginator = Paginator(staff, 20)
    page_obj = paginator.get_page(request.GET.get("page"))

    base = User.objects.filter(is_staff=True)
    return render(request, "staff/staff/list.html", {
        "page_obj": page_obj,
        "q": q,
        "staff_stats": {
            "total": base.count(),
            "owners": base.filter(is_superuser=True).count(),
            "active": base.filter(is_active=True).count(),
            "inactive": base.filter(is_active=False).count(),
        },
    })


@require_POST
def staff_toggle_active(request, user_id):
    if not request.user.is_superuser:
        raise Http404
    target = get_object_or_404(User, id=user_id, is_staff=True)
    if target == request.user:
        messages.error(request, "You can't change your own account status.")
        return redirect("staff:staff_staff_list")
    target.is_active = not target.is_active
    target.save(update_fields=["is_active"])
    action = "reactivated" if target.is_active else "deactivated"
    messages.success(request, f"{target.email} {action}.")
    return _staff_next(request, "staff:staff_staff_list")


@require_POST
def staff_toggle_role(request, user_id):
    if not request.user.is_superuser:
        raise Http404
    target = get_object_or_404(User, id=user_id, is_staff=True)
    if target == request.user:
        messages.error(request, "You can't change your own role.")
        return redirect("staff:staff_staff_list")
    target.is_superuser = not target.is_superuser
    target.save(update_fields=["is_superuser"])
    action = "made an Owner" if target.is_superuser else "demoted to Staff"
    messages.success(request, f"{target.email} {action}.")
    return _staff_next(request, "staff:staff_staff_list")


# ── Phase 6: Staff notification center ────────
def staff_notifications(request):
    notifications = Notification.objects.filter(user=request.user).order_by("-created_at")
    category = request.GET.get("category", "")
    status = request.GET.get("status", "")

    if category in Notification.Category.values:
        notifications = notifications.filter(category=category)
    if status == "unread":
        notifications = notifications.filter(is_read=False)
    elif status == "read":
        notifications = notifications.filter(is_read=True)

    paginator = Paginator(notifications, 20)
    page_obj = paginator.get_page(request.GET.get("page"))

    user_qs = Notification.objects.filter(user=request.user)
    return render(request, "staff/notifications/list.html", {
        "page_obj": page_obj,
        "category": category,
        "status": status,
        "unread_count": NotificationService.unread_count(request.user),
        "category_stats": [
            {"key": key, "label": label, "count": user_qs.filter(category=key).count()}
            for key, label in Notification.Category.choices
        ],
    })


@require_POST
def staff_notification_read(request, notification_id):
    try:
        NotificationService.mark_read(request.user, notification_id)
    except ServiceError:
        messages.error(request, "Notification not found.")
    return _staff_next(request, "staff:staff_notifications")


@require_POST
def staff_notification_read_all(request):
    Notification.objects.mark_all_read(request.user)
    return _staff_next(request, "staff:staff_notifications")


# ── Ch13: Owner executive dashboard (superuser) ──
def executive_dashboard(request):
    data = StaffDashboardService.get_executive_data()
    data["site"] = SiteSettings.objects.get_solo()
    return render(request, "staff/executive/dashboard.html", data)

