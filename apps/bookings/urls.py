from django.urls import path
from . import views

urlpatterns = [
    path('', views.booking_create, name='booking_create'),
    path('<int:pk>/payment/', views.booking_payment, name='booking_payment'),
    path('<int:pk>/confirm/', views.booking_confirm, name='booking_confirm'),
]
