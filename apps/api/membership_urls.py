from django.urls import path
from . import membership_views

urlpatterns = [
    path("plans/", membership_views.plan_list, name="api-membership-plans"),
    path("subscription/", membership_views.subscription_detail, name="api-membership-subscription"),
    path("<int:plan_id>/subscribe/", membership_views.subscribe, name="api-membership-subscribe"),
    path("verify-payment/", membership_views.verify_payment, name="api-membership-verify"),
]
