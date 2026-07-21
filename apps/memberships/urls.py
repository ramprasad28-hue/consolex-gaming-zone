from django.urls import path
from . import views

app_name = "memberships"

urlpatterns = [
    path("", views.plan_list, name="plan_list"),
    path("<int:plan_id>/subscribe/", views.subscribe, name="subscribe"),
    path("<int:plan_id>/pay/", views.membership_payment_page, name="membership_payment_page"),
    path("verify-payment/", views.verify_membership_payment, name="verify_membership_payment"),
]
