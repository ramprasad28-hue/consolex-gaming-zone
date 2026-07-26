# apps/common/tests.py
from django.test import TestCase

from apps.common.exceptions import (
    ServiceError,
    ValidationError,
    BookingConflictError,
    BookingValidationError,
    SlotOutsideOperatingHoursError,
    BookingInPastError,
    BookingCannotBeCancelledError,
    PaymentAlreadyCompletedError,
    PaymentVerificationError,
    SubscriptionAlreadyActiveError,
    NotFoundError,
    BookingNotFoundError,
    ConsoleNotFoundError,
    PlanNotFoundError,
    PaymentNotFoundError,
    ExternalServiceError,
    RazorpayError,
    RazorpaySignatureError,
    AuthenticationError,
    DuplicateEmailError,
)


class ServiceErrorTests(TestCase):
    def test_base_exception_default_message(self):
        err = ServiceError()
        self.assertEqual(str(err), "An unexpected error occurred.")
        self.assertEqual(err.status_code, 500)

    def test_base_exception_custom_message(self):
        err = ServiceError(message="Custom error")
        self.assertEqual(str(err), "Custom error")

    def test_base_exception_code(self):
        err = ServiceError(code="MY_CODE")
        self.assertEqual(err.code, "MY_CODE")

    def test_base_exception_default_code(self):
        err = ServiceError()
        self.assertEqual(err.code, "ServiceError")

    def test_base_exception_extra(self):
        err = ServiceError(extra={"field": "value"})
        self.assertEqual(err.extra, {"field": "value"})

    def test_base_exception_default_extra(self):
        err = ServiceError()
        self.assertEqual(err.extra, {})


class ValidationErrorHierarchyTests(TestCase):
    def test_booking_conflict_is_validation(self):
        self.assertTrue(issubclass(BookingConflictError, ValidationError))

    def test_booking_validation_is_service_error(self):
        self.assertTrue(issubclass(BookingValidationError, ServiceError))

    def test_slot_outside_hours_is_validation(self):
        self.assertTrue(issubclass(SlotOutsideOperatingHoursError, ValidationError))

    def test_booking_in_past_is_validation(self):
        self.assertTrue(issubclass(BookingInPastError, ValidationError))

    def test_booking_cannot_cancel_is_validation(self):
        self.assertTrue(issubclass(BookingCannotBeCancelledError, ValidationError))

    def test_payment_already_completed_is_validation(self):
        self.assertTrue(issubclass(PaymentAlreadyCompletedError, ValidationError))

    def test_payment_verification_is_validation(self):
        self.assertTrue(issubclass(PaymentVerificationError, ValidationError))

    def test_subscription_already_active_is_validation(self):
        self.assertTrue(issubclass(SubscriptionAlreadyActiveError, ValidationError))

    def test_validation_error_status_code(self):
        self.assertEqual(ValidationError.status_code, 400)

    def test_custom_messages(self):
        self.assertIn("time slot", BookingConflictError().message.lower())
        self.assertIn("past", BookingInPastError().message.lower())
        self.assertIn("cancelled", BookingCannotBeCancelledError().message.lower())
        self.assertIn("already been completed", PaymentAlreadyCompletedError().message.lower())


class NotFoundErrorHierarchyTests(TestCase):
    def test_booking_not_found_is_not_found(self):
        self.assertTrue(issubclass(BookingNotFoundError, NotFoundError))

    def test_console_not_found_is_not_found(self):
        self.assertTrue(issubclass(ConsoleNotFoundError, NotFoundError))

    def test_plan_not_found_is_not_found(self):
        self.assertTrue(issubclass(PlanNotFoundError, NotFoundError))

    def test_payment_not_found_is_not_found(self):
        self.assertTrue(issubclass(PaymentNotFoundError, NotFoundError))

    def test_not_found_status_code(self):
        self.assertEqual(NotFoundError.status_code, 404)

    def test_not_found_is_service_error(self):
        self.assertTrue(issubclass(NotFoundError, ServiceError))


class ExternalServiceErrorTests(TestCase):
    def test_razorpay_error_is_external(self):
        self.assertTrue(issubclass(RazorpayError, ExternalServiceError))

    def test_external_service_status_code(self):
        self.assertEqual(ExternalServiceError.status_code, 502)

    def test_razorpay_signature_is_validation(self):
        self.assertTrue(issubclass(RazorpaySignatureError, ValidationError))


class AuthErrorTests(TestCase):
    def test_authentication_error_status_code(self):
        self.assertEqual(AuthenticationError.status_code, 401)

    def test_authentication_error_is_service_error(self):
        self.assertTrue(issubclass(AuthenticationError, ServiceError))

    def test_duplicate_email_is_validation(self):
        self.assertTrue(issubclass(DuplicateEmailError, ValidationError))


class ExceptionInstantiationTests(TestCase):
    def test_booking_conflict_default_message(self):
        err = BookingConflictError()
        self.assertEqual(err.status_code, 400)

    def test_console_not_found_default_message(self):
        err = ConsoleNotFoundError()
        self.assertIn("Console", err.message)

    def test_razorpay_error_default_message(self):
        err = RazorpayError()
        self.assertIn("Razorpay", err.message)

    def test_custom_message_override(self):
        err = BookingNotFoundError(message="Custom not found")
        self.assertEqual(err.message, "Custom not found")
