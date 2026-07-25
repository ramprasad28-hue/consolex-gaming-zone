from django.db import models
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.core.validators import RegexValidator
from django.utils import timezone


class UserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError("Email is required")
        email = self.normalize_email(email)
        if not extra_fields.get("username"):
            extra_fields["username"] = email.split("@")[0]
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_active", True)
        return self.create_user(email, password, **extra_fields)

    def verified(self):
        return self.filter(is_verified=True)

    def active_members(self):
        return self.filter(
            subscriptions__status="active",
            subscriptions__expires_at__gt=timezone.now(),
        ).distinct()


class User(AbstractUser):
    phone_regex = RegexValidator(
        regex=r"^\+?[\d\s-]{7,15}$",
        message="Phone number must be in valid format (e.g. +91 98765 43210).",
    )

    email = models.EmailField(unique=True)
    phone = models.CharField(
        max_length=15, blank=True, null=True,
        validators=[phone_regex],
    )
    is_verified = models.BooleanField(default=False)
    membership = models.ForeignKey(
        "memberships.Membership",
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="users",
    )
    created_at = models.DateTimeField(default=timezone.now)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    objects = UserManager()

    class Meta:
        ordering = ["-date_joined"]
        indexes = [
            models.Index(fields=["email"], name="idx_user_email"),
            models.Index(fields=["phone"], name="idx_user_phone"),
            models.Index(fields=["-created_at"], name="idx_user_created"),
        ]

    def __str__(self):
        return self.email

    @property
    def full_display_name(self):
        name = self.get_full_name()
        return name if name else self.email

    @property
    def has_active_subscription(self):
        return self.subscriptions.filter(
            status="active",
            expires_at__gt=timezone.now(),
        ).exists()
