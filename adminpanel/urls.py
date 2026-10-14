from django.urls import path

from . import views, views_laporan

urlpatterns = [
    path("dashboard/", views.dashboard_admin, name="admin_dashboard"),
    path("laporan/transaksi/", views_laporan.laporan_transaksi, name="laporan_transaksi"),
    path("laporan/pendapatan/", views_laporan.laporan_pendapatan, name="laporan_pendapatan"),
    path("laporan/stok/", views_laporan.laporan_stok, name="laporan_stok"),
    path("laporan/mekanik/", views_laporan.laporan_mekanik, name="laporan_mekanik"),
]
