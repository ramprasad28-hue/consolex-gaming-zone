"""
Business logic for user registration, login, and dashboard aggregation.
"""
import logging
from decimal import Decimal

from django.contrib.auth import get_user_model, authenticate
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db.models import Sum, Count, Q

from apps.bookings.models import Booking
from apps.notifications.services import NotificationService
from apps.common.exceptions import (
    AuthenticationError,
    DuplicateEmailError,
    ValidationError,
)

logger = logging.getLogger("apps.users")

User = get_user_model()


class UserService:
    """Stateless user operations."""

    @staticmethod
    def register(email, password, first_name="", last_name=""):
        """Register a new user. Raises on duplicate email or invalid password."""
        if User.objects.filter(email=email).exists():
            raise DuplicateEmailError()

        try:
            from django.contrib.auth.password_validation import validate_password
            validate_password(password)
        except DjangoValidationError as e:
            raise ValidationError(" ".join(e.messages))

        user = User.objects.create_user(
            email=email,
            password=password,
            first_name=first_name,
            last_name=last_name,
        )
        logger.info("User registered: %s", email)
        return user

    @staticmethod
    def login(request, email, password):
        """Authenticate a user. Raises on failure."""
        user = authenticate(request, username=email, password=password)
        if user is None:
            raise AuthenticationError("Invalid email or password.")
        return user

    @staticmethod
    def get_dashboard_data(user):
        """
        Aggregate all data needed for the user dashboard template view.

        Returns a dict ready for template context.
        """
        all_bookings = (
            Booking.objects
            .filter(user=user)
            .select_related("game_console", "payment")
            .order_by("-booking_date", "-start_time")
        )

        stats = all_bookings.aggregate(
            total=Count("id"),
            confirmed=Count("id", filter=Q(status="confirmed")),
            pending=Count("id", filter=Q(status="pending")),
            completed=Count("id", filter=Q(status="completed")),
            cancelled=Count("id", filter=Q(status="cancelled")),
        )

        total_spent = all_bookings.filter(
            payment__status__in=["captured", "demo"]
        ).aggregate(total=Sum("payment__amount"))["total"] or 0
        total_spent = (Decimal(str(total_spent)) / Decimal("100")).quantize(Decimal("0.01"))

        completed = all_bookings.filter(status="completed")
        total_hours_played = sum(b.duration_hours for b in completed[:200])

        console_stats = (
            all_bookings
            .filter(status__in=["confirmed", "completed", "pending"])
            .values("game_console__name")
            .annotate(cnt=Count("id"))
            .order_by("-cnt")
        )
        console_list = [
            (c["game_console__name"], c["cnt"])
            for c in console_stats
            if c["game_console__name"]
        ]
        favorite_console = console_list[0][0] if console_list else None
        games_played = len(console_list)

        notifications = NotificationService.recent(user, limit=8)
        unread_count = NotificationService.unread_count(user)

        activity = UserService._build_activity(all_bookings)

        achievements = [
            {"label": "First Booking", "icon": "🕹️", "achieved": stats["total"] >= 1},
            {"label": "Regular Player", "icon": "⭐", "achieved": stats["total"] >= 5},
            {"label": "Marathon Gamer", "icon": "⏱️", "achieved": total_hours_played >= 20},
            {"label": "Big Spender", "icon": "💎", "achieved": float(total_spent) >= 5000},
        ]

        hours_progress_pct = min(round((total_hours_played / 40) * 100), 100) if total_hours_played else 0
        games_progress_pct = min(round((games_played / 10) * 100), 100) if games_played else 0

        return {
            "bookings": all_bookings,
            "total_bookings": stats["total"],
            "confirmed_bookings": stats["confirmed"],
            "pending_bookings": stats["pending"],
            "completed_bookings": stats["completed"],
            "cancelled_bookings": stats["cancelled"],
            "total_spent": total_spent,
            "total_hours_played": round(total_hours_played, 1),
            "favorite_console": favorite_console,
            "games_played": games_played,
            "notifications": notifications,
            "unread_notifications_count": unread_count,
            "activity": activity,
            "achievements": achievements,
            "hours_progress_pct": hours_progress_pct,
            "games_progress_pct": games_progress_pct,
        }

    @staticmethod
    def get_api_dashboard_data(user):
        """
        Aggregate all data needed for the API dashboard endpoint.

        Returns a serializable dict.
        """
        all_bookings = Booking.objects.filter(user=user).select_related("game_console", "payment")

        stats = all_bookings.aggregate(
            total=Count("id"),
            confirmed=Count("id", filter=Q(status="confirmed")),
            pending=Count("id", filter=Q(status="pending")),
            completed=Count("id", filter=Q(status="completed")),
            cancelled=Count("id", filter=Q(status="cancelled")),
        )

        total_spent = all_bookings.filter(
            payment__status__in=["captured", "demo"]
        ).aggregate(total=Sum("payment__amount"))["total"] or 0
        total_spent = (Decimal(str(total_spent)) / Decimal("100")).quantize(Decimal("0.01"))

        completed_qs = all_bookings.filter(status="completed")
        total_hours_played = sum(b.duration_hours for b in completed_qs[:200])

        console_stats = (
            all_bookings
            .filter(status__in=["confirmed", "completed", "pending"])
            .values("game_console__name")
            .annotate(cnt=Count("id"))
            .order_by("-cnt")
        )
        console_list = [
            (c["game_console__name"], c["cnt"])
            for c in console_stats
            if c["game_console__name"]
        ]
        favorite_console = console_list[0][0] if console_list else None
        games_played = len(console_list)

        notifications = NotificationService.recent(user, limit=8)
        unread_count = NotificationService.unread_count(user)

        activity = UserService._build_activity_api(all_bookings)

        achievements = [
            {"label": "First Booking", "icon": "gamepad", "achieved": stats["total"] >= 1},
            {"label": "Regular Player", "icon": "star", "achieved": stats["total"] >= 5},
            {"label": "Marathon Gamer", "icon": "clock", "achieved": total_hours_played >= 20},
            {"label": "Big Spender", "icon": "gem", "achieved": float(total_spent) >= 5000},
        ]

        hours_progress_pct = min(round((total_hours_played / 40) * 100), 100) if total_hours_played else 0
        games_progress_pct = min(round((games_played / 10) * 100), 100) if games_played else 0

        return {
            "total_bookings": stats["total"],
            "confirmed": stats["confirmed"],
            "pending": stats["pending"],
            "completed": stats["completed"],
            "cancelled": stats["cancelled"],
            "total_spent": float(total_spent),
            "total_hours_played": round(total_hours_played, 1),
            "favorite_console": favorite_console,
            "games_played": games_played,
            "notifications": [
                {"id": n.id, "message": n.message, "is_read": n.is_read, "created_at": n.created_at.isoformat()}
                for n in notifications
            ],
            "unread_count": unread_count,
            "activity": activity,
            "achievements": achievements,
            "hours_progress_pct": hours_progress_pct,
            "games_progress_pct": games_progress_pct,
        }

    @staticmethod
    def _build_activity(bookings):
        """Build activity timeline for template view."""
        activity = []
        for b in bookings[:8]:
            activity.append({
                "icon": "🎮",
                "text": f"Booked {b.game_console.name if b.game_console else 'a console'}",
                "timestamp": b.created_at,
            })
            if hasattr(b, "payment") and b.payment.status in ("captured", "demo"):
                activity.append({
                    "icon": "💳",
                    "text": f"Payment completed for Booking #{b.id}",
                    "timestamp": b.payment.updated_at,
                })
            if b.status == "cancelled":
                activity.append({
                    "icon": "✖",
                    "text": f"Booking #{b.id} cancelled",
                    "timestamp": b.updated_at,
                })
        activity.sort(key=lambda a: a["timestamp"], reverse=True)
        return activity[:6]

    @staticmethod
    def _build_activity_api(bookings):
        """Build activity timeline for API response."""
        activity = []
        for b in bookings[:8]:
            activity.append({
                "icon": "gamepad",
                "text": f"Booked {b.game_console.name if b.game_console else 'a console'}",
                "timestamp": b.created_at.isoformat(),
            })
            if hasattr(b, "payment") and b.payment.status in ("captured", "demo"):
                activity.append({
                    "icon": "credit_card",
                    "text": f"Payment completed for Booking #{b.id}",
                    "timestamp": b.payment.updated_at.isoformat(),
                })
            if b.status == "cancelled":
                activity.append({
                    "icon": "x_circle",
                    "text": f"Booking #{b.id} cancelled",
                    "timestamp": b.updated_at.isoformat(),
                })
        activity.sort(key=lambda a: a["timestamp"], reverse=True)
        return activity[:6]
