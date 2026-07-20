# apps/memberships/tests.py
from datetime import timedelta

from django.contrib.auth.models import AnonymousUser
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from apps.memberships.models import Membership, MembershipSubscription
from apps.users.models import User


class MembershipUniqueActiveTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(email="m@m.com", password="x")
        self.plan = Membership.objects.create(
            name="Basic", price=1199, duration_days=30, tier_level=1
        )

    def test_two_active_subscriptions_violates_constraint(self):
        now = timezone.now()
        MembershipSubscription.objects.create(
            user=self.user, plan=self.plan,
            status=MembershipSubscription.STATUS_ACTIVE,
            expires_at=now + timedelta(days=30),
        )
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                MembershipSubscription.objects.create(
                    user=self.user, plan=self.plan,
                    status=MembershipSubscription.STATUS_ACTIVE,
                    expires_at=now + timedelta(days=30),
                )

    def test_subscribe_cancels_prior_active(self):
        client = self.client
        client.force_login(self.user)
        pro = Membership.objects.create(
            name="Pro", price=3999, duration_days=30, tier_level=3
        )

        client.post(reverse("memberships:subscribe", args=[self.plan.id]))
        client.post(reverse("memberships:subscribe", args=[pro.id]))

        active = MembershipSubscription.objects.filter(
            user=self.user, status=MembershipSubscription.STATUS_ACTIVE
        )
        self.assertEqual(active.count(), 1)
        self.assertEqual(active.first().plan, pro)
        self.assertEqual(
            MembershipSubscription.objects.filter(
                user=self.user, status=MembershipSubscription.STATUS_CANCELLED
            ).count(),
            1,
        )

    def test_subscribe_requires_login(self):
        resp = self.client.get(
            reverse("memberships:subscribe", args=[self.plan.id])
        )
        self.assertEqual(resp.status_code, 302)  # redirected to login
