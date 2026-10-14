from django.urls import path
from . import views

urlpatterns = [
    path("dashboard/", views.dashboard_admin, name="admin_dashboard"),
]