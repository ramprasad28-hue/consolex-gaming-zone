"""
Custom exception hierarchy for CONSOLEX.

Service layers raise these; views/serializers catch and translate them into
appropriate HTTP responses.  This keeps business logic decoupled from HTTP.
"""
import logging

logger = logging.getLogger("apps.common")


class ServiceError(Exception):
    """Base class for all service-layer errors."""

    status_code = 500
    default_message = "An unexpected error occurred."

    def __init__(self, message=None, code=None, extra=None):
        self.message = message or self.default_message
        self.code = code or self.__class__.__name__
        self.extra = extra or {}
        logger.warning(
            "%s: %s (code=%s, extra=%s)",
            self.__class__.__name__,
            self.message,
            self.code,
            self.extra,
        )
        super().__init__(self.message)


# ── Validation ────────────────────────────────────
class ValidationError(ServiceError):
    status_code = 400
    default_message = "Validation failed."


class BookingConflictError(ValidationError):
    default_message = "This time slot is already booked."


class BookingValidationError(ValidationError):
    default_message = "Invalid booking data."


class SlotOutsideOperatingHoursError(ValidationError):
    default_message = "Selected time is outside operating hours."


class BookingInPastError(ValidationError):
    default_message = "Cannot book a slot in the past."


class BookingCannotBeCancelledError(ValidationError):
    default_message = "This booking cannot be cancelled."


class PaymentAlreadyCompletedError(ValidationError):
    default_message = "Payment has already been completed."


class PaymentVerificationError(ValidationError):
    default_message = "Payment verification failed."


class SubscriptionAlreadyActiveError(ValidationError):
    default_message = "You already have an active subscription."


# ── Not Found ─────────────────────────────────────
class NotFoundError(ServiceError):
    status_code = 404
    default_message = "Resource not found."


class BookingNotFoundError(NotFoundError):
    default_message = "Booking not found."


class ConsoleNotFoundError(NotFoundError):
    default_message = "Console not found."


class PlanNotFoundError(NotFoundError):
    default_message = "Membership plan not found."


class PaymentNotFoundError(NotFoundError):
    default_message = "Payment not found."


# ── External Service ──────────────────────────────
class ExternalServiceError(ServiceError):
    status_code = 502
    default_message = "External service unavailable."


class RazorpayError(ExternalServiceError):
    default_message = "Unable to connect to Razorpay. Please try again."


class RazorpaySignatureError(ValidationError):
    default_message = "Payment signature verification failed."


# ── Auth ──────────────────────────────────────────
class AuthenticationError(ServiceError):
    status_code = 401
    default_message = "Authentication failed."


class DuplicateEmailError(ValidationError):
    default_message = "An account with this email already exists."
