from django.db import IntegrityError, models, transaction
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.core.validators import RegexValidator
from django.utils import timezone
from django.utils.crypto import get_random_string

USERNAME_MAX_LENGTH = 150


class UserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError("Email is required")
        email = self.normalize_email(email)
        if not extra_fields.get("username"):
            extra_fields["username"] = self._generate_username(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        try:
            with transaction.atomic():
                user.save(using=self._db)
        except IntegrityError:
            # A concurrent registration claimed the same username between
            # the availability check and save; retry with a random suffix.
            extra_fields["username"] = self._fallback_username(email)
            user = self.model(email=email, **extra_fields)
            user.set_password(password)
            user.save(using=self._db)
        return user

    def _generate_username(self, email):
        """Derive a unique username from the email local-part.

        Keeps the plain prefix when free (john@a.com -> john) and appends an
        index on collision (john@b.com -> john1, john@c.com -> john2).
        """
        base = email.split("@")[0]
        username = base
        index = 0
        while self.model._default_manager.filter(username=username).exists():
            index += 1
            suffix = str(index)
            username = f"{base[:USERNAME_MAX_LENGTH - len(suffix)]}{suffix}"
        return username

    def _fallback_username(self, email):
        """Random-suffix username used when the availability check races."""
        return (
            f"{email.split('@')[0][:USERNAME_MAX_LENGTH - 9]}"
            f"-{get_random_string(8)}"
        )

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
