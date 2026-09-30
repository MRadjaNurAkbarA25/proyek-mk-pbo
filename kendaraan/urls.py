from django.urls import path
from . import views

urlpatterns = [
    path("", views.daftar_kendaraan, name="daftar_kendaraan"),
    path("tambah/<str:tipe>/", views.tambah_kendaraan, name="tambah_kendaraan"),
    path("cari/", views.cari_kendaraan, name="cari_kendaraan"),
]