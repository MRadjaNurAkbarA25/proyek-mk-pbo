from django.urls import path
from . import views

urlpatterns = [
    path("", views.daftar_kendaraan, name="daftar_kendaraan"),
    path("tambah/<str:tipe>/", views.tambah_kendaraan, name="tambah_kendaraan"),
    path("edit/<str:tipe>/<int:pk>/", views.edit_kendaraan, name="edit_kendaraan"),
    path("hapus/<str:tipe>/<int:pk>/", views.hapus_kendaraan, name="hapus_kendaraan"),
    path("cari/", views.cari_kendaraan, name="cari_kendaraan"),
]