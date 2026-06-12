# ─────────────────────────────────────────────
# File: apps/payments/urls.py
# ─────────────────────────────────────────────

from django.urls import path
from . import views

urlpatterns = [
    path('<int:booking_id>/',         views.payment_page,    name='payment_page'),
    path('demo/<int:booking_id>/',    views.demo_payment,    name='demo_payment'),
    path('verify/',                   views.verify_payment,  name='verify_payment'),
    path('success/<int:booking_id>/', views.payment_success, name='payment_success'),
    path('failed/<int:booking_id>/',  views.payment_failed,  name='payment_failed'),
]