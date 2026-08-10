import csv
from datetime import date, datetime
from urllib.parse import urlencode

from django.shortcuts import render, get_object_or_404, redirect
from django.core.paginator import Paginator
from django.contrib import messages
from django.db.models import Count, Q, Sum
from django.http import HttpResponse, JsonResponse
from django.utils import timezone
from django.views.decorators.http import require_POST

from apps.bookings.models import Booking
from apps.bookings.services import BookingService
from apps.common.exceptions import ServiceError
from apps.users.models import User
from apps.payments.models import Payment
from apps.memberships.models import (
    Membership, MembershipSubscription, LoyaltyProfile
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


def customer_list(request):
    q = request.GET.get("q", "")
    membership_filter = request.GET.get("membership", "")
    sort = request.GET.get("sort", "-date_joined")

    users = User.objects.annotate(
        booking_count=Count("bookings"),
        total_spent=Sum(
            "payments__amount",
            filter=Q(payments__status__in=["captured", "demo"])
        ),
    ).select_related("membership")

    if q:
        users = users.filter(
            Q(email__icontains=q)
            | Q(first_name__icontains=q)
            | Q(last_name__icontains=q)
            | Q(phone__icontains=q)
        )
    if membership_filter:
        if membership_filter == "none":
            users = users.filter(membership__isnull=True)
        else:
            users = users.filter(membership__isnull=False)

    valid_sorts = ["date_joined", "-date_joined", "email", "-email",
                   "booking_count", "-booking_count", "last_login", "-last_login"]
    if sort in valid_sorts:
        users = users.order_by(sort)
    else:
        users = users.order_by("-date_joined")

    paginator = Paginator(users, 20)
    page = paginator.get_page(request.GET.get("page"))

    return render(request, "staff/customers/list.html", {
        "page_obj": page,
        "q": q,
        "membership_filter": membership_filter,
        "sort": sort,
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

    return render(request, "staff/customers/detail.html", {
        "customer": customer,
        "bookings": bookings,
        "payments": payments,
        "subscriptions": subscriptions,
    })


def game_list(request):
    q = request.GET.get("q", "")
    platform = request.GET.get("platform", "")
    active_filter = request.GET.get("active", "")

    games = Game.objects.all()
    if q:
        games = games.filter(
            Q(title__icontains=q)
            | Q(category__icontains=q)
        )
    if platform:
        games = games.filter(category=platform.lower())
    if active_filter == "active":
        games = games.filter(is_active=True)
    elif active_filter == "archived":
        games = games.filter(is_active=False)

    paginator = Paginator(games, 20)
    page = paginator.get_page(request.GET.get("page"))

    consoles = GameConsole.objects.active()

    return render(request, "staff/games/list.html", {
        "page_obj": page,
        "consoles": consoles,
        "q": q,
        "platform": platform,
        "active_filter": active_filter,
    })


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

    valid_sorts = ["date", "-date", "title", "-title", "prize_pool", "-prize_pool"]
    if sort in valid_sorts:
        tournaments = tournaments.order_by(sort)
    else:
        tournaments = tournaments.order_by("-date")

    paginator = Paginator(tournaments, 20)
    page = paginator.get_page(request.GET.get("page"))

    return render(request, "staff/tournaments/list.html", {
        "page_obj": page,
        "q": q,
        "status_filter": status_filter,
        "sort": sort,
        "status_choices": Tournament.Status.choices,
    })


def membership_list(request):
    memberships = Membership.objects.all()
    subscriptions = MembershipSubscription.objects.select_related(
        "user", "plan"
    ).order_by("-created_at")[:30]

    total_active = MembershipSubscription.objects.active().count()
    total_expired = MembershipSubscription.objects.filter(status="expired").count()

    return render(request, "staff/memberships/list.html", {
        "memberships": memberships,
        "subscriptions": subscriptions,
        "total_active": total_active,
        "total_expired": total_expired,
    })


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
