# ─────────────────────────────────────────────
# File: apps/payments/urls.py
# ─────────────────────────────────────────────

from django.urls import path
from . import views
app_name = "payments"
urlpatterns = [
    path('<int:booking_id>/',         views.payment_page,    name='payment_page'),
    path('verify/',                   views.verify_payment,  name='verify_payment'),
    path('webhook/',                  views.razorpay_webhook, name='webhook'),
    path('success/<int:booking_id>/', views.payment_success, name='payment_success'),
    path('failed/<int:booking_id>/',  views.payment_failed,  name='payment_failed'),
    path('receipt/<int:booking_id>/', views.payment_receipt, name='payment_receipt'),
]