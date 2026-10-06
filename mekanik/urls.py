from django.urls import path
from . import views

urlpatterns = [
    path("dashboard/", views.dashboard_mekanik, name="mekanik_dashboard"),
]