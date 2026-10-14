from django.urls import path
from . import views, views_pelanggan

urlpatterns = [
    path("dashboard/", views.dashboard_admin, name="admin_dashboard"),
    path("pelanggan/", views_pelanggan.daftar_pelanggan, name="kelola_pelanggan"),
    path("pelanggan/tambah/", views_pelanggan.tambah_pelanggan, name="kelola_pelanggan_tambah"),
    path("pelanggan/<int:pk>/ubah/", views_pelanggan.ubah_pelanggan, name="kelola_pelanggan_ubah"),
    path("pelanggan/<int:pk>/hapus/", views_pelanggan.hapus_pelanggan, name="kelola_pelanggan_hapus"),
]