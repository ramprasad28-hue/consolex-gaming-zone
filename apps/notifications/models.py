from django.db import models
from django.conf import settings


class NotificationQuerySet(models.QuerySet):
    def for_user(self, user):
        return self.filter(user=user).order_by("-created_at")

    def unread(self, user):
        return self.filter(user=user, is_read=False)

    def mark_all_read(self, user):
        return self.filter(user=user, is_read=False).update(is_read=True)


class Notification(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="notifications",
    )
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    objects = NotificationQuerySet.as_manager()

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["user", "is_read"], name="idx_notif_user_read"),
            models.Index(fields=["-created_at"], name="idx_notif_created"),
        ]

    def __str__(self):
        return f"Notif for {self.user.email} – {'Read' if self.is_read else 'Unread'}"
