from django.urls import path
from . import views

urlpatterns = [
    path("dashboard/", views.dashboard_pelanggan, name="pelanggan_dashboard"),
]