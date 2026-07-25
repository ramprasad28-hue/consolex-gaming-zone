from rest_framework import serializers
from django.contrib.auth import get_user_model
from apps.games.models import GameConsole
from apps.bookings.models import Booking
from apps.payments.models import Payment
from apps.memberships.models import Membership, MembershipSubscription
from apps.notifications.models import Notification

User = get_user_model()


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = [
            "id", "email", "first_name", "last_name", "phone",
            "is_verified", "membership", "created_at",
        ]
        read_only_fields = ["id", "email", "is_verified", "created_at"]


class UserRegisterSerializer(serializers.Serializer):
    email = serializers.EmailField()
    first_name = serializers.CharField(max_length=150, required=False, default="")
    last_name = serializers.CharField(max_length=150, required=False, default="")
    password = serializers.CharField(min_length=8, write_only=True)


class UserLoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField()


class MembershipPlanSerializer(serializers.ModelSerializer):
    class Meta:
        model = Membership
        fields = [
            "id", "name", "description", "price", "duration_days",
            "discount_percent", "priority_booking", "included_hours",
            "weekend_hours", "bonus_hours", "badge_color", "tier_level",
            "is_popular", "is_active",
        ]


class MembershipSubscriptionSerializer(serializers.ModelSerializer):
    plan = MembershipPlanSerializer(read_only=True)
    days_remaining = serializers.IntegerField(read_only=True)
    is_active_valid = serializers.BooleanField(read_only=True)

    class Meta:
        model = MembershipSubscription
        fields = [
            "id", "plan", "status", "started_at", "expires_at",
            "days_remaining", "is_active_valid",
        ]


class GameConsoleSerializer(serializers.ModelSerializer):
    class Meta:
        model = GameConsole
        fields = [
            "id", "name", "console_type", "hourly_rate_weekday",
            "hourly_rate_weekend", "is_active", "image",
        ]
        read_only_fields = ["id"]


class BookingSerializer(serializers.ModelSerializer):
    game_console_detail = GameConsoleSerializer(source="game_console", read_only=True)
    duration_hours = serializers.FloatField(read_only=True)
    advance_amount = serializers.DecimalField(
        max_digits=8, decimal_places=2, read_only=True
    )
    balance_amount = serializers.DecimalField(
        max_digits=8, decimal_places=2, read_only=True
    )
    is_paid = serializers.BooleanField(read_only=True)
    console_name = serializers.CharField(
        source="game_console.name", read_only=True
    )

    class Meta:
        model = Booking
        fields = [
            "id", "user", "game_console", "game_console_detail", "console_name",
            "booking_date", "start_time", "end_time", "number_of_players",
            "total_cost", "status", "created_at", "duration_hours",
            "advance_amount", "balance_amount", "is_paid",
        ]
        read_only_fields = [
            "id", "user", "total_cost", "status", "created_at",
            "advance_amount", "balance_amount", "is_paid",
        ]


class BookingCreateSerializer(serializers.Serializer):
    booking_date = serializers.DateField()
    start_time = serializers.TimeField()
    duration_hours = serializers.IntegerField(min_value=1, max_value=10)
    number_of_players = serializers.IntegerField(min_value=1, max_value=4)
    game_console = serializers.IntegerField()


class PaymentSerializer(serializers.ModelSerializer):
    amount_rupees = serializers.DecimalField(
        max_digits=8, decimal_places=2, read_only=True
    )

    class Meta:
        model = Payment
        fields = [
            "id", "booking", "amount", "amount_rupees", "currency",
            "status", "is_demo", "razorpay_order_id", "created_at",
        ]
        read_only_fields = fields


class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = ["id", "message", "is_read", "created_at"]
        read_only_fields = ["id", "message", "is_read", "created_at"]
