from django.urls import path

from . import views

urlpatterns = [
    path("daftar/", views.daftar, name="faq_daftar"),
    path("cari/", views.cari, name="faq_cari"),
]
