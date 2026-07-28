from datetime import date, timedelta, datetime, time
from decimal import Decimal
from collections import defaultdict

from django.db.models import Sum, Count, Q, Avg
from django.utils import timezone

from apps.bookings.models import Booking
from apps.users.models import User
from apps.payments.models import Payment
from apps.memberships.models import (
    Membership, MembershipSubscription, LoyaltyProfile
)
from apps.games.models import GameConsole
from apps.tournaments.models import Tournament


class StaffDashboardService:
    """Data aggregation for staff/admin dashboard."""

    @staticmethod
    def get_dashboard_data():
        today = date.today()
        now = timezone.now()
        week_start = today - timedelta(days=today.weekday())
        month_start = today.replace(day=1)

        # Today's bookings
        todays_bookings = Booking.objects.filter(booking_date=today)
        todays_count = todays_bookings.count()

        # Active customers (all users who have booked)
        active_customer_ids = Booking.objects.values_list("user_id", flat=True).distinct()
        active_customers_count = User.objects.filter(id__in=active_customer_ids).count()

        # Total registered users
        total_users = User.objects.count()

        # Revenue
        all_payments = Payment.objects.captured()
        today_revenue = all_payments.filter(
            created_at__date=today
        ).aggregate(t=Sum("amount"))["t"] or 0

        week_revenue = all_payments.filter(
            created_at__date__gte=week_start
        ).aggregate(t=Sum("amount"))["t"] or 0

        month_revenue = all_payments.filter(
            created_at__date__gte=month_start
        ).aggregate(t=Sum("amount"))["t"] or 0

        total_revenue = all_payments.aggregate(t=Sum("amount"))["t"] or 0

        # Membership stats
        active_subscriptions = MembershipSubscription.objects.active().count()
        total_membership_revenue = MembershipSubscription.objects.filter(
            status="active"
        ).aggregate(
            t=Sum("plan__price")
        )["t"] or 0
        membership_plans_count = Membership.objects.active().count()

        # Tournament stats
        total_tournaments = Tournament.objects.active().count()
        upcoming_tournaments = Tournament.objects.upcoming().count()

        # Console utilization
        total_consoles = GameConsole.objects.active().count()
        booked_today = Booking.objects.filter(
            booking_date=today,
            status__in=["confirmed", "pending"]
        ).values_list("game_console_id", flat=True).distinct().count()

        # Peak booking hours (from all bookings)
        bookings_today_qs = Booking.objects.filter(booking_date=today)
        peak_hours = defaultdict(int)
        for b in bookings_today_qs:
            hour = b.start_time.hour
            peak_hours[hour] += 1
        peak_hour = max(peak_hours, key=peak_hours.get) if peak_hours else None

        # Pending tasks
        pending_bookings = Booking.objects.filter(status="pending").count()
        pending_payments = Payment.objects.pending().count()
        expiring_subscriptions = MembershipSubscription.objects.filter(
            status="active",
            expires_at__gte=now,
            expires_at__lte=now + timedelta(days=7),
        ).count()

        # Recent activity (bookings + payments)
        recent_bookings = Booking.objects.select_related(
            "user", "game_console"
        ).order_by("-created_at")[:10]

        # Booking stats
        booking_stats = Booking.objects.aggregate(
            total=Count("id"),
            confirmed=Count("id", filter=Q(status="confirmed")),
            pending=Count("id", filter=Q(status="pending")),
            completed=Count("id", filter=Q(status="completed")),
            cancelled=Count("id", filter=Q(status="cancelled")),
        )

        return {
            "todays_bookings_count": todays_count,
            "todays_bookings": todays_bookings.select_related("user", "game_console")[:5],
            "active_customers_count": active_customers_count,
            "total_users": total_users,
            "today_revenue": round(Decimal(today_revenue) / Decimal(100), 2),
            "week_revenue": round(Decimal(week_revenue) / Decimal(100), 2),
            "month_revenue": round(Decimal(month_revenue) / Decimal(100), 2),
            "total_revenue": round(Decimal(total_revenue) / Decimal(100), 2),
            "active_subscriptions": active_subscriptions,
            "total_membership_revenue": total_membership_revenue,
            "membership_plans_count": membership_plans_count,
            "total_tournaments": total_tournaments,
            "upcoming_tournaments": upcoming_tournaments,
            "total_consoles": total_consoles,
            "consoles_used_today": booked_today,
            "peak_hour": peak_hour,
            "pending_bookings": pending_bookings,
            "pending_payments": pending_payments,
            "expiring_subscriptions": expiring_subscriptions,
            "booking_stats": booking_stats,
            "recent_bookings": recent_bookings,
            "recent_activity": recent_bookings[:6],
        }

    @staticmethod
    def get_analytics_data():
        today = date.today()
        week_start = today - timedelta(days=today.weekday())
        month_start = today.replace(day=1)
        year_start = today.replace(month=1, day=1)

        captured_payments = Payment.objects.captured()

        # Daily bookings this month
        days_in_month = [
            month_start + timedelta(days=i) for i in range((today - month_start).days + 1)
        ]
        daily_bookings = []
        daily_revenue = []
        for d in days_in_month:
            count = Booking.objects.filter(booking_date=d).count()
            rev = captured_payments.filter(created_at__date=d).aggregate(
                t=Sum("amount")
            )["t"] or 0
            daily_bookings.append({"date": d, "count": count})
            daily_revenue.append({"date": d, "amount": round(Decimal(rev) / Decimal(100), 2)})

        # Weekly revenue
        weeks = []
        w = week_start - timedelta(weeks=11)
        while w <= today:
            we = w + timedelta(days=6)
            rev = captured_payments.filter(
                created_at__date__gte=w, created_at__date__lte=we
            ).aggregate(t=Sum("amount"))["t"] or 0
            bk = Booking.objects.filter(
                booking_date__gte=w, booking_date__lte=we
            ).count()
            weeks.append({
                "start": w, "end": we,
                "revenue": round(Decimal(rev) / Decimal(100), 2),
                "bookings": bk,
            })
            w += timedelta(weeks=4)

        # Popular games (consoles)
        popular_consoles = Booking.objects.values(
            "game_console__name"
        ).annotate(
            count=Count("id")
        ).filter(
            game_console__isnull=False
        ).order_by("-count")[:10]

        # Console usage by type
        console_usage = GameConsole.objects.active().values(
            "console_type"
        ).annotate(count=Count("id"))

        # Membership growth
        membership_growth = MembershipSubscription.objects.filter(
            status="active"
        ).values("plan__name").annotate(count=Count("id"))

        # Tournament participation
        tournament_stats = Tournament.objects.active().aggregate(
            total_slots=Sum("total_slots"),
            registered=Sum("registered_slots"),
        )

        # Customer returning rate
        all_customers = User.objects.filter(
            bookings__isnull=False
        ).distinct().count()
        returning_customers = User.objects.annotate(
            booking_count=Count("bookings")
        ).filter(booking_count__gte=2).count()

        # Booking by status (pie chart data)
        status_data = Booking.objects.aggregate(
            confirmed=Count("id", filter=Q(status="confirmed")),
            pending=Count("id", filter=Q(status="pending")),
            completed=Count("id", filter=Q(status="completed")),
            cancelled=Count("id", filter=Q(status="cancelled")),
        )

        # Today's hourly breakdown
        hourly_breakdown = defaultdict(int)
        for b in Booking.objects.filter(booking_date=today):
            hourly_breakdown[b.start_time.hour] += 1

        return {
            "daily_bookings": daily_bookings,
            "daily_revenue": daily_revenue,
            "weekly_trends": weeks,
            "popular_consoles": popular_consoles,
            "console_usage": console_usage,
            "membership_growth": membership_growth,
            "tournament_stats": tournament_stats,
            "all_customers": all_customers,
            "returning_customers": returning_customers,
            "status_data": status_data,
            "hourly_breakdown": dict(hourly_breakdown),
        }

    @staticmethod
    def get_report_data(report_type, date_from=None, date_to=None):
        captured_payments = Payment.objects.captured()

        if date_from:
            captured_payments = captured_payments.filter(created_at__date__gte=date_from)
        if date_to:
            captured_payments = captured_payments.filter(created_at__date__lte=date_to)

        base_bookings = Booking.objects.all()
        if date_from:
            base_bookings = base_bookings.filter(booking_date__gte=date_from)
        if date_to:
            base_bookings = base_bookings.filter(booking_date__lte=date_to)

        if report_type == "revenue":
            data = captured_payments.aggregate(
                total=Sum("amount"),
                count=Count("id"),
                avg=Avg("amount"),
            )
            total = round(Decimal(data["total"] or 0) / Decimal(100), 2)
            avg = round(Decimal(data["avg"] or 0) / Decimal(100), 2)
            return {
                "total_revenue": total,
                "payment_count": data["count"],
                "avg_payment": avg,
                "items": captured_payments.select_related("booking", "user").order_by("-created_at")[:50],
            }

        elif report_type == "bookings":
            data = base_bookings.aggregate(
                total=Count("id"),
                confirmed=Count("id", filter=Q(status="confirmed")),
                pending=Count("id", filter=Q(status="pending")),
                completed=Count("id", filter=Q(status="completed")),
                cancelled=Count("id", filter=Q(status="cancelled")),
            )
            return {
                "total": data["total"],
                "confirmed": data["confirmed"],
                "pending": data["pending"],
                "completed": data["completed"],
                "cancelled": data["cancelled"],
                "items": base_bookings.select_related("user", "game_console").order_by("-booking_date")[:50],
            }

        elif report_type == "customers":
            customers = User.objects.annotate(
                booking_count=Count("bookings"),
                total_spent=Sum("payments__amount", filter=Q(payments__status__in=["captured", "demo"])),
            ).order_by("-date_joined")
            if date_from:
                customers = customers.filter(date_joined__gte=date_from)
            if date_to:
                customers = customers.filter(date_joined__lte=date_to)
            total = customers.count()
            active = customers.filter(booking_count__gt=0).count()
            return {
                "total_customers": total,
                "active_customers": active,
                "items": customers[:50],
            }

        elif report_type == "memberships":
            subs = MembershipSubscription.objects.select_related("user", "plan")
            if date_from:
                subs = subs.filter(created_at__gte=date_from)
            if date_to:
                subs = subs.filter(created_at__lte=date_to)
            data = subs.aggregate(
                total=Count("id"),
                active=Count("id", filter=Q(status="active")),
                expired=Count("id", filter=Q(status="expired")),
                cancelled=Count("id", filter=Q(status="cancelled")),
            )
            return {
                "total": data["total"],
                "active": data["active"],
                "expired": data["expired"],
                "cancelled": data["cancelled"],
                "items": subs.order_by("-created_at")[:50],
            }

        elif report_type == "tournaments":
            tours = Tournament.objects.all()
            if date_from:
                tours = tours.filter(date__gte=date_from)
            if date_to:
                tours = tours.filter(date__lte=date_to)
            data = tours.aggregate(
                total=Count("id"),
                total_slots=Sum("total_slots"),
                registered=Sum("registered_slots"),
            )
            return {
                "total": data["total"],
                "total_slots": data["total_slots"],
                "registered": data["registered"],
                "items": tours.order_by("-date")[:50],
            }

        return {}
