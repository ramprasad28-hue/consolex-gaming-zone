# apps/users/tests.py
from django.test import TestCase
from django.urls import reverse

from apps.users.models import User
from apps.users.services import UserService
from apps.common.exceptions import (
    DuplicateEmailError,
    AuthenticationError,
    ValidationError,
)


class UserAuthTests(TestCase):
    def test_register_creates_user_and_logs_in(self):
        resp = self.client.post(reverse("users:register"), {
            "email": "new@user.com",
            "first_name": "New",
            "last_name": "User",
            "password1": "Str0ng!Pass",
            "password2": "Str0ng!Pass",
        })
        self.assertEqual(resp.status_code, 302)
        self.assertTrue(User.objects.filter(email="new@user.com").exists())

    def test_duplicate_email_rejected(self):
        User.objects.create_user(email="dup@user.com", password="x")
        resp = self.client.post(reverse("users:register"), {
            "email": "dup@user.com",
            "password1": "Str0ng!Pass",
            "password2": "Str0ng!Pass",
        })
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(User.objects.filter(email="dup@user.com").count(), 1)

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


class UserServiceTests(TestCase):
    def test_register_success(self):
        user = UserService.register("svc@test.com", "Str0ng!Pass", "Svc", "Test")
        self.assertEqual(user.email, "svc@test.com")
        self.assertEqual(user.first_name, "Svc")
        self.assertTrue(user.check_password("Str0ng!Pass"))

    def test_register_duplicate_email(self):
        User.objects.create_user(email="dup@test.com", password="x")
        with self.assertRaises(DuplicateEmailError):
            UserService.register("dup@test.com", "Str0ng!Pass")

    def test_register_weak_password(self):
        with self.assertRaises(ValidationError):
            UserService.register("weak@test.com", "123")

    def test_login_success(self):
        user = User.objects.create_user(email="l@test.com", password="x")
        from django.test import RequestFactory
        request = RequestFactory().post("/")
        request.session = self.client.session
        result = UserService.login(request, "l@test.com", "x")
        self.assertEqual(result, user)

    def test_login_failure(self):
        from django.test import RequestFactory
        request = RequestFactory().post("/")
        request.session = self.client.session
        with self.assertRaises(AuthenticationError):
            UserService.login(request, "no@test.com", "wrong")

    def test_get_dashboard_data(self):
        user = User.objects.create_user(email="dash@test.com", password="x")
        data = UserService.get_dashboard_data(user)
        self.assertIn("total_bookings", data)
        self.assertIn("total_spent", data)
        self.assertIn("achievements", data)
        self.assertEqual(data["total_bookings"], 0)

    def test_get_api_dashboard_data(self):
        user = User.objects.create_user(email="apidash@test.com", password="x")
        data = UserService.get_api_dashboard_data(user)
        self.assertIn("total_bookings", data)
        self.assertIn("activity", data)
        self.assertIsInstance(data["activity"], list)


class UserModelTests(TestCase):
    def test_user_str(self):
        user = User.objects.create_user(email="str@test.com", password="x")
        self.assertEqual(str(user), "str@test.com")

    def test_user_full_display_name(self):
        user = User.objects.create_user(
            email="name@test.com", password="x",
            first_name="John", last_name="Doe",
        )
        self.assertEqual(user.full_display_name, "John Doe")

    def test_user_full_display_name_fallback(self):
        user = User.objects.create_user(email="fallback@test.com", password="x")
        self.assertEqual(user.full_display_name, "fallback@test.com")

    def test_user_has_active_subscription_false(self):
        user = User.objects.create_user(email="nosub@test.com", password="x")
        self.assertFalse(user.has_active_subscription)

    def test_verified_manager(self):
        User.objects.create_user(email="v@test.com", password="x", is_verified=True)
        User.objects.create_user(email="nv@test.com", password="x", is_verified=False)
        self.assertEqual(User.objects.verified().count(), 1)
