from django.urls import path
from . import payment_views

urlpatterns = [
    path("create-order/", payment_views.create_order, name="api-payment-create-order"),
    path("verify/", payment_views.verify_payment, name="api-payment-verify"),
    path("receipt/<int:booking_id>/", payment_views.receipt, name="api-payment-receipt"),
]
