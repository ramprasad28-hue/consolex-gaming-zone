from django.urls import path
from django.contrib.auth.decorators import user_passes_test
from . import views

staff_required = user_passes_test(lambda u: u.is_staff or u.is_superuser, login_url="users:login")

urlpatterns = [
    path("", staff_required(views.staff_dashboard), name="staff_dashboard"),
    path("bookings/", staff_required(views.booking_list), name="staff_booking_list"),
    path("bookings/<int:booking_id>/", staff_required(views.booking_detail), name="staff_booking_detail"),
    path("customers/", staff_required(views.customer_list), name="staff_customer_list"),
    path("customers/<int:user_id>/", staff_required(views.customer_detail), name="staff_customer_detail"),
    path("games/", staff_required(views.game_list), name="staff_game_list"),
    path("tournaments/", staff_required(views.tournament_list), name="staff_tournament_list"),
    path("memberships/", staff_required(views.membership_list), name="staff_membership_list"),
    path("analytics/", staff_required(views.analytics_dashboard), name="staff_analytics"),
    path("reports/", staff_required(views.reports), name="staff_reports"),
    path("reports/<str:report_type>/", staff_required(views.report_detail), name="staff_report_detail"),
    path("import/", staff_required(views.import_customers), name="staff_import"),
    path("communication/", staff_required(views.bulk_communication), name="staff_communication"),
    path("communication/history/", staff_required(views.communication_history), name="staff_comm_history"),
    path("settings/", staff_required(views.settings_page), name="staff_settings"),
]
