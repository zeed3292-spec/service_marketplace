from django.urls import path
from . import views
app_name='payments'
urlpatterns=[path('create/<str:order_number>/', views.payment_create, name='payment_create')]
