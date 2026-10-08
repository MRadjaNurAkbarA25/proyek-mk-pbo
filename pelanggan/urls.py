# pelanggan/urls.py
from django.urls import path
from . import views

urlpatterns = [
    path("dashboard/", views.dashboard_pelanggan, name="pelanggan_dashboard"),
    path("profil/edit/", views.edit_profil, name="edit_profil"),
    path("kendaraan/tambah/pilih/", views.pilih_tipe_kendaraan, name="pilih_tipe_kendaraan"),
    path("kendaraan/tambah/<str:tipe>/", views.tambah_kendaraan, name="tambah_kendaraan"),
    path("kendaraan/edit/<int:pk>/", views.edit_kendaraan, name="edit_kendaraan"),
    path("kendaraan/hapus/<int:pk>/", views.hapus_kendaraan, name="hapus_kendaraan"),
    path("kendaraan/", views.kendaraan_saya, name="kendaraan_saya"),
]