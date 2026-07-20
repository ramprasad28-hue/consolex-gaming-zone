# apps/users/tests.py
from django.test import TestCase
from django.urls import reverse

from apps.users.models import User


class UserAuthTests(TestCase):
    def test_register_creates_user_and_logs_in(self):
        resp = self.client.post(reverse("users:register"), {
            "email": "new@user.com",
            "first_name": "New",
            "last_name": "User",
            "password1": "Str0ng!Pass",
            "password2": "Str0ng!Pass",
        })
        self.assertEqual(resp.status_code, 302)  # redirect after register
        self.assertTrue(User.objects.filter(email="new@user.com").exists())
        self.assertTrue(User.objects.get(email="new@user.com").is_authenticated)

    def test_duplicate_email_rejected(self):
        User.objects.create_user(email="dup@user.com", password="x")
        resp = self.client.post(reverse("users:register"), {
            "email": "dup@user.com",
            "password1": "Str0ng!Pass",
            "password2": "Str0ng!Pass",
        })
        # Re-renders the form (200) with an error.
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(
            User.objects.filter(email="dup@user.com").count(), 1
        )

    def test_login(self):
        User.objects.create_user(email="login@user.com", password="x")
        resp = self.client.post(reverse("users:login"), {
            "email": "login@user.com",
            "password": "x",
        })
        self.assertEqual(resp.status_code, 302)

    def test_password_reset_view_renders(self):
        resp = self.client.get(reverse("users:password_reset"))
        self.assertEqual(resp.status_code, 200)
