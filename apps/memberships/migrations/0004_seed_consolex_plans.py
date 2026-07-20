# Generated data migration: seed the real CONSOLEX membership plans.
from django.db import migrations, models


# Plan data exactly as per the CONSOLEX business model poster.
PLANS = [
    {
        "name": "Basic",
        "description": "Perfect for casual gamers who want a regular weekday slot.",
        "price": "1199.00",
        "duration_days": 30,
        "included_hours": 10,
        "weekend_hours": 0,
        "bonus_hours": 0,
        "discount_percent": 0,
        "priority_booking": False,
        "tier_level": 1,
        "is_popular": False,
        "is_active": True,
    },
    {
        "name": "Standard",
        "description": "For dedicated gamers who love weekend sessions with their squad.",
        "price": "2499.00",
        "duration_days": 30,
        "included_hours": 25,
        "weekend_hours": 5,
        "bonus_hours": 0,
        "discount_percent": 0,
        "priority_booking": False,
        "tier_level": 2,
        "is_popular": True,
        "is_active": True,
    },
    {
        "name": "Pro",
        "description": "For hardcore gamers who live and breathe PS5. Unlimited mode.",
        "price": "3999.00",
        "duration_days": 30,
        "included_hours": 40,
        "weekend_hours": 0,
        "bonus_hours": 5,
        "discount_percent": 0,
        "priority_booking": True,
        "tier_level": 3,
        "is_popular": False,
        "is_active": True,
    },
]


def seed_plans(apps, schema_editor):
    Membership = apps.get_model("memberships", "Membership")
    for data in PLANS:
        Membership.objects.update_or_create(
            name=data["name"],
            defaults=data,
        )


def remove_plans(apps, schema_editor):
    Membership = apps.get_model("memberships", "Membership")
    Membership.objects.filter(
        name__in=[p["name"] for p in PLANS]
    ).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('memberships', '0003_membership_bonus_hours_membership_included_hours_and_more'),
    ]

    operations = [
        migrations.RunPython(seed_plans, remove_plans),
    ]
