from django.urls import path
from . import views, views_transaksi

urlpatterns = [
    path("dashboard/", views.dashboard_kasir, name="kasir_dashboard"),
    path("kendaraan/cari/", views.cari_kendaraan, name="kasir_cari_kendaraan"),

    # FR-11: Buat & lihat transaksi servis
    path("transaksi/buat/", views_transaksi.buat_transaksi, name="kasir_transaksi_buat"),
    path("transaksi/", views_transaksi.daftar_transaksi, name="kasir_transaksi_daftar"),
    path("transaksi/<int:pk>/", views_transaksi.detail_transaksi, name="kasir_transaksi_detail"),
]
