"""
Business logic for notifications: creation, listing, read-marking.
"""
import logging

from apps.notifications.models import Notification
from apps.common.exceptions import NotFoundError

logger = logging.getLogger("apps.notifications")


class NotificationService:
    """Stateless notification operations."""

    @staticmethod
    def notify(user, message):
        """Create a notification for a user. Never raises."""
        try:
            Notification.objects.create(user=user, message=message)
        except Exception:
            logger.exception("Failed to create notification for %s", user)

    @staticmethod
    def list_for_user(user, page=1, page_size=20):
        qs = Notification.objects.filter(user=user).order_by("-created_at")
        total = qs.count()
        start = (page - 1) * page_size
        items = qs[start : start + page_size]
        return {
            "count": total,
            "page": page,
            "page_size": page_size,
            "results": items,
        }

    @staticmethod
    def mark_read(user, notification_id):
        try:
            notif = Notification.objects.get(pk=notification_id, user=user)
        except Notification.DoesNotExist:
            raise NotFoundError(f"Notification #{notification_id} not found.")
        notif.is_read = True
        notif.save(update_fields=["is_read"])
        return notif

    @staticmethod
    def unread_count(user):
        return Notification.objects.filter(user=user, is_read=False).count()

    @staticmethod
    def recent(user, limit=8):
        return Notification.objects.filter(user=user).order_by("-created_at")[:limit]
