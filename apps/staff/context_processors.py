"""
Staff portal topbar context — notification bell data for authenticated staff.
"""
from apps.notifications.services import NotificationService


def staff_topbar(request):
    user = getattr(request, "user", None)
    if not user or not user.is_authenticated:
        return {}
    if not (user.is_staff or user.is_superuser):
        return {}
    return {
        "staff_unread_count": NotificationService.unread_count(user),
        "staff_recent_notifications": NotificationService.recent(user, limit=8),
    }
