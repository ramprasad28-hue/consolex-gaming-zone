"""
Business logic for memberships: plans, subscriptions, payments.
"""
import logging

import razorpay
from datetime import timedelta
from decimal import Decimal

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from apps.memberships.models import (
    Membership,
    MembershipSubscription,
    MembershipPayment,
)
from apps.notifications.services import NotificationService
from apps.common.exceptions import (
    PlanNotFoundError,
    RazorpayError,
    RazorpaySignatureError,
    PaymentNotFoundError,
    SubscriptionAlreadyActiveError,
)

logger = logging.getLogger("apps.memberships")


class MembershipService:
    """Stateless membership operations."""

    # ── Plans ──────────────────────────────────────────────

    @staticmethod
    def list_plans():
        return Membership.objects.filter(is_active=True).order_by("tier_level", "price")

    @staticmethod
    def get_plan(plan_id):
        try:
            return Membership.objects.get(pk=plan_id, is_active=True)
        except Membership.DoesNotExist:
            raise PlanNotFoundError(f"Plan #{plan_id} not found.")

    # ── Subscriptions ──────────────────────────────────────

    @staticmethod
    def get_subscription(user):
        return (
            MembershipSubscription.objects.filter(user=user)
            .select_related("plan")
            .order_by("-started_at")
            .first()
        )

    @staticmethod
    def create_order(user, plan_id):
        """
        Create a pending subscription + Razorpay order (or demo payment).

        Returns dict with order details.
        """
        plan = MembershipService.get_plan(plan_id)
        amount_paise = int(plan.price * Decimal("100"))

        client = MembershipService._get_client()

        # Create pending subscription
        now = timezone.now()
        subscription = MembershipSubscription.objects.create(
            user=user,
            plan=plan,
            status=MembershipSubscription.STATUS_PENDING,
            started_at=now,
            expires_at=now + timedelta(days=plan.duration_days),
        )

        if client is None:
            MembershipPayment.objects.create(
                subscription=subscription,
                user=user,
                amount=amount_paise,
                status=MembershipPayment.Status.PENDING,
            )
            logger.info("Demo mode: subscription #%s created for %s", subscription.id, user.email)
            return {
                "demo_mode": True,
                "subscription_id": subscription.id,
                "amount": amount_paise,
            }

        try:
            order = client.order.create({
                "amount": amount_paise,
                "currency": "INR",
                "payment_capture": 0,
            })
        except Exception as e:
            logger.error("Razorpay order creation failed for membership: %s", e)
            subscription.delete()
            raise RazorpayError()

        MembershipPayment.objects.create(
            subscription=subscription,
            user=user,
            amount=amount_paise,
            razorpay_order_id=order["id"],
        )

        return {
            "order_id": order["id"],
            "amount": amount_paise,
            "key_id": settings.RAZORPAY_KEY_ID,
            "subscription_id": subscription.id,
        }

    @staticmethod
    @transaction.atomic
    def verify_payment(user, subscription_id, razorpay_order_id, razorpay_payment_id, razorpay_signature):
        """Verify Razorpay payment and activate the subscription."""
        try:
            sub = MembershipSubscription.objects.select_for_update().get(
                pk=subscription_id, user=user
            )
        except MembershipSubscription.DoesNotExist:
            raise PlanNotFoundError("Subscription not found.")

        mp = MembershipPayment.objects.filter(subscription=sub).first()
        if mp is None:
            raise PaymentNotFoundError("No payment record found.")

        if mp.is_successful:
            return {"status": mp.status, "subscription_status": sub.status}

        client = MembershipService._get_client()

        if client is None:
            # Demo mode
            MembershipService._activate_subscription(
                mp, sub,
                razorpay_payment_id or "demo_payment",
                razorpay_signature or "demo_sig",
                user,
                is_demo=True,
            )
            logger.info("Demo membership payment approved for %s", user.email)
            return {"status": "demo", "subscription_status": "active"}

        try:
            client.utility.verify_payment_signature({
                "razorpay_order_id": razorpay_order_id,
                "razorpay_payment_id": razorpay_payment_id,
                "razorpay_signature": razorpay_signature,
            })
        except razorpay.errors.SignatureVerificationError:
            mp.status = MembershipPayment.Status.FAILED
            mp.razorpay_payment_id = razorpay_payment_id
            mp.save(update_fields=["status", "razorpay_payment_id", "updated_at"])
            logger.warning("Membership payment signature verification failed for sub #%s", sub.id)
            raise RazorpaySignatureError()

        MembershipService._activate_subscription(
            mp, sub, razorpay_payment_id, razorpay_signature, user, is_demo=False
        )

        return {"status": mp.status, "subscription_status": sub.status}

    # ── Internal helpers ───────────────────────────────────

    @staticmethod
    def _get_client():
        if settings.RAZORPAY_KEY_ID and settings.RAZORPAY_KEY_SECRET:
            return razorpay.Client(
                auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET)
            )
        return None

    @staticmethod
    def _activate_subscription(mpayment, subscription, razorpay_payment_id, razorpay_signature, user, is_demo=False):
        """Mark payment captured, activate subscription, cancel prior active subs."""
        mpayment.razorpay_payment_id = razorpay_payment_id
        mpayment.razorpay_signature = razorpay_signature
        mpayment.status = MembershipPayment.Status.CAPTURED
        mpayment.save(update_fields=["razorpay_payment_id", "razorpay_signature", "status", "updated_at"])

        # Cancel any prior active subscription
        MembershipSubscription.objects.filter(
            user=user, status=MembershipSubscription.STATUS_ACTIVE
        ).update(
            status=MembershipSubscription.STATUS_CANCELLED,
            cancelled_at=timezone.now(),
        )

        subscription.status = MembershipSubscription.STATUS_ACTIVE
        subscription.started_at = timezone.now()
        subscription.expires_at = timezone.now() + timedelta(days=subscription.plan.duration_days)
        subscription.save(update_fields=["status", "started_at", "expires_at", "updated_at"])

        # Update user's FK
        user.membership = subscription.plan
        user.save(update_fields=["membership"])

        NotificationService.notify(
            user,
            f"Your {subscription.plan.name} membership is now active!",
        )
