from django.urls import path
from . import views

urlpatterns = [
     path('book/',            views.booking_form,   name='booking_form'),
    path('<int:booking_id>/', views.booking_detail, name='booking_detail'),

]
