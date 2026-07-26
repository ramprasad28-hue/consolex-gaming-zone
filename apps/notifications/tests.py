# apps/notifications/tests.py
from django.test import TestCase

from apps.notifications.models import Notification
from apps.notifications.services import NotificationService
from apps.users.models import User
from apps.common.exceptions import NotFoundError


class NotificationServiceTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(email="notif@test.com", password="x")

    def test_notify_creates_notification(self):
        NotificationService.notify(self.user, "Test message")
        self.assertEqual(Notification.objects.count(), 1)
        self.assertEqual(Notification.objects.first().message, "Test message")

    def test_notify_never_raises(self):
        # Even with invalid user, should not raise
        NotificationService.notify(None, "Test")
        # No assertion needed — just ensure no exception

    def test_list_for_user(self):
        Notification.objects.create(user=self.user, message="One")
        Notification.objects.create(user=self.user, message="Two")
        result = NotificationService.list_for_user(self.user)
        self.assertEqual(result["count"], 2)
        self.assertEqual(len(result["results"]), 2)

    def test_mark_read(self):
        notif = Notification.objects.create(user=self.user, message="Read me")
        result = NotificationService.mark_read(self.user, notif.id)
        result.refresh_from_db()
        self.assertTrue(result.is_read)

    def test_mark_read_not_found(self):
        with self.assertRaises(NotFoundError):
            NotificationService.mark_read(self.user, 9999)

    def test_unread_count(self):
        Notification.objects.create(user=self.user, message="Unread", is_read=False)
        Notification.objects.create(user=self.user, message="Read", is_read=True)
        self.assertEqual(NotificationService.unread_count(self.user), 1)

    def test_recent(self):
        for i in range(10):
            Notification.objects.create(user=self.user, message=f"Msg {i}")
        recent = NotificationService.recent(self.user, limit=5)
        self.assertEqual(len(recent), 5)

    def test_list_for_user_pagination(self):
        for i in range(25):
            Notification.objects.create(user=self.user, message=f"M{i}")
        result = NotificationService.list_for_user(self.user, page=1, page_size=10)
        self.assertEqual(result["count"], 25)
        self.assertEqual(len(result["results"]), 10)
        result2 = NotificationService.list_for_user(self.user, page=3, page_size=10)
        self.assertEqual(len(result2["results"]), 5)

    def test_recent_empty(self):
        recent = NotificationService.recent(self.user)
        self.assertEqual(len(recent), 0)

    def test_mark_read_wrong_user(self):
        user2 = User.objects.create_user(email="wrong@test.com", password="x")
        notif = Notification.objects.create(user=user2, message="Not yours")
        with self.assertRaises(NotFoundError):
            NotificationService.mark_read(self.user, notif.id)


class NotificationModelTests(TestCase):
    def test_notification_str(self):
        user = User.objects.create_user(email="str@test.com", password="x")
        notif = Notification.objects.create(user=user, message="Test", is_read=False)
        self.assertIn("Unread", str(notif))
        notif.is_read = True
        notif.save()
        self.assertIn("Read", str(notif))

    def test_queryset_mark_all_read(self):
        user = User.objects.create_user(email="bulk@test.com", password="x")
        Notification.objects.create(user=user, message="A", is_read=False)
        Notification.objects.create(user=user, message="B", is_read=False)
        count = Notification.objects.mark_all_read(user)
        self.assertEqual(count, 2)
        self.assertEqual(Notification.objects.filter(user=user, is_read=False).count(), 0)

    def test_queryset_for_user(self):
        user = User.objects.create_user(email="fu@test.com", password="x")
        user2 = User.objects.create_user(email="other@test.com", password="x")
        Notification.objects.create(user=user, message="Mine")
        Notification.objects.create(user=user2, message="Theirs")
        qs = Notification.objects.for_user(user)
        self.assertEqual(qs.count(), 1)

    def test_queryset_unread(self):
        user = User.objects.create_user(email="ur@test.com", password="x")
        Notification.objects.create(user=user, message="U", is_read=False)
        Notification.objects.create(user=user, message="R", is_read=True)
        self.assertEqual(Notification.objects.unread(user).count(), 1)
