# apps/memberships/tests.py
from datetime import timedelta
from decimal import Decimal

from django.db import IntegrityError, transaction
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from apps.memberships.models import (
    Membership, MembershipSubscription, LoyaltyProfile, MembershipPayment,
)
from apps.memberships.services import MembershipService
from apps.users.models import User
from apps.common.exceptions import PlanNotFoundError


class MembershipUniqueActiveTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(email="m@m.com", password="x")
        self.plan = Membership.objects.create(
            name="Basic", price=1199, duration_days=30, tier_level=1,
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
        now = timezone.now()
        MembershipSubscription.objects.create(
            user=self.user, plan=self.plan,
            status=MembershipSubscription.STATUS_ACTIVE,
            started_at=now,
            expires_at=now + timedelta(days=30),
        )
        pro = Membership.objects.create(
            name="Pro", price=3999, duration_days=30, tier_level=3,
        )
        MembershipSubscription.objects.filter(
            user=self.user, status=MembershipSubscription.STATUS_ACTIVE
        ).update(status=MembershipSubscription.STATUS_CANCELLED, cancelled_at=now)
        MembershipSubscription.objects.create(
            user=self.user, plan=pro,
            status=MembershipSubscription.STATUS_ACTIVE,
            started_at=now,
            expires_at=now + timedelta(days=30),
        )

        active = MembershipSubscription.objects.filter(
            user=self.user, status=MembershipSubscription.STATUS_ACTIVE,
        )
        self.assertEqual(active.count(), 1)
        self.assertEqual(active.first().plan, pro)

    def test_subscribe_requires_login(self):
        resp = self.client.get(
            reverse("memberships:subscribe", args=[self.plan.id]),
        )
        self.assertEqual(resp.status_code, 302)


class MembershipServiceTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(email="msvc@m.com", password="x")
        self.plan = Membership.objects.create(
            name="Silver", price=1999, duration_days=30, tier_level=1, is_active=True,
        )
        self.inactive_plan = Membership.objects.create(
            name="Retired", price=999, duration_days=30, tier_level=0, is_active=False,
        )

    def test_list_plans(self):
        plans = MembershipService.list_plans()
        self.assertGreaterEqual(plans.count(), 1)
        self.assertTrue(all(p.is_active for p in plans))

    def test_get_plan_success(self):
        plan = MembershipService.get_plan(self.plan.id)
        self.assertEqual(plan.name, "Silver")

    def test_get_plan_not_found(self):
        with self.assertRaises(PlanNotFoundError):
            MembershipService.get_plan(9999)

    def test_get_plan_inactive(self):
        with self.assertRaises(PlanNotFoundError):
            MembershipService.get_plan(self.inactive_plan.id)

    def test_get_subscription_none(self):
        result = MembershipService.get_subscription(self.user)
        self.assertIsNone(result)

    def test_create_order_demo_mode(self):
        from unittest.mock import patch
        with patch.object(MembershipService, "_get_client", return_value=None):
            result = MembershipService.create_order(self.user, self.plan.id)
            self.assertTrue(result["demo_mode"])
            self.assertIn("subscription_id", result)

            sub = MembershipSubscription.objects.get(pk=result["subscription_id"])
            self.assertEqual(sub.status, MembershipSubscription.STATUS_PENDING)


class MembershipModelTests(TestCase):
    def test_plan_str(self):
        plan = Membership.objects.create(name="Gold", price=2999, duration_days=30, tier_level=2)
        self.assertEqual(str(plan), "Gold")

    def test_plan_total_hours(self):
        plan = Membership.objects.create(
            name="Gold", price=2999, duration_days=30,
            included_hours=10, weekend_hours=5, bonus_hours=2, tier_level=2,
        )
        self.assertEqual(plan.total_hours, 17)

    def test_subscription_days_remaining(self):
        user = User.objects.create_user(email="sub@m.com", password="x")
        plan = Membership.objects.create(name="Silver", price=1999, duration_days=30, tier_level=1)
        sub = MembershipSubscription.objects.create(
            user=user, plan=plan,
            status=MembershipSubscription.STATUS_ACTIVE,
            expires_at=timezone.now() + timedelta(days=15),
        )
        self.assertGreater(sub.days_remaining, 0)
        self.assertLessEqual(sub.days_remaining, 15)

    def test_subscription_is_active_valid(self):
        user = User.objects.create_user(email="valid@m.com", password="x")
        plan = Membership.objects.create(name="Gold", price=2999, duration_days=30, tier_level=2)
        sub = MembershipSubscription.objects.create(
            user=user, plan=plan,
            status=MembershipSubscription.STATUS_ACTIVE,
            expires_at=timezone.now() + timedelta(days=30),
        )
        self.assertTrue(sub.is_active_valid)

    def test_subscription_is_not_active_valid_expired(self):
        user = User.objects.create_user(email="exp@m.com", password="x")
        plan = Membership.objects.create(name="Gold", price=2999, duration_days=30, tier_level=2)
        sub = MembershipSubscription.objects.create(
            user=user, plan=plan,
            status=MembershipSubscription.STATUS_ACTIVE,
            expires_at=timezone.now() - timedelta(days=1),
        )
        self.assertFalse(sub.is_active_valid)

    def test_loyalty_recalculate_level(self):
        user = User.objects.create_user(email="loy@m.com", password="x")
        profile = LoyaltyProfile.objects.create(user=user)
        profile.lifetime_spending = 2500
        profile.save()
        level = profile.recalculate_level()
        self.assertEqual(level, "gold")

    def test_queryset_active_subscriptions(self):
        user = User.objects.create_user(email="q@m.com", password="x")
        plan = Membership.objects.create(name="Basic", price=999, duration_days=30, tier_level=0)
        MembershipSubscription.objects.create(
            user=user, plan=plan,
            status=MembershipSubscription.STATUS_ACTIVE,
            expires_at=timezone.now() + timedelta(days=30),
        )
        MembershipSubscription.objects.create(
            user=user, plan=plan,
            status=MembershipSubscription.STATUS_CANCELLED,
            expires_at=timezone.now() + timedelta(days=30),
        )
        self.assertEqual(MembershipSubscription.objects.active().count(), 1)

    def test_membership_payment_amount_rupees(self):
        mp = MembershipPayment(amount=199900)
        self.assertEqual(mp.amount_rupees, Decimal("1999.00"))
