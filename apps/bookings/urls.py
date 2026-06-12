from django.urls import path
from . import views

urlpatterns = [
    path('', views.booking_create, name='booking_create'),
    path('<int:pk>/payment/', views.booking_payment, name='booking_payment'),
    path('<int:pk>/confirm/', views.booking_confirm, name='booking_confirm'),
    path('<int:pk>/cancel/', views.booking_cancel, name='booking_cancel'),
     path('book/',            views.booking_form,   name='booking_form'),
    path('<int:booking_id>/', views.booking_detail, name='booking_detail'),
]
