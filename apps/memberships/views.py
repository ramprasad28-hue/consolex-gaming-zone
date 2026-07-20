# apps/memberships/views.py
from datetime import date

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from apps.bookings.pricing import player_hourly_rate

from .models import Membership, MembershipSubscription


def plan_list(request):
    """Render all active membership plans from the database."""
    plans = Membership.objects.filter(is_active=True)

    # Standard pay-per-hour cost for a 2-player, 2-hour weekday session,
    # used by the savings-comparison section on the page.
    payg_2h_weekday = player_hourly_rate(2, date(2026, 1, 5)) * 2  # Mon = weekday

    return render(
        request,
        "memberships/plans.html",
        {"plans": plans, "payg_2h_weekday": payg_2h_weekday},
    )


@login_required
def subscribe(request, plan_id):
    """
    Purchase/subscribe a user to a membership plan.

    Creates a MembershipSubscription (active, with an expiry computed once
    from the plan's duration_days) and points the user's membership FK at
    it for quick dashboard display. Any previously active subscription is
    marked cancelled so the DB-level unique-active constraint holds.
    """
    plan = get_object_or_404(Membership, id=plan_id, is_active=True)

    if request.method == "POST":
        now = timezone.now()
        # End any currently active subscription for this user.
        MembershipSubscription.objects.filter(
            user=request.user, status=MembershipSubscription.STATUS_ACTIVE
        ).update(
            status=MembershipSubscription.STATUS_CANCELLED,
            cancelled_at=now,
        )

        MembershipSubscription.objects.create(
            user=request.user,
            plan=plan,
            status=MembershipSubscription.STATUS_ACTIVE,
            started_at=now,
            expires_at=now + timezone.timedelta(days=plan.duration_days),
        )

        # Keep the simple FK in sync for dashboard display.
        request.user.membership = plan
        request.user.save(update_fields=["membership"])

        messages.success(
            request,
            f"You're now subscribed to the {plan.name} plan!",
        )
        return redirect("users:dashboard")

    return render(
        request,
        "memberships/subscribe_confirm.html",
        {"plan": plan},
    )
