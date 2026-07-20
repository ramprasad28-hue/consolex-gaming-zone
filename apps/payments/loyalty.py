# apps/payments/loyalty.py
"""Loyalty accrual helpers, called when a payment is confirmed."""
from decimal import Decimal

from apps.memberships.models import LoyaltyProfile


def accrue_loyalty(user, amount_rupees: Decimal) -> None:
    """
    Credit a user's loyalty profile with spending and points.

    Call this exactly once at the moment a payment transitions to a
    successful state (from verify_payment or a webhook handler). Idempotency
    is the caller's responsibility — this function always adds.
    """
    profile, _ = LoyaltyProfile.objects.get_or_create(user=user)
    profile.lifetime_spending = profile.lifetime_spending + amount_rupees
    # 1 loyalty point per ₹10 spent.
    profile.points += int(amount_rupees // Decimal("10"))
    profile.save(update_fields=["lifetime_spending", "points", "updated_at"])
