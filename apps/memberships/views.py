# apps/memberships/views.py
from django.shortcuts import render

from .models import Membership


def plan_list(request):
    """Render all active membership plans from the database."""
    plans = Membership.objects.filter(is_active=True)
    return render(
        request,
        "memberships/plans.html",
        {"plans": plans},
    )
